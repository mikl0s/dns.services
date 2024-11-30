"""Rollback management for DNS templates."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.base import RecordModel


class ChangeSet:
    """Represents a set of DNS record changes."""

    def __init__(self, domain: str = "", environment: str = ""):
        """Initialize change set.

        Args:
            domain: Domain name for the changes
            environment: Environment name for the changes
        """
        self.domain = domain
        self.environment = environment
        self.added: List[RecordModel] = []
        self.updated: List[RecordModel] = []
        self.deleted: List[RecordModel] = []
        self.modified: List[RecordModel] = []
        self.removed: List[RecordModel] = []
        self.timestamp = datetime.utcnow()

    def add_record(self, record: RecordModel) -> None:
        """Add a new record.

        Args:
            record: Record to add
        """
        self.added.append(record)

    def update_record(self, record: RecordModel) -> None:
        """Update an existing record.

        Args:
            record: Record to update
        """
        self.updated.append(record)
        self.modified.append(record)

    def delete_record(self, record: RecordModel) -> None:
        """Delete a record.

        Args:
            record: Record to delete
        """
        self.deleted.append(record)
        self.removed.append(record)

    def is_empty(self) -> bool:
        """Check if change set is empty.

        Returns:
            True if no changes, False otherwise
        """
        return not (self.added or self.updated or self.deleted)

    def to_dict(self) -> Dict:
        """Convert change set to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "domain": self.domain,
            "environment": self.environment,
            "added": [r.dict() for r in self.added],
            "updated": [r.dict() for r in self.updated],
            "deleted": [r.dict() for r in self.deleted],
            "modified": [r.dict() for r in self.modified],
            "removed": [r.dict() for r in self.removed],
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChangeSet":
        """Create change set from dictionary.

        Args:
            data: Dictionary data

        Returns:
            ChangeSet instance
        """
        changeset = cls(
            domain=data.get("domain", ""), environment=data.get("environment", "")
        )
        changeset.added = [RecordModel(**r) for r in data.get("added", [])]
        changeset.updated = [RecordModel(**r) for r in data.get("updated", [])]
        changeset.deleted = [RecordModel(**r) for r in data.get("deleted", [])]
        changeset.modified = [RecordModel(**r) for r in data.get("modified", [])]
        changeset.removed = [RecordModel(**r) for r in data.get("removed", [])]
        changeset.timestamp = datetime.fromisoformat(data["timestamp"])
        return changeset


class RollbackManager:
    """Manages DNS template rollbacks."""

    def __init__(self, rollback_dir: str):
        """Initialize rollback manager.

        Args:
            rollback_dir: Directory for storing rollback data
        """
        self.rollback_dir = Path(rollback_dir)
        self._ensure_rollback_dir()

    def _ensure_rollback_dir(self) -> None:
        """Ensure rollback directory exists."""
        self.rollback_dir.mkdir(parents=True, exist_ok=True)

    def save_changeset(self, change_id: str, changeset: ChangeSet) -> None:
        """Save change set for possible rollback.

        Args:
            change_id: Change ID
            changeset: Change set to save
        """
        path = self.rollback_dir / f"{change_id}.json"
        with path.open("w") as f:
            json.dump(changeset.to_dict(), f, indent=2)

    def load_changeset(self, change_id: str) -> Optional[ChangeSet]:
        """Load change set for rollback.

        Args:
            change_id: Change ID

        Returns:
            ChangeSet if found, None otherwise
        """
        path = self.rollback_dir / f"{change_id}.json"
        if not path.exists():
            return None

        with path.open() as f:
            data = json.load(f)
            return ChangeSet.from_dict(data)

    def delete_changeset(self, change_id: str) -> None:
        """Delete change set.

        Args:
            change_id: Change ID
        """
        path = self.rollback_dir / f"{change_id}.json"
        if path.exists():
            path.unlink()

    def list_changesets(self) -> List[str]:
        """List available change sets.

        Returns:
            List of change IDs
        """
        return [p.stem for p in self.rollback_dir.glob("*.json")]

    def rollback_change(self, change_id: str) -> Optional[ChangeSet]:
        """Create rollback change set.

        Args:
            change_id: Change ID

        Returns:
            Rollback change set if found, None otherwise
        """
        changeset = self.load_changeset(change_id)
        if not changeset:
            return None

        # Create inverse change set
        rollback = ChangeSet(domain=changeset.domain, environment=changeset.environment)

        # Reverse additions (delete them)
        rollback.deleted.extend(changeset.added)
        rollback.removed.extend(changeset.added)

        # Reverse updates (restore previous version)
        rollback.updated.extend(changeset.updated)
        rollback.modified.extend(changeset.updated)

        # Reverse deletions (add them back)
        rollback.added.extend(changeset.deleted)

        return rollback
