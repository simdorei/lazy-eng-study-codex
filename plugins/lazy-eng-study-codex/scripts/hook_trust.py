from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from install_errors import InstallPluginError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from hook_types import JsonObject, JsonValue

EVENT_LABELS: Final[dict[str, str]] = {
    "PreToolUse": "pre_tool_use",
    "PermissionRequest": "permission_request",
    "PostToolUse": "post_tool_use",
    "PreCompact": "pre_compact",
    "PostCompact": "post_compact",
    "SessionStart": "session_start",
    "UserPromptSubmit": "user_prompt_submit",
    "SubagentStart": "subagent_start",
    "SubagentStop": "subagent_stop",
    "Stop": "stop",
}


@dataclass(frozen=True, slots=True)
class TrustedHookState:
    key: str
    trusted_hash: str


def trusted_hook_states_for_plugin(
    *,
    plugin_root: Path,
    plugin_name: str,
    marketplace_name: str,
    manifest: JsonObject,
) -> list[TrustedHookState]:
    states: list[TrustedHookState] = []
    for hook_path in hook_manifest_paths(manifest.get("hooks")):
        hooks_file = resolve_hook_manifest_path(plugin_root, hook_path)
        if not hooks_file.is_file():
            msg = f"hook manifest path does not exist: {hooks_file}"
            raise InstallPluginError(msg)
        parsed = read_json_object(hooks_file)
        hooks = parsed.get("hooks")
        if not isinstance(hooks, dict):
            msg = f"hooks file must contain a hooks object: {hooks_file}"
            raise InstallPluginError(msg)
        key_source = f"{plugin_name}@{marketplace_name}:{hook_path}"
        states.extend(trusted_hook_states_for_hooks_file(key_source, hooks))
    return states


def hook_manifest_paths(value: JsonValue) -> list[str]:
    if isinstance(value, str) and value.strip() != "":
        return [strip_dot_slash(value)]
    if not isinstance(value, list):
        return []
    return [strip_dot_slash(item) for item in value if isinstance(item, str) and item.strip() != ""]


def resolve_hook_manifest_path(plugin_root: Path, hook_path: str) -> Path:
    resolved_root = plugin_root.resolve()
    resolved_path = (plugin_root / hook_path).resolve()
    if resolved_path != resolved_root and resolved_path.is_relative_to(resolved_root):
        return resolved_path
    msg = f"hook manifest path escapes plugin root: {hook_path}"
    raise InstallPluginError(msg)


def trusted_hook_states_for_hooks_file(
    key_source: str,
    hooks: Mapping[str, JsonValue],
) -> list[TrustedHookState]:
    states: list[TrustedHookState] = []
    for event_name, groups_value in hooks.items():
        if not isinstance(groups_value, list):
            continue
        event_label = EVENT_LABELS.get(event_name)
        if event_label is None:
            continue
        states.extend(trusted_hook_states_for_event(key_source, event_label, groups_value))
    return states


def trusted_hook_states_for_event(
    key_source: str,
    event_label: str,
    groups: list[JsonValue],
) -> list[TrustedHookState]:
    states: list[TrustedHookState] = []
    for group_index, group_value in enumerate(groups):
        if not isinstance(group_value, dict):
            continue
        handlers = group_value.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler_index, handler_value in enumerate(handlers):
            key = f"{key_source}:{event_label}:{group_index}:{handler_index}"
            state = trusted_hook_state_for_handler(
                key=key,
                event_label=event_label,
                matcher=group_value.get("matcher"),
                handler_value=handler_value,
            )
            if state is not None:
                states.append(state)
    return states


def trusted_hook_state_for_handler(
    *,
    key: str,
    event_label: str,
    matcher: JsonValue,
    handler_value: JsonValue,
) -> TrustedHookState | None:
    if not isinstance(handler_value, dict):
        return None
    if handler_value.get("type") != "command" or handler_value.get("async") is True:
        return None
    command = handler_value.get("command")
    if not isinstance(command, str) or command.strip() == "":
        return None
    return TrustedHookState(
        key=key,
        trusted_hash=command_hook_hash(event_label, matcher, handler_value),
    )


def command_hook_hash(
    event_label: str,
    matcher: JsonValue,
    handler: Mapping[str, JsonValue],
) -> str:
    command = required_command(handler)
    timeout = normalized_timeout(handler.get("timeout"))
    normalized_handler: JsonObject = {
        "type": "command",
        "command": command,
        "timeout": timeout,
        "async": False,
    }
    status_message = handler.get("statusMessage")
    if isinstance(status_message, str):
        normalized_handler["statusMessage"] = status_message
    identity: JsonObject = {"event_name": event_label, "hooks": [normalized_handler]}
    if isinstance(matcher, str):
        identity["matcher"] = matcher
    canonical = json.dumps(canonical_json(identity), ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def required_command(handler: Mapping[str, JsonValue]) -> str:
    command = handler.get("command")
    if not isinstance(command, str) or command.strip() == "":
        msg = "command hook is missing command"
        raise InstallPluginError(msg)
    return command


def normalized_timeout(value: JsonValue) -> int:
    if isinstance(value, bool) or value is None:
        return 600
    if isinstance(value, int | float):
        return max(int(value), 1)
    return 600


def canonical_json(value: JsonValue) -> JsonValue:
    if isinstance(value, list):
        return [canonical_json(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical_json(value[key]) for key in sorted(value)}
    return value


def read_json_object(path: Path) -> JsonObject:
    try:
        parsed: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"invalid JSON: {path}: {exc}"
        raise InstallPluginError(msg) from exc
    if not isinstance(parsed, dict):
        msg = f"expected JSON object: {path}"
        raise InstallPluginError(msg)
    return parsed


def strip_dot_slash(value: str) -> str:
    stripped = value.strip().removeprefix("./")
    return stripped.replace("\\", "/")
