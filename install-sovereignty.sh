#!/bin/bash
set -e
echo "=== Sovereignty Bridge Installer ==="
if [ -f "SecureEnclaveHelper.swift" ]; then
    swiftc -o secure-enclave-helper SecureEnclaveHelper.swift
    chmod +x secure-enclave-helper
fi
./secure-enclave-helper generate || true
# launchd + newsyslog setup here
echo "ERROR: install-sovereignty.sh is missing the real LaunchDaemon plist and newsyslog configuration contents." >&2
echo "Refusing to install placeholder configuration into /Library/LaunchDaemons or /etc/newsyslog.d." >&2
echo "Please replace the placeholder heredocs with the full com.sovereignty.bridge.plist and sovereignty-bridge.conf contents, then rerun this installer." >&2
exit 1
echo "Installation complete"