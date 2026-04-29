import json
import os
import hashlib
import time
from pathlib import Path
from typing import Any, Iterator, Optional
from datetime import datetime
import socket
import sys
import shutil
from contextlib import contextmanager
import fcntl  # For file locking

from signature_manager import SignatureManager  # Moved to separate module


class LoggerUtils:
    @staticmethod
    def ensure_logfile(path: Path) -> None:
        """Ensure the log file and its parent directories exist."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()

    @staticmethod
    def write_entry(path: Path, entry: dict[str, Any]) -> None:
        """Append a JSON entry to the log file with proper file locking."""
        with open(path, 'a', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(entry, f)
                f.write('\n')
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    @staticmethod
    def compute_checksum(path: Path) -> str:
        """Compute a SHA256 checksum for the given file."""
        sha = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha.update(chunk)
        return sha.hexdigest()

    @staticmethod
    def count_entries(path: Path) -> int:
        """Count non-empty entries (lines) in the log file."""
        count = 0
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    @staticmethod
    def rotate_log(path: Path, max_size: int) -> None:
        """Rotate the log file if it exceeds the specified size limit."""
        if path.stat().st_size > max_size:
            rotated = path.with_suffix('.1')
            if rotated.exists():
                rotated.unlink()
            shutil.move(str(path), str(rotated))
            path.touch()


class ImmutableLogger:
    def __init__(self, log_file: str = "scar_chain.log", secret_key: Optional[str] = None, max_log_size: int = 10_000_000) -> None:
        self.log_file: Path = Path(log_file)
        self.secret_key: str = secret_key or os.urandom(32).hex()
        self.max_log_size: int = max_log_size
        self.signer: SignatureManager = SignatureManager(self.secret_key)
        LoggerUtils.ensure_logfile(self.log_file)

    # --- Context Manager and File Operations ---

    @contextmanager
    def _entry_context(self) -> Iterator[dict[str, Any]]:
        """Context manager that prepares a log entry, signs it, and writes it safely."""
        entry: dict[str, Any] = {}
        try:
            yield entry
            entry["timestamp"] = time.time()
            entry["signature"] = self.signer.generate_signature(entry)

            LoggerUtils.rotate_log(self.log_file, self.max_log_size)
            LoggerUtils.write_entry(self.log_file, entry)

            total: int = LoggerUtils.count_entries(self.log_file)
            self._log_to_stdout(f"Appended event '{entry.get('event', 'UNKNOWN')}' (Total entries: {total})")
        except Exception as e:
            self._log_to_stdout(f"Failed to append entry: {e}")
            raise

    def append(self, event: str, **fields: Any) -> None:
        """Append a new event entry to the immutable log."""
        with self._entry_context() as entry:
            entry.update({"event": event, **fields})

    def write_boot_entry(self, system_id: str) -> bool:
        """Write a boot event entry and verify log integrity after writing."""
        self.append("BOOT", system_id=system_id, status="BOOT_OK")
        return self.verify_integrity()

    # --- Verification and Output Methods ---

    def verify_integrity(self) -> bool:
        """Verify the cryptographic integrity of the entire log file."""
        return self.signer.verify_log_integrity(self.log_file)

    def checksum(self) -> str:
        """Return the SHA256 checksum of the log file."""
        return LoggerUtils.compute_checksum(self.log_file)

    # === Private/Internal Helper Methods ===
    # These methods are intended for internal use within the class only.

    def _log_to_stdout(self, message: str) -> None:
        """Write a timestamped, host-prefixed message to stdout for debugging and logging."""
        ts: str = datetime.utcnow().isoformat()
        host: str = socket.gethostname()
        pid: int = os.getpid()
        print(f"[{ts}] {host} PID:{pid} - {message}", file=sys.stdout)
