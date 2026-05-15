#!/bin/bash
set -euo pipefail

echo "=== Sovereignty Bridge Installer ==="

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This installer currently supports macOS launchd + Secure Enclave setup only." >&2
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_SRC="$REPO_DIR/SecureEnclaveHelper.swift"
HELPER_BIN="$REPO_DIR/secure-enclave-helper"
BRIDGE_SCRIPT="$REPO_DIR/bridge.py"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
PLIST_PATH="/Library/LaunchDaemons/com.sovereignty.bridge.plist"
NEWSYSLOG_PATH="/etc/newsyslog.d/sovereignty-bridge.conf"
LOG_DIR="/usr/local/var/log"
STDOUT_LOG="$LOG_DIR/sovereignty-bridge.log"
STDERR_LOG="$LOG_DIR/sovereignty-bridge.error.log"

if [ -z "$PYTHON_BIN" ]; then
    echo "python3 is required but was not found in PATH." >&2
    exit 1
fi

if [ ! -f "$BRIDGE_SCRIPT" ]; then
    echo "bridge.py was not found at $BRIDGE_SCRIPT" >&2
    exit 1
fi

mkdir -p "$LOG_DIR"

if [ -f "$HELPER_SRC" ]; then
    if ! command -v swiftc >/dev/null 2>&1; then
        echo "swiftc is required to compile SecureEnclaveHelper.swift." >&2
        exit 1
    fi
    swiftc -o "$HELPER_BIN" "$HELPER_SRC"
    chmod +x "$HELPER_BIN"
fi

if [ -x "$HELPER_BIN" ]; then
    "$HELPER_BIN" generate || true
fi

sudo tee "$PLIST_PATH" > /dev/null <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sovereignty.bridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$BRIDGE_SCRIPT</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>PYTHONPATH</key>
        <string>$REPO_DIR:$REPO_DIR/backend</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$STDOUT_LOG</string>
    <key>StandardErrorPath</key>
    <string>$STDERR_LOG</string>
</dict>
</plist>
PLIST

sudo tee "$NEWSYSLOG_PATH" > /dev/null <<EOF
$STDOUT_LOG 640 7 1024 * JC
$STDERR_LOG 640 7 1024 * JC
EOF

sudo launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
sudo launchctl load "$PLIST_PATH"

echo "Installation complete"
