#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bootstrap="$script_dir/bootstrap.sh"

printf '%s\n' 'Lazy Eng Study Codex install starting'
"$bootstrap" --ensure-python
"$bootstrap" install_plugin.py
"$bootstrap" kortoeng_control.py model gpt55
"$bootstrap" kortoeng_control.py on
"$bootstrap" kortoeng_control.py codex-bin
"$bootstrap" kortoeng_control.py status
printf '%s\n' 'install=ok'
