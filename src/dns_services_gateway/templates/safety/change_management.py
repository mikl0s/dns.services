"""Change management system for DNS template configurations."""
import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from ..models.settings import ChangeManagementSettings
from .rollback import ChangeSet


class ChangeStatus(str, Enum):
    """Change status enumeration."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Change:
    """Represents a change request."""

    def __init__(self, changeset: ChangeSet, requester: str, description: str):
        """Initialize change request.

        Args:
            changeset: Change set
            requester: Person requesting change
            description: Change description
        """
        self.id = self._generate_id()
        self.changeset = changeset
        self.requester = requester
        self.description = description
        self.status = ChangeStatus.PENDING
        self.approver: Optional[str] = None
        self.applied_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at

    def _generate_id(self) -> str:
        """Generate unique change ID.

        Returns:
            Change ID
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"CHG_{timestamp}"

    def to_dict(self) -> Dict:
        """Convert change to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "changeset": self.changeset.to_dict(),
            "requester": self.requester,
            "description": self.description,
            "status": self.status.value,
            "approver": self.approver,
            "applied_at": (self.applied_at.isoformat() if self.applied_at else None),
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Change":
        """Create change from dictionary.

        Args:
            data: Dictionary data

        Returns:
            Change instance
        """
        changeset = ChangeSet.from_dict(data["changeset"])
        change = cls(changeset, data["requester"], data["description"])

        change.id = data["id"]
        change.status = ChangeStatus(data["status"])
        change.approver = data["approver"]
        change.applied_at = (
            datetime.fromisoformat(data["applied_at"]) if data["applied_at"] else None
        )
        change.error = data["error"]
        change.created_at = datetime.fromisoformat(data["created_at"])
        change.updated_at = datetime.fromisoformat(data["updated_at"])

        return change


class ChangeManager:
    """Manages DNS record changes."""

    def __init__(
        self,
        changes_dir: str,
        settings: ChangeManagementSettings,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize change manager.

        Args:
            changes_dir: Directory for storing changes
            settings: Change management settings
            logger: Optional logger instance
        """
        self.changes_dir = Path(changes_dir)
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self._ensure_changes_dir()

    def _ensure_changes_dir(self) -> None:
        """Ensure changes directory exists."""
        self.changes_dir.mkdir(parents=True, exist_ok=True)

    def create_change(
        self, changeset: ChangeSet, requester: str, description: str
    ) -> Change:
        """Create a new change request.

        Args:
            changeset: Change set
            requester: Person requesting change
            description: Change description

        Returns:
            Created change
        """
        change = Change(changeset, requester, description)
        self._save_change(change)
        self._notify_change(change, "created")
        return change

    def approve_change(self, change_id: str, approver: str) -> Optional[Change]:
        """Approve a change request.

        Args:
            change_id: Change ID
            approver: Person approving change

        Returns:
            Updated change if found, None otherwise
        """
        change = self.get_change(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.PENDING:
            raise ValueError(
                f"Change {change_id} cannot be approved in " f"status {change.status}"
            )

        change.status = ChangeStatus.APPROVED
        change.approver = approver
        change.updated_at = datetime.utcnow()

        self._save_change(change)
        self._notify_change(change, "approved")
        return change

    def reject_change(
        self, change_id: str, approver: str, reason: str
    ) -> Optional[Change]:
        """Reject a change request.

        Args:
            change_id: Change ID
            approver: Person rejecting change
            reason: Rejection reason

        Returns:
            Updated change if found, None otherwise
        """
        change = self.get_change(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.PENDING:
            raise ValueError(
                f"Change {change_id} cannot be rejected in " f"status {change.status}"
            )

        change.status = ChangeStatus.REJECTED
        change.approver = approver
        change.error = reason
        change.updated_at = datetime.utcnow()

        self._save_change(change)
        self._notify_change(change, "rejected")
        return change

    def apply_change(self, change_id: str) -> Optional[Change]:
        """Mark a change as applied.

        Args:
            change_id: Change ID

        Returns:
            Updated change if found, None otherwise
        """
        change = self.get_change(change_id)
        if not change:
            return None

        if change.status != ChangeStatus.APPROVED:
            raise ValueError(f"Change {change_id} must be approved before applying")

        change.status = ChangeStatus.APPLIED
        change.applied_at = datetime.utcnow()
        change.updated_at = datetime.utcnow()

        self._save_change(change)
        self._notify_change(change, "applied")
        return change

    def fail_change(self, change_id: str, error: str) -> Optional[Change]:
        """Mark a change as failed.

        Args:
            change_id: Change ID
            error: Error message

        Returns:
            Updated change if found, None otherwise
        """
        change = self.get_change(change_id)
        if not change:
            return None

        change.status = ChangeStatus.FAILED
        change.error = error
        change.updated_at = datetime.utcnow()

        self._save_change(change)
        self._notify_change(change, "failed")
        return change

    def rollback_change(self, change_id: str) -> Optional[Change]:
        """Mark a change as rolled back.

        Args:
            change_id: Change ID

        Returns:
            Updated change if found, None otherwise
        """
        change = self.get_change(change_id)
        if not change:
            return None

        change.status = ChangeStatus.ROLLED_BACK
        change.updated_at = datetime.utcnow()

        self._save_change(change)
        self._notify_change(change, "rolled back")
        return change

    def get_change(self, change_id: str) -> Optional[Change]:
        """Get a change by ID.

        Args:
            change_id: Change ID

        Returns:
            Change if found, None otherwise
        """
        change_path = self.changes_dir / f"{change_id}.json"
        if not change_path.exists():
            return None

        with open(change_path, "r") as f:
            data = json.load(f)

        return Change.from_dict(data)

    def list_changes(
        self,
        status: Optional[ChangeStatus] = None,
        domain: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> List[Change]:
        """List changes with optional filters.

        Args:
            status: Optional status filter
            domain: Optional domain filter
            environment: Optional environment filter

        Returns:
            List of matching changes
        """
        changes = []
        for change_file in self.changes_dir.glob("*.json"):
            with open(change_file, "r") as f:
                data = json.load(f)

            change = Change.from_dict(data)

            if status and change.status != status:
                continue

            if domain and change.changeset.domain != domain:
                continue

            if environment and change.changeset.environment != environment:
                continue

            changes.append(change)

        # Sort by creation time (newest first)
        changes.sort(key=lambda x: x.created_at, reverse=True)
        return changes

    def _save_change(self, change: Change) -> None:
        """Save change to file.

        Args:
            change: Change to save
        """
        change_path = self.changes_dir / f"{change.id}.json"
        with open(change_path, "w") as f:
            json.dump(change.to_dict(), f, indent=2)

    def _notify_change(self, change: Change, action: str) -> None:
        """Send notifications for change.

        Args:
            change: Change to notify about
            action: Action that occurred
        """
        if not self.settings.notify:
            return

        message = (
            f"DNS change {change.id} {action}\n"
            f"Domain: {change.changeset.domain}\n"
            f"Environment: {change.changeset.environment}\n"
            f"Requester: {change.requester}\n"
            f"Status: {change.status.value}\n"
            f"Description: {change.description}"
        )

        # Log change
        self.logger.info(message)

        # Send notifications
        if self.settings.notify.email:
            self._send_email_notification(
                self.settings.notify.email,
                f"DNS Change {action.title()}: {change.id}",
                message,
            )

        if self.settings.notify.slack:
            self._send_slack_notification(self.settings.notify.slack, message)

    def _send_email_notification(
        self, recipients: List[str], subject: str, message: str
    ) -> None:
        """Send email notification.

        Args:
            recipients: Email recipients
            subject: Email subject
            message: Email message
        """
        # Implement email sending logic here
        self.logger.info(
            f"Would send email to {recipients}\n"
            f"Subject: {subject}\n"
            f"Message: {message}"
        )

    def _send_slack_notification(self, channels: List[str], message: str) -> None:
        """Send Slack notification.

        Args:
            channels: Slack channels
            message: Message to send
        """
        # Implement Slack notification logic here
        self.logger.info(
            f"Would send Slack message to {channels}\n" f"Message: {message}"
        )
