"""Base models for DNS template configurations."""
from datetime import datetime
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class MetadataModel(BaseModel):
    """Template metadata information."""

    version: str = Field(..., description="Template version using semantic versioning")
    description: str = Field(..., description="Template description")
    author: str = Field(..., description="Template author")
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(
        default_factory=list, description="Template tags for categorization"
    )

    @validator("version")
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        import re

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        return v


class VariableModel(BaseModel):
    """Template variable definitions."""

    domain: str = Field(..., description="Domain name")
    ttl: int = Field(default=3600, description="Default TTL for records")
    custom_vars: Dict[str, Union[str, int]] = Field(
        default_factory=dict, description="Custom variables for template"
    )

    @validator("ttl")
    def validate_ttl(cls, v: int) -> int:
        """Validate TTL value."""
        if v < 0:
            raise ValueError("TTL must be non-negative")
        return v


class RecordModel(BaseModel):
    """Base model for DNS records."""

    type: str = Field(..., description="Record type (A, AAAA, CNAME, MX, TXT, etc.)")
    name: str = Field(..., description="Record name")
    value: str = Field(..., description="Record value")
    ttl: Optional[int] = Field(None, description="Record-specific TTL")
    description: Optional[str] = Field(None, description="Record description")

    @validator("type")
    def validate_type(cls, v: str) -> str:
        """Validate record type."""
        valid_types = {"A", "AAAA", "CNAME", "MX", "TXT", "CAA", "NS", "PTR", "SRV"}
        if v.upper() not in valid_types:
            raise ValueError(
                f'Invalid record type. Must be one of: {", ".join(valid_types)}'
            )
        return v.upper()


class EnvironmentModel(BaseModel):
    """Environment-specific configuration."""

    name: str = Field(..., description="Environment name")
    variables: Dict[str, Union[str, int]] = Field(
        default_factory=dict, description="Environment-specific variables"
    )
    records: Dict[str, List[RecordModel]] = Field(
        default_factory=dict, description="Environment-specific records"
    )

    @validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate environment name."""
        valid_names = {"production", "staging", "development", "testing"}
        if v.lower() not in valid_names:
            raise ValueError(
                f'Invalid environment name. Must be one of: {", ".join(valid_names)}'
            )
        return v.lower()
