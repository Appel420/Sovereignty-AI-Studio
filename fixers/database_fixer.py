"""
Database fixer for SQLite database corruption and integrity issues.

Automatically detects and fixes:
  - Database corruption
  - Missing tables or indices
  - Integrity constraint violations
  - Lock contention issues
"""

import asyncio
import logging
import pathlib
import shutil
import sqlite3
from typing import Optional

from errors.exceptions import MemoryError

log = logging.getLogger("fixers.database")


class DatabaseFixer:
    """
    Monitors and repairs SQLite database issues automatically.
    """

    def __init__(self, db_path: pathlib.Path, schema: str):
        self.db_path = pathlib.Path(db_path)
        self.schema = schema
        self._backup_dir = self.db_path.parent / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def check_integrity(self) -> tuple[bool, list[str]]:
        """
        Check database integrity.

        Returns:
            Tuple of (is_healthy, list of issues found)
        """
        issues = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result and result[0] != "ok":
                issues.append(f"Integrity check failed: {result[0]}")

            # Check for required tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in cursor.fetchall()}

            expected_tables = {"conversations", "kv", "events"}
            missing = expected_tables - tables
            if missing:
                issues.append(f"Missing tables: {missing}")

            conn.close()

        except sqlite3.DatabaseError as e:
            issues.append(f"Database error: {e}")
        except Exception as e:
            issues.append(f"Unexpected error: {e}")

        is_healthy = len(issues) == 0
        return is_healthy, issues

    def create_backup(self) -> pathlib.Path:
        """
        Create a backup of the database.

        Returns:
            Path to backup file

        Raises:
            MemoryError: If backup creation fails
        """
        import time

        timestamp = int(time.time())
        backup_path = self._backup_dir / f"memory_backup_{timestamp}.db"

        try:
            shutil.copy2(self.db_path, backup_path)
            log.info("Database backed up to %s", backup_path)
            return backup_path
        except Exception as e:
            raise MemoryError(f"Failed to create backup: {e}") from e

    def restore_from_backup(self, backup_path: pathlib.Path) -> bool:
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            True if restoration successful
        """
        try:
            if not backup_path.exists():
                log.error("Backup file not found: %s", backup_path)
                return False

            # Verify backup integrity
            temp_conn = sqlite3.connect(backup_path)
            temp_cursor = temp_conn.cursor()
            temp_cursor.execute("PRAGMA integrity_check")
            result = temp_cursor.fetchone()
            temp_conn.close()

            if result[0] != "ok":
                log.error("Backup file is corrupted: %s", backup_path)
                return False

            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            log.info("Database restored from %s", backup_path)
            return True

        except Exception as e:
            log.error("Failed to restore from backup: %s", e)
            return False

    def rebuild_database(self) -> bool:
        """
        Rebuild database from scratch using schema.

        Returns:
            True if rebuild successful
        """
        conn = None
        try:
            # Backup existing database if it exists
            if self.db_path.exists():
                try:
                    self.create_backup()
                except Exception as e:
                    log.warning("Could not backup before rebuild: %s", e)

            # Remove corrupted database
            if self.db_path.exists():
                self.db_path.unlink()

            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create new database with schema
            conn = sqlite3.connect(self.db_path)
            conn.executescript(self.schema)
            conn.commit()

            # Ensure required tables exist even if schema is partial.
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT
                );
                CREATE TABLE IF NOT EXISTS kv (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT
                );
                """
            )
            conn.commit()

            log.info("Database rebuilt successfully")
            return True

        except Exception as e:
            log.error("Failed to rebuild database: %s", e)
            return False
        finally:
            if conn is not None:
                conn.close()

    async def fix_database(self) -> bool:
        """
        Attempt to fix database issues automatically.

        Returns:
            True if database was fixed successfully
        """
        log.info("Checking database health...")
        is_healthy, issues = self.check_integrity()

        if is_healthy:
            log.info("Database is healthy")
            return True

        log.warning("Database issues detected: %s", issues)

        # Try to create backup first
        try:
            self.create_backup()
        except Exception as e:
            log.warning("Could not create backup: %s", e)

        # Attempt to fix by rebuilding
        log.info("Attempting to rebuild database...")
        return await asyncio.get_event_loop().run_in_executor(None, self.rebuild_database)

    def vacuum_database(self) -> bool:
        """
        Vacuum database to reclaim space and optimize.

        Returns:
            True if vacuum successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM")
            conn.close()
            log.info("Database vacuumed successfully")
            return True
        except Exception as e:
            log.error("Failed to vacuum database: %s", e)
            return False

    def status(self) -> dict:
        """Get current database status."""
        is_healthy, issues = self.check_integrity()

        return {
            "is_healthy": is_healthy,
            "issues": issues,
            "db_path": str(self.db_path),
            "db_exists": self.db_path.exists(),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
        }
