#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$repo_root/plugins/lazy-eng-study-codex/scripts/install.sh"
