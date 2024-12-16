"""Settings models for DNS template configurations."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class NotificationConfig(BaseModel):
    """Configuration for change notifications."""

    email: Optional[list[str]] = Field(
        default=None, description="Email addresses for notifications"
    )
    slack: Optional[list[str]] = Field(
        default=None, description="Slack channels for notifications"
    )

    @classmethod
    def validate_email(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate email addresses."""
        if v is not None:
            import re

            email_pattern = re.compile(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )
            for email in v:
                if not email_pattern.match(email):
                    raise ValueError(f"Invalid email address: {email}")
        return v

    @classmethod
    def validate_slack(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate Slack channel names."""
        if v is not None:
            for channel in v:
                if not channel.startswith("#"):
                    raise ValueError(f"Slack channel must start with #: {channel}")
        return v

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default if not found
        """
        return getattr(self, key, default)


class BackupSettings(BaseModel):
    """Backup settings for templates."""

    enabled: bool = Field(default=True, description="Enable backups")
    directory: str = Field(default="backups", description="Backup directory")
    retention_days: int = Field(default=30, description="Backup retention in days")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default if not found
        """
        return getattr(self, key, default)


class RollbackSettings(BaseModel):
    """Rollback settings for templates."""

    enabled: bool = Field(default=True, description="Enable rollback")
    max_changes: int = Field(default=10, description="Maximum changes to track")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default if not found
        """
        return getattr(self, key, default)


class ChangeManagementSettings(BaseModel):
    """Change management settings for templates."""

    enabled: bool = Field(default=True, description="Enable change management")
    changes_dir: str = Field(default="changes", description="Changes directory")
    require_approval: bool = Field(
        default=True, description="Require approval for changes"
    )
    notify: "NotificationConfig" = Field(
        default_factory=NotificationConfig,
        description="Notification configuration",
    )
    dry_run: bool = Field(default=False, description="Run in dry-run mode")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default if not found
        """
        return getattr(self, key, default)
