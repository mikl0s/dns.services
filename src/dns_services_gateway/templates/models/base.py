"""Base models for DNS template configurations."""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator, ValidationInfo
import re
import ipaddress
from dns_services_gateway.exceptions import ValidationError


class MetadataModel(BaseModel):
    """Template metadata information."""

    name: Optional[str] = None
    version: str = Field(..., description="Template version using semantic versioning")
    description: str = Field(..., description="Template description")
    author: str = Field(..., description="Template author")
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(
        default_factory=list, description="Template tags for categorization"
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str, info: ValidationInfo) -> str:
        """Validate semantic version format."""
        if not v:
            raise ValueError("Version cannot be empty")
        # Check for semantic version format (x.y.z)
        if not re.match(
            r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$",
            v,
        ):
            raise ValueError("Version must follow semantic versioning")
        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = super().model_dump(**kwargs)
        # Convert datetime objects to ISO format strings
        for key in ["created", "updated"]:
            if key in data and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return data


class SingleVariableModel(BaseModel):
    """Model for a single variable definition."""

    name: Optional[str] = Field(None, description="Variable name")
    value: Any = Field(..., description="Variable value")
    description: str = Field("", description="Variable description")
    domain: Optional[str] = Field(None, description="Variable domain scope")
    ttl: Optional[int] = Field(None, description="Variable TTL")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Any, info: ValidationInfo) -> Any:
        """Validate value."""
        # Allow any type of value, but ensure it can be converted to string
        try:
            str(v)
            return v
        except Exception as e:
            raise ValueError(f"Value must be convertible to string: {str(e)}")

    @field_validator("ttl")
    @classmethod
    def validate_ttl(cls, v: Optional[int], info: ValidationInfo) -> Optional[int]:
        """Validate TTL value."""
        if v is not None:
            if not isinstance(v, int):
                try:
                    v = int(v)
                except (ValueError, TypeError):
                    raise ValueError("TTL must be a valid integer")
            if v < 0:
                raise ValueError("TTL must be non-negative")
        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = super().model_dump(**kwargs)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    def __str__(self) -> str:
        """Return string representation of variable value."""
        return str(self.value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the model.

        Args:
            key: Key to get
            default: Default value if key not found

        Returns:
            Value if found, default otherwise
        """
        if hasattr(self, key):
            return getattr(self, key)
        return default

    class Config:
        validate_assignment = True
        extra = "allow"  # Allow extra fields for future use


class VariableModel(BaseModel):
    """Model for template variables."""

    domain: str = Field(..., description="Domain name")
    ttl: int = Field(..., description="Default TTL")
    nameservers: List[str] = Field(
        default_factory=list, description="List of nameservers"
    )
    custom_vars: Dict[str, Any] = Field(
        default_factory=dict, description="Custom variables"
    )
    descriptions: Dict[str, str] = Field(
        default_factory=lambda: {"domain": "Domain name", "ttl": "Default TTL"},
        description="Variable descriptions",
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str, info: ValidationInfo) -> str:
        """Validate domain name."""
        if not v:
            raise ValueError("Domain cannot be empty")
        if not re.match(
            r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
            v,
        ):
            raise ValueError("Invalid domain name format")
        return v

    @field_validator("ttl")
    @classmethod
    def validate_ttl(cls, v: int, info: ValidationInfo) -> int:
        """Validate TTL value."""
        if not isinstance(v, int):
            try:
                v = int(v)
            except (ValueError, TypeError):
                raise ValueError("TTL must be a valid integer")
        if v < 0:
            raise ValueError("TTL must be non-negative")
        return v

    @field_validator("nameservers")
    @classmethod
    def validate_nameservers(cls, v: List[str], info: ValidationInfo) -> List[str]:
        """Validate nameserver list."""
        if not v:
            return v
        for ns in v:
            if not re.match(
                r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
                ns,
            ):
                raise ValueError(f"Invalid nameserver format: {ns}")
        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = super().model_dump(**kwargs)
        # Combine custom_vars with main fields
        if "custom_vars" in data:
            custom_vars = data.pop("custom_vars")
            data.update(custom_vars)
        return data


class RecordModel(BaseModel):
    """DNS record model."""

    type: str
    name: str
    value: str
    ttl: Union[int, str] = 3600
    priority: Optional[Union[int, str]] = None
    weight: Optional[Union[int, str]] = None
    port: Optional[Union[int, str]] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str, info: ValidationInfo) -> str:
        """Basic name validation."""
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("ttl")
    @classmethod
    def validate_ttl(cls, v: Union[int, str], info: ValidationInfo) -> Union[int, str]:
        """Basic TTL validation."""
        # Skip validation if the value is a string containing variable references
        if isinstance(v, str) and ("${" in v or "{{" in v):
            return v
        try:
            if not isinstance(v, int):
                v = int(v)
            if v < 0:
                raise ValueError("TTL must be non-negative")
            return v
        except (ValueError, TypeError):
            raise ValueError("TTL must be a valid integer")

    @field_validator("priority", "weight", "port")
    @classmethod
    def validate_numeric(
        cls, v: Optional[Union[int, str]], info: ValidationInfo
    ) -> Optional[Union[int, str]]:
        """Basic numeric field validation."""
        if v is None:
            return v
        # Skip validation if the value is a string containing variable references
        if isinstance(v, str) and ("${" in v or "{{" in v):
            return v
        try:
            if not isinstance(v, int):
                v = int(v)
            return v
        except (ValueError, TypeError):
            raise ValueError(f"{info.field_name} must be a valid integer")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str, info: ValidationInfo) -> str:
        """Basic value validation."""
        if not v and info.data.get("type") not in ["TXT", "NS"]:
            raise ValueError("Value cannot be empty")
        return v


class ValidationResult:
    """Result of template validation."""

    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None):
        """Initialize validation result.

        Args:
            is_valid: Whether the validation passed
            errors: List of validation errors
        """
        self.errors = errors or []
        self._is_valid = is_valid

    @property
    def is_valid(self) -> bool:
        """Get validation status.

        Returns:
            bool: Whether the validation passed
        """
        return self._is_valid and not self.errors

    def add_error(self, error: str) -> None:
        """Add validation error.

        Args:
            error: Error message to add
        """
        if error not in self.errors:  # Avoid duplicate error messages
            self.errors.append(error)
            self._is_valid = False

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one.

        Args:
            other: Other validation result to merge
        """
        if not other.is_valid:
            self._is_valid = False
            for error in other.errors:
                if error not in self.errors:  # Avoid duplicate error messages
                    self.errors.append(error)

    def __bool__(self) -> bool:
        """Return validation status.

        Returns:
            bool: Whether the validation passed
        """
        return self.is_valid

    def __await__(self):
        """Make ValidationResult awaitable.

        Returns:
            Generator that yields self
        """
        yield self
        return self


class EnvironmentModel(BaseModel):
    """Environment model for templates."""

    name: Optional[str] = None
    variables: Dict[str, Union[SingleVariableModel, Dict[str, Any], Any]] = Field(
        default_factory=dict
    )
    records: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None, description="Environment records"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Environment metadata")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate environment name."""
        if v is not None and not v:
            raise ValueError("Environment name cannot be empty")
        return v

    @field_validator("variables")
    @classmethod
    def validate_variables(
        cls, v: Dict[str, Any], info: ValidationInfo
    ) -> Dict[str, Any]:
        """Validate environment variables."""
        validated = {}
        for key, value in v.items():
            if isinstance(value, dict):
                try:
                    if "value" in value:
                        validated[key] = SingleVariableModel(
                            name=key,
                            value=str(value["value"]),
                            description=value.get("description", ""),
                        )
                    else:
                        validated[key] = SingleVariableModel(
                            name=key,
                            value=str(value),
                            description="",
                        )
                except Exception as e:
                    # If not a valid SingleVariableModel, convert to string
                    validated[key] = SingleVariableModel(
                        name=key,
                        value=str(value),
                        description="",
                    )
            else:
                validated[key] = SingleVariableModel(
                    name=key,
                    value=str(value),
                    description="",
                )
        return validated

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Dump environment model to dictionary."""
        data = super().model_dump(**kwargs)
        # Convert SingleVariableModel instances to dictionaries
        if "variables" in data:
            variables = {}
            for key, value in data["variables"].items():
                if isinstance(value, SingleVariableModel):
                    variables[key] = value.model_dump()
                else:
                    variables[key] = value
            data["variables"] = variables
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentModel":
        """Create environment model from dictionary.

        Args:
            data: Environment data

        Returns:
            EnvironmentModel instance
        """
        if not isinstance(data, dict):
            raise ValueError("Environment data must be a dictionary")

        # Handle variables specially
        if "variables" in data:
            variables = {}
            for key, value in data["variables"].items():
                if isinstance(value, dict):
                    try:
                        variables[key] = SingleVariableModel(**value)
                    except Exception:
                        variables[key] = value
                else:
                    variables[key] = value
            data["variables"] = variables

        return cls(**data)


class Template(BaseModel):
    """Template configuration model."""

    metadata: Optional[MetadataModel] = None
    variables: Optional[Union[VariableModel, Dict[str, Any]]] = None
    environments: Dict[str, Any] = Field(default_factory=dict)
    records: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("variables")
    @classmethod
    def validate_variables(
        cls, v: Optional[Union[VariableModel, Dict[str, Any]]], info: ValidationInfo
    ) -> Optional[Union[VariableModel, Dict[str, Any]]]:
        """Validate template variables."""
        if v is None:
            return None

        if isinstance(v, VariableModel):
            return v

        if not isinstance(v, dict):
            raise ValueError("Template variables must be a dictionary")

        # Convert simple values to SingleVariableModel instances
        variables = {}
        for key, value in v.items():
            if isinstance(value, SingleVariableModel):
                variables[key] = value
            elif isinstance(value, dict):
                if "value" in value:
                    # Handle nested variable structure
                    variables[key] = SingleVariableModel(
                        name=key,
                        value=value["value"],
                        description=value.get("description", ""),
                    )
                else:
                    # Convert to SingleVariableModel with the dict as value
                    variables[key] = SingleVariableModel(
                        name=key,
                        value=value,
                        description="",
                    )
            else:
                # Convert simple value to SingleVariableModel
                variables[key] = SingleVariableModel(
                    name=key,
                    value=value,
                    description="",
                )

        return variables

    @field_validator("environments")
    @classmethod
    def validate_environments(
        cls, v: Dict[str, Any], info: ValidationInfo
    ) -> Dict[str, Any]:
        """Validate environments for duplicates."""
        # Check for duplicate environment names
        env_names = set()
        for env_name in v:
            if env_name in env_names:
                raise ValueError(f"Duplicate environment name: {env_name}")
            env_names.add(env_name)
        return v

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = super().model_dump(**kwargs)
        # Convert metadata to dict if present
        if self.metadata:
            data["metadata"] = self.metadata.model_dump()
        # Convert variables to dict if present and is VariableModel
        if isinstance(self.variables, VariableModel):
            data["variables"] = self.variables.model_dump()
        return data
