"""DNS Services Gateway template management package."""

# Import core components to make them available at the package level
from .core.loader import TemplateLoader
from .core.validator import TemplateValidator
from .models.base import (
    MetadataModel,
    VariableModel,
    RecordModel,
    EnvironmentModel,
)
from .models.settings import (
    NotificationConfig,
    BackupSettings,
    RollbackSettings,
    ChangeManagementSettings,
)

__all__ = [
    "TemplateLoader",
    "TemplateValidator",
    "MetadataModel",
    "VariableModel",
    "RecordModel",
    "EnvironmentModel",
    "NotificationConfig",
    "BackupSettings",
    "RollbackSettings",
    "ChangeManagementSettings",
]
