#!/bin/bash
set -e
echo "=== Sovereignty Bridge Installer ==="
if [ -f "SecureEnclaveHelper.swift" ]; then
    swiftc -o secure-enclave-helper SecureEnclaveHelper.swift
    chmod +x secure-enclave-helper
fi
./secure-enclave-helper generate || true
# launchd + newsyslog setup here
sudo tee /Library/LaunchDaemons/com.sovereignty.bridge.plist > /dev/null << 'PLIST'
... (full plist)
PLIST
sudo tee /etc/newsyslog.d/sovereignty-bridge.conf > /dev/null << 'EOF'
... log rotation
EOF
sudo launchctl load /Library/LaunchDaemons/com.sovereignty.bridge.plist || true
echo "Installation complete"