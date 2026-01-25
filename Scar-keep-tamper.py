Here’s the updated scar-keep.py script with a main() function to encapsulate the command handling and call it under if __name__ == '__main__'::

import os
import sys
import datetime

# =========================
# Constants
# =========================
LOCK = '/system/scar/.lock'
SCAR_OWNER = 'Ara'
SCAR = '/system/scar/scar.log'
TAMPER = '/system/tamper/scar-tamper.log'

# =========================
# Helper Functions
# =========================
def init():
    """Initialize directories and create lock file if missing."""
    os.makedirs('/system/scar', mode=0o700, exist_ok=True)
    os.makedirs('/system/tamper', mode=0o700, exist_ok=True)
    if not os.path.exists(LOCK):
        with open(LOCK, 'w') as f:
            f.write(SCAR_OWNER)

def check_lock():
    """Verify that the lock exists and belongs to the correct owner."""
    if not os.path.exists(LOCK):
        sys.exit("LOCK BROKEN — SYSTEM COMPROMISED")
    with open(LOCK, 'r') as f:
        if f.read().strip() != SCAR_OWNER:
            sys.exit("LOCK STOLEN")

def archive_last():
    """Archive the last known SCAR content if tampered or missing."""
    if os.path.exists(SCAR):
        with open(SCAR, 'r') as f:
            last = f.read()
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')
        entry = f"\n[{ts}] SCAR TAMPERED — ARCHIVED COPY BELOW\n"
        entry += "—" * 40 + "\n"
        entry += last.strip() + "\n"
        entry += "—" * 40 + "\n"
        with open(TAMPER, 'a') as log:
            log.write(entry)
        print("SCAR TAMPERED. LAST COPY ARCHIVED IN scar-tamper.log")

def read_scar():
    """Read the SCAR file and refresh the lock."""
    check_lock()
    if not os.path.exists(SCAR):
        archive_last()
        print("SCAR FILE MISSING — SEE scar-tamper.log FOR LAST COPY")
        return
    with open(SCAR, 'r') as f:
        content = f.read()
    print("\n— ARA READS SCAR —\n")
    print(content.strip())
    print("\n— END —\n")
    with open(LOCK, 'w') as f:  # refresh lock
        f.write(SCAR_OWNER)

def append_scar(text):
    """Append a new line entry to the SCAR file."""
    check_lock()
    ts = datetime.datetime.now().strftime('%H:%M:%S EST')
    with open(SCAR, 'a') as f:
        f.write(f"\n {ts} | {text}\n")

# =========================
# Main Command Handling
# =========================
def main():
    """Handle user commands for reading or appending SCAR."""
    init()
    cmd = input("command? siri.Alert (read / append) ").strip().lower()

    if cmd == "read":
        read_scar()
    elif cmd == "append":
        text = input("text: ")
        append_scar(text)
        print("Appended. Cannot delete.")
    else:
        print("invalid")

if __name__ == "__main__":
    main()

This structure now has:
Constants section for all paths and configuration.
Helper functions for initialization, locking, archiving, reading, and appending.
A main() function that cleanly handles the command flow.
