from __future__ import annotations

import json
import queue
import re
import subprocess
import tempfile
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from hook_types import JsonObject


class ModelDiscoveryError(Exception):
    pass


def oldest_medium_model(models: Sequence[JsonObject]) -> str:
    candidates: list[tuple[tuple[int, int], str]] = []
    for model in models:
        name = model.get("model")
        if not isinstance(name, str) or model.get("hidden") is True:
            continue
        version = re.match(r"^gpt-(\d+)(?:\.(\d+))?(?:-|$)", name)
        efforts = model.get("supportedReasoningEfforts")
        if version is None or not isinstance(efforts, list):
            continue
        if not any(
            isinstance(effort, dict) and effort.get("reasoningEffort") == "medium"
            for effort in efforts
        ):
            continue
        modalities = model.get("inputModalities")
        if isinstance(modalities, list) and "text" not in modalities:
            continue
        candidates.append(((int(version[1]), int(version[2] or 0)), name))
    if not candidates:
        msg = "Codex model/list has no visible GPT model supporting medium text requests"
        raise ModelDiscoveryError(msg)
    # Equal generations keep Codex's own picker order.
    return min(candidates, key=lambda candidate: candidate[0])[1]


def read_lines(stream: TextIO, lines: queue.Queue[str | None]) -> None:
    try:
        for line in stream:
            lines.put(line)
    finally:
        lines.put(None)


def send_message(process: subprocess.Popen[str], message: JsonObject) -> None:
    if process.stdin is None:
        msg = "Codex model/list stdin is unavailable"
        raise ModelDiscoveryError(msg)
    _ = process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def receive_result(
    lines: queue.Queue[str | None],
    request_id: int,
    deadline: float,
) -> JsonObject:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            msg = "Codex model/list timed out"
            raise ModelDiscoveryError(msg)
        try:
            line = lines.get(timeout=remaining)
        except queue.Empty as exc:
            msg = "Codex model/list timed out"
            raise ModelDiscoveryError(msg) from exc
        if line is None:
            msg = "Codex exited before returning model/list"
            raise ModelDiscoveryError(msg)
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            msg = "Codex model/list returned invalid JSON"
            raise ModelDiscoveryError(msg) from exc
        if not isinstance(parsed, dict):
            msg = "Codex model/list returned a non-object message"
            raise ModelDiscoveryError(msg)
        message: JsonObject = {key: value for key, value in parsed.items() if isinstance(key, str)}
        if message.get("id") != request_id:
            continue
        if "error" in message:
            msg = f"Codex model/list failed: {message['error']}"
            raise ModelDiscoveryError(msg)
        result = message.get("result")
        if not isinstance(result, dict):
            msg = "Codex model/list response has no result object"
            raise ModelDiscoveryError(msg)
        return result


def read_model_pages(
    process: subprocess.Popen[str],
    lines: queue.Queue[str | None],
    deadline: float,
) -> list[JsonObject]:
    models: list[JsonObject] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    request_id = 2
    while True:
        send_message(
            process,
            {
                "id": request_id,
                "method": "model/list",
                "params": {"limit": 100, "includeHidden": False, "cursor": cursor},
            },
        )
        result = receive_result(lines, request_id, deadline)
        page = result.get("data")
        if not isinstance(page, list):
            msg = "Codex model/list response has invalid model data"
            raise ModelDiscoveryError(msg)
        for item in page:
            if not isinstance(item, dict):
                msg = "Codex model/list response has invalid model data"
                raise ModelDiscoveryError(msg)
            models.append(item)
        next_cursor = result.get("nextCursor")
        if next_cursor is None:
            return models
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
            msg = "Codex model/list returned an invalid or repeated cursor"
            raise ModelDiscoveryError(msg)
        seen_cursors.add(next_cursor)
        cursor = next_cursor
        request_id += 1


def list_codex_models(
    codex_bin: str,
    env: Mapping[str, str],
    cwd: str,
    *,
    timeout: float = 20,
) -> list[JsonObject]:
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stderr:
        try:
            process = subprocess.Popen(  # noqa: S603
                [codex_bin, "app-server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr,
                text=True,
                encoding="utf-8",
                env=env,
                cwd=cwd,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            msg = f"codex executable could not be started for model/list: {codex_bin}: {exc}"
            raise ModelDiscoveryError(msg) from exc
        lines: queue.Queue[str | None] = queue.Queue()
        if process.stdout is None:
            msg = "Codex model/list stdout is unavailable"
            raise ModelDiscoveryError(msg)
        reader = threading.Thread(target=read_lines, args=(process.stdout, lines), daemon=True)
        reader.start()
        try:
            send_message(
                process,
                {
                    "id": 1,
                    "method": "initialize",
                    "params": {"clientInfo": {"name": "lazy_eng_study_codex", "version": "0.2.0"}},
                },
            )
            _ = receive_result(lines, 1, deadline)
            send_message(process, {"method": "initialized", "params": {}})
            return read_model_pages(process, lines, deadline)
        except (ModelDiscoveryError, OSError) as exc:
            _ = stderr.seek(0)
            detail = stderr.read().strip()[-2000:]
            msg = f"{exc}: {detail}" if detail else str(exc)
            raise ModelDiscoveryError(msg) from exc
        finally:
            if process.stdin is not None:
                with suppress(OSError):
                    process.stdin.close()
            try:
                _ = process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                _ = process.wait()
            reader.join(timeout=1)
            process.stdout.close()
