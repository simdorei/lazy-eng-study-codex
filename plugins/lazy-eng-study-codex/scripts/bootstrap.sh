#!/bin/sh
set -eu

MIN_MAJOR=3
MIN_MINOR=11
PY_VERSION=3.12.13
PY_RELEASE=20260623
DEFAULT_DOWNLOAD_ROOT="https://github.com/astral-sh/python-build-standalone/releases/download/$PY_RELEASE"

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

runtime_root() {
    if [ -n "${CODEX_KOR_TO_ENG_RUNTIME_DIR:-}" ]; then
        printf '%s\n' "$CODEX_KOR_TO_ENG_RUNTIME_DIR"
    elif [ -n "${CODEX_HOME:-}" ]; then
        printf '%s\n' "$CODEX_HOME/lazy-eng-study-codex/runtime"
    else
        printf '%s\n' "$HOME/.codex/lazy-eng-study-codex/runtime"
    fi
}

download_root() {
    if [ -n "${CODEX_KOR_TO_ENG_PYTHON_DOWNLOAD_ROOT:-}" ]; then
        printf '%s\n' "${CODEX_KOR_TO_ENG_PYTHON_DOWNLOAD_ROOT%/}"
    else
        printf '%s\n' "$DEFAULT_DOWNLOAD_ROOT"
    fi
}

python_ok() {
    "$1" -c "import sys; raise SystemExit(0 if sys.version_info >= ($MIN_MAJOR, $MIN_MINOR) else 1)" >/dev/null 2>&1
}

system_python() {
    if [ -n "${CODEX_KOR_TO_ENG_PYTHON_BIN:-}" ]; then
        if python_ok "$CODEX_KOR_TO_ENG_PYTHON_BIN"; then
            printf '%s\n' "$CODEX_KOR_TO_ENG_PYTHON_BIN"
            return 0
        fi
        printf '%s\n' "CODEX_KOR_TO_ENG_PYTHON_BIN is not Python $MIN_MAJOR.$MIN_MINOR+: $CODEX_KOR_TO_ENG_PYTHON_BIN" >&2
        return 1
    fi

    if [ "${CODEX_KOR_TO_ENG_BOOTSTRAP_FORCE_PORTABLE:-}" = "1" ]; then
        return 2
    fi

    if command -v python3 >/dev/null 2>&1 && python_ok "$(command -v python3)"; then
        command -v python3
        return 0
    fi
    if command -v python >/dev/null 2>&1 && python_ok "$(command -v python)"; then
        command -v python
        return 0
    fi
    return 2
}

asset_for_platform() {
    os=${CODEX_KOR_TO_ENG_TEST_OS:-$(uname -s)}
    arch=${CODEX_KOR_TO_ENG_TEST_ARCH:-$(uname -m)}

    if [ "$os" = "Darwin" ] && [ "$arch" = "arm64" ]; then
        printf '%s|%s|%s|%s\n' \
            "cpython-$PY_VERSION+$PY_RELEASE-aarch64-apple-darwin-install_only_stripped.tar.gz" \
            "41df7d3ae4757e84b97874f76d634268456aaa271740d33f968d826374998fb7" \
            "cpython-$PY_VERSION-macos-arm64" \
            "python/bin/python3"
        return 0
    fi
    if [ "$os" = "Darwin" ] && [ "$arch" = "x86_64" ]; then
        printf '%s\n' "Intel macOS is not supported by Lazy Eng Study Codex portable Python bootstrap." >&2
        return 1
    fi
    printf '%s\n' "unsupported platform for portable Python: $os/$arch" >&2
    return 1
}

sha256_ok() {
    file=$1
    expected=$2
    actual=$(shasum -a 256 "$file" | awk '{print $1}')
    [ "$actual" = "$expected" ]
}

ensure_portable_python() {
    root=$(runtime_root)
    if ! asset_line=$(asset_for_platform); then
        return 1
    fi
    asset_name=$(printf '%s' "$asset_line" | cut -d '|' -f 1)
    asset_sha=$(printf '%s' "$asset_line" | cut -d '|' -f 2)
    runtime_name=$(printf '%s' "$asset_line" | cut -d '|' -f 3)
    python_rel=$(printf '%s' "$asset_line" | cut -d '|' -f 4)
    target="$root/$runtime_name"
    python_bin="$target/$python_rel"

    if [ -x "$python_bin" ] && python_ok "$python_bin"; then
        printf '%s\n' "$python_bin"
        return 0
    fi

    mkdir -p "$root/downloads"
    archive="$root/downloads/$asset_name"
    if [ -f "$archive" ] && ! sha256_ok "$archive" "$asset_sha"; then
        rm -f "$archive"
    fi
    if [ ! -f "$archive" ]; then
        escaped_asset=$(printf '%s' "$asset_name" | sed 's/+/%2B/g')
        curl -fsSL "$(download_root)/$escaped_asset" -o "$archive"
    fi
    if ! sha256_ok "$archive" "$asset_sha"; then
        printf '%s\n' "portable Python SHA256 mismatch: $archive" >&2
        return 1
    fi

    tmp="$root/extract.$$"
    target_tmp="$target.tmp.$$"
    rm -rf "$tmp" "$target_tmp"
    mkdir -p "$tmp" "$target_tmp"
    trap 'rm -rf "$tmp" "$target_tmp"' EXIT HUP INT TERM
    tar -xzf "$archive" -C "$tmp"
    mv "$tmp/python" "$target_tmp/python"
    rm -rf "$target"
    mv "$target_tmp" "$target"

    if ! python_ok "$python_bin"; then
        printf '%s\n' "portable Python is not usable after extraction: $python_bin" >&2
        return 1
    fi
    printf '%s\n' "$python_bin"
}

source=system
status=0
python_bin=$(system_python) || status=$?
status=${status:-0}
if [ "$status" = "2" ]; then
    source=portable
    python_bin=$(ensure_portable_python)
elif [ "$status" != "0" ]; then
    exit "$status"
fi

if [ "${1:-}" = "--ensure-python" ]; then
    printf 'python_source=%s\n' "$source"
    printf 'python_bin=%s\n' "$python_bin"
    printf 'runtime_dir=%s\n' "$(runtime_root)"
    exit 0
fi

script_name=${1:-kor_to_eng_hook.py}
if [ "$#" -gt 0 ]; then
    shift
fi
case "$script_name" in
    /*) script_path=$script_name ;;
    *) script_path="$script_dir/$script_name" ;;
esac

exec "$python_bin" "$script_path" "$@"
