from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

    from hook_trust import TrustedHookState

LEGACY_MARKETPLACE_NAME: Final = "codex-kor-to-eng-local"
LEGACY_PLUGIN_KEY: Final = "codex-kor-to-eng@codex-kor-to-eng-local"
LEGACY_HOOK_KEY: Final = f"{LEGACY_PLUGIN_KEY}:hooks/hooks.json:user_prompt_submit:0:0"


def update_codex_config(
    *,
    config_path: Path,
    source_root: Path,
    marketplace_name: str,
    plugin_name: str,
    trusted_hooks: tuple[TrustedHookState, ...],
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    config = remove_legacy_plugin_config(config)
    config = ensure_table_setting(config, "features", "plugins", "true")
    config = ensure_table_setting(config, "features", "plugin_hooks", "true")
    config = upsert_table(
        config,
        f"marketplaces.{marketplace_name}",
        "\n".join(
            [
                f"[marketplaces.{marketplace_name}]",
                f'last_updated = "{utc_timestamp()}"',
                f"source_type = {toml_string('local')}",
                f"source = {toml_string(str(source_root))}",
            ],
        ),
    )
    plugin_key = f"{plugin_name}@{marketplace_name}"
    plugin_header = f"plugins.{toml_string(plugin_key)}"
    config = upsert_table(config, plugin_header, f"[{plugin_header}]\nenabled = true")
    for state in trusted_hooks:
        header = f"hooks.state.{toml_string(state.key)}"
        body = (
            f"[{header}]\n"
            "enabled = true\n"
            f"trusted_hash = {toml_string(state.trusted_hash)}"
        )
        config = upsert_table(config, header, body)
    _ = config_path.write_text(f"{config.rstrip()}\n", encoding="utf-8")


def remove_legacy_plugin_config(config: str) -> str:
    cleaned = remove_table(config, f"marketplaces.{LEGACY_MARKETPLACE_NAME}")
    cleaned = remove_table(cleaned, f"plugins.{toml_string(LEGACY_PLUGIN_KEY)}")
    return remove_table(cleaned, f"hooks.state.{toml_string(LEGACY_HOOK_KEY)}")


def ensure_table_setting(config: str, header: str, key: str, value: str) -> str:
    section = find_table(config, header)
    if section is None:
        return append_block(config, f"[{header}]\n{key} = {value}")

    start, end = section
    lines = config.splitlines(keepends=True)
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for index in range(start + 1, end):
        if pattern.match(lines[index]):
            lines[index] = f"{key} = {value}\n"
            return "".join(lines)
    lines.insert(start + 1, f"{key} = {value}\n")
    return "".join(lines)


def upsert_table(config: str, header: str, body: str) -> str:
    without_old = remove_table(config, header)
    return append_block(without_old, body)


def find_table(config: str, header: str) -> tuple[int, int] | None:
    lines = config.splitlines(keepends=True)
    header_line = f"[{header}]"
    start = -1
    for index, line in enumerate(lines):
        stripped = line.strip()
        if start == -1:
            if stripped == header_line:
                start = index
        elif is_table_header(stripped):
            return start, index
    if start == -1:
        return None
    return start, len(lines)


def remove_table(config: str, header: str) -> str:
    lines = config.splitlines(keepends=True)
    header_line = f"[{header}]"
    kept: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != header_line:
            kept.append(lines[index])
            index += 1
            continue
        index += 1
        while index < len(lines) and not is_table_header(lines[index].strip()):
            index += 1
    return re.sub(r"\n{3,}", "\n\n", "".join(kept))


def append_block(config: str, block: str) -> str:
    prefix = config.rstrip()
    clean_block = block.strip()
    if prefix == "":
        return f"{clean_block}\n"
    return f"{prefix}\n\n{clean_block}\n"


def is_table_header(line: str) -> bool:
    return line.startswith("[") and line.endswith("]") and not line.startswith("[[")


def toml_string(value: str) -> str:
    return json.dumps(value)


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
