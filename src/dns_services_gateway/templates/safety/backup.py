"""Backup management for DNS template configurations."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..models.base import RecordModel
from ..models.settings import BackupSettings


class BackupManager:
    """Manages DNS record backups."""

    def __init__(self, backup_dir: str, settings: BackupSettings):
        """Initialize backup manager.

        Args:
            backup_dir: Directory for storing backups
            settings: Backup settings
        """
        self.backup_dir = Path(backup_dir)
        self.settings = settings
        self._ensure_backup_dir()

    def _ensure_backup_dir(self) -> None:
        """Ensure backup directory exists."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self, domain: str, records: List[RecordModel], environment: str
    ) -> str:
        """Create a backup of DNS records.

        Args:
            domain: Domain name
            records: List of records to backup
            environment: Environment name

        Returns:
            Backup filename
        """
        if not self.settings.enabled:
            return ""

        # Create backup data
        backup_data: Dict[str, Any] = {
            "domain": domain,
            "environment": environment,
            "timestamp": datetime.utcnow().isoformat(),
            "records": [record.dict() for record in records],
        }

        # Generate backup filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{environment}_{timestamp}.json"
        backup_path = self.backup_dir / filename

        # Write backup file
        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2)

        # Clean up old backups
        self._cleanup_old_backups()

        return filename

    def restore_backup(self, filename: str) -> Optional[Dict[str, List[RecordModel]]]:
        """Restore records from a backup.

        Args:
            filename: Backup filename

        Returns:
            Dictionary of restored records by group, None if backup not found
        """
        backup_path = self.backup_dir / filename
        if not backup_path.exists():
            return None

        # Read backup file
        with open(backup_path, "r") as f:
            backup_data = json.load(f)

        # Convert record dictionaries back to models
        records = []
        for record_dict in backup_data["records"]:
            records.append(RecordModel(**record_dict))

        return {"restored": records}

    def get_latest_backup(self, domain: str, environment: str) -> Optional[str]:
        """Get latest backup for domain and environment.

        Args:
            domain: Domain name
            environment: Environment name

        Returns:
            Latest backup filename if found, None otherwise
        """
        pattern = f"{domain}_{environment}_*.json"
        backups = list(self.backup_dir.glob(pattern))

        if not backups:
            return None

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return backups[0].name

    def list_backups(
        self,
        domain: Optional[str] = None,
        environment: Optional[str] = None,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List available backups.

        Args:
            domain: Optional domain filter
            environment: Optional environment filter
            days: Optional number of days to look back

        Returns:
            List of backup information dictionaries
        """
        pattern = "*.json"
        if domain and environment:
            pattern = f"{domain}_{environment}_*.json"
        elif domain:
            pattern = f"{domain}_*.json"
        elif environment:
            pattern = f"*_{environment}_*.json"

        backups = list(self.backup_dir.glob(pattern))

        # Filter by age if specified
        if days is not None:
            cutoff = datetime.utcnow() - timedelta(days=days)
            backups = [
                b for b in backups if datetime.fromtimestamp(b.stat().st_mtime) > cutoff
            ]

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        return [
            {
                "filename": b.name,
                "timestamp": datetime.fromtimestamp(b.stat().st_mtime).isoformat(),
                "size": b.stat().st_size,
            }
            for b in backups
        ]

    def delete_backup(self, filename: str) -> bool:
        """Delete a backup file.

        Args:
            filename: Backup filename

        Returns:
            True if backup was deleted, False if not found
        """
        backup_path = self.backup_dir / filename
        if not backup_path.exists():
            return False

        os.remove(backup_path)
        return True

    def _cleanup_old_backups(self) -> None:
        """Clean up backups older than retention period."""
        if not self.settings.retention:
            return

        cutoff = datetime.utcnow() - timedelta(days=self.settings.retention)

        for backup in self.backup_dir.glob("*.json"):
            if datetime.fromtimestamp(backup.stat().st_mtime) < cutoff:
                os.remove(backup)
