"""Backup management for DNS template configurations."""

import json
import os
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..models.base import RecordModel
from ..models.settings import BackupSettings


class BackupManager:
    """Manages template backups."""

    def __init__(self, settings: BackupSettings):
        """Initialize backup manager.

        Args:
            settings: Backup settings
        """
        self.settings = settings
        self.backup_dir = Path(settings.directory)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, template_data: Dict[str, Any]) -> None:
        """Create a backup of a template.

        Args:
            template_data: Template data to backup
        """
        timestamp = datetime.utcnow().isoformat()
        backup_file = self.backup_dir / f"backup_{timestamp}.yaml"
        with open(backup_file, "w") as f:
            yaml.dump(template_data, f)

    def restore_latest(self) -> Dict[str, Any]:
        """Restore latest backup.

        Returns:
            Template data from backup
        """
        backup_files = sorted(self.backup_dir.glob("backup_*.yaml"))
        if not backup_files:
            raise FileNotFoundError("No backups found")
        latest_backup = backup_files[-1]
        with open(latest_backup, "r") as f:
            return yaml.safe_load(f)

    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups.

        Returns:
            List of backup information
        """
        backups = []
        for backup_file in self.backup_dir.glob("backup_*.yaml"):
            backup_info = {
                "file": backup_file.name,
                "timestamp": backup_file.stat().st_mtime,
                "size": backup_file.stat().st_size,
            }
            backups.append(backup_info)
        return sorted(backups, key=lambda x: x["timestamp"])

    def cleanup_old_backups(self) -> None:
        """Clean up old backups based on retention settings."""
        if not self.settings.retention_days:
            return

        cutoff_time = datetime.utcnow() - timedelta(days=self.settings.retention_days)
        for backup_file in self.backup_dir.glob("backup_*.yaml"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_time:
                backup_file.unlink()
