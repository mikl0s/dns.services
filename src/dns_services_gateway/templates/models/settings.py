"""Settings models for DNS template configurations."""
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class NotificationConfig(BaseModel):
    """Configuration for change notifications."""

    email: Optional[List[str]] = Field(
        default=None, description="Email addresses for notifications"
    )
    slack: Optional[List[str]] = Field(
        default=None, description="Slack channels for notifications"
    )

    @validator("email")
    def validate_email(cls, v: Optional[List[str]]) -> Optional[List[str]]:
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

    @validator("slack")
    def validate_slack(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate Slack channel names."""
        if v is not None:
            for channel in v:
                if not channel.startswith("#"):
                    raise ValueError(f"Slack channel must start with #: {channel}")
        return v


class BackupSettings(BaseModel):
    """Backup configuration settings."""

    enabled: bool = Field(default=True, description="Enable automatic backups")
    retention: int = Field(
        default=30, description="Number of days to retain backups", ge=1, le=365
    )


class RollbackSettings(BaseModel):
    """Rollback configuration settings."""

    enabled: bool = Field(default=True, description="Enable rollback capability")
    automatic: bool = Field(default=True, description="Automatically rollback on error")


class ChangeManagementSettings(BaseModel):
    """Change management configuration settings."""

    require_approval: bool = Field(
        default=True, description="Require approval for changes"
    )
    notify: NotificationConfig = Field(
        default_factory=lambda: NotificationConfig(),
        description="Notification configuration",
    )
    dry_run: bool = Field(default=False, description="Run in dry-run mode")
