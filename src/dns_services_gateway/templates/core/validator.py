"""Template validator for DNS configurations."""

import re
import ipaddress
from typing import Dict, List, Any, Optional, Union, Set
from pydantic import ValidationInfo

from ..models.base import (
    EnvironmentModel,
    MetadataModel,
    RecordModel,
    SingleVariableModel,
    VariableModel,
    ValidationResult,
    Template,
)
from ...exceptions import ValidationError


class TemplateValidator:
    """Template validator for DNS configurations."""

    def __init__(self, template_data: Optional[Dict[str, Any]] = None):
        """Initialize template validator.

        Args:
            template_data: Template data to validate
        """
        self.template_data = template_data or {}
        self.variables = set()
        self.environment_names = set()

    async def validate_template(
        self,
        metadata: Optional[MetadataModel] = None,
        variables: Optional[List[SingleVariableModel]] = None,
        environments: Optional[Dict[str, Any]] = None,
        records: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> ValidationResult:
        """Validate entire template configuration.

        Args:
            metadata: Template metadata
            variables: Template variables
            environments: Template environments
            records: Template DNS records

        Returns:
            ValidationResult: Validation result with any errors
        """
        result = ValidationResult()

        try:
            # Update template data with provided components
            if metadata:
                self.template_data["metadata"] = metadata.model_dump()
            if variables:
                self.template_data["variables"] = {
                    var.name: var.value for var in variables
                }
            if environments is not None:
                self.template_data["environments"] = environments
            if records is not None:
                self.template_data["records"] = records

            # Validate metadata
            metadata_result = await self.validate_metadata(metadata)
            result.merge(metadata_result)

            # Validate variables and store them for reference validation
            variables_result = await self.validate_variables(variables)
            result.merge(variables_result)

            # Check for required variables
            template_vars = self.template_data.get("variables", {})
            if "domain" not in template_vars:
                result.add_error("Missing required variable: domain")
            if "ip" not in template_vars:
                result.add_error("Missing required variable: ip")

            # Validate environments
            env_result = await self.validate_environments()
            result.merge(env_result)

            # Validate records
            records_result = await self._validate_records(records)
            result.merge(records_result)

            # Validate variable references
            refs_result = await self.validate_variable_references()
            result.merge(refs_result)

        except ValidationError as e:
            result.add_error(str(e))
        except Exception as e:
            result.add_error(f"Template validation failed: {str(e)}")

        return result

    async def validate_metadata(
        self, metadata: Optional[MetadataModel] = None
    ) -> ValidationResult:
        """Validate template metadata.

        Args:
            metadata: Template metadata to validate

        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult()

        try:
            if metadata:
                # Validate version format
                version = metadata.version
                if not re.match(r"^\d+\.\d+\.\d+$", version):
                    result.add_error(
                        "Version must follow semantic versioning (e.g., 1.0.0)"
                    )
                    return result
                return result

            if "metadata" not in self.template_data:
                result.add_error("Missing metadata section")
                return result

            meta_dict = self.template_data["metadata"]
            if "version" in meta_dict:
                version = meta_dict["version"]
                if not re.match(r"^\d+\.\d+\.\d+$", version):
                    result.add_error(
                        "Version must follow semantic versioning (e.g., 1.0.0)"
                    )
                    return result

            MetadataModel(**meta_dict)

        except Exception as e:
            result.add_error(f"Invalid metadata: {str(e)}")

        return result

    async def validate_variables(
        self,
        variables: Optional[Union[Dict[str, Any], List[SingleVariableModel]]] = None,
    ) -> ValidationResult:
        """Validate template variables.

        Args:
            variables: Variables to validate, either as dict or list of models

        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult()

        if variables is None:
            variables = self.template_data.get("variables", {})

        # Convert list of models to dict if needed
        if isinstance(variables, list):
            variables = {var.name: var.value for var in variables}
            self.template_data["variables"] = variables

        # Handle _descriptions field
        descriptions = {}
        if isinstance(variables, dict):
            descriptions = variables.pop("_descriptions", {}) if variables else {}

        # Update the variables set for reference validation
        base_vars = set()
        if isinstance(variables, dict):
            # Add root level variables
            for key in ["domain", "ttl"]:
                if key in variables:
                    base_vars.add(key)

            # Add custom variables
            custom_vars = variables.get("custom_vars", {})
            for name, var in custom_vars.items():
                if isinstance(var, dict) and "value" in var:
                    base_vars.add(name)
                else:
                    base_vars.add(name)

        self.variables = base_vars

        # Validate each variable
        if isinstance(variables, dict):
            # Validate root level variables
            for name in ["domain", "ttl"]:
                if name in variables:
                    value = variables[name]
                    if not isinstance(name, str):
                        result.add_error(f"Variable name must be a string: {name}")
                        continue

                    if name == "":
                        result.add_error("Variable name cannot be empty")
                        continue

                    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name):
                        result.add_error(
                            f"Invalid variable name '{name}'. Must start with a letter and contain only letters, numbers, and underscores"
                        )

                    # Validate TTL values
                    if name == "ttl":
                        try:
                            ttl = int(value)
                            if ttl < 0:
                                result.add_error("TTL must be non-negative")
                            elif ttl > 2147483647:  # Max 32-bit signed int
                                result.add_error("TTL value is too large")
                        except (ValueError, TypeError):
                            result.add_error("TTL must be a valid integer")

            # Validate custom variables
            custom_vars = variables.get("custom_vars", {})
            for name, var in custom_vars.items():
                if not isinstance(name, str):
                    result.add_error(f"Variable name must be a string: {name}")
                    continue

                if name == "":
                    result.add_error("Variable name cannot be empty")
                    continue

                if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name):
                    result.add_error(
                        f"Invalid variable name '{name}'. Must start with a letter and contain only letters, numbers, and underscores"
                    )

                if isinstance(var, dict):
                    if "value" not in var:
                        result.add_error(
                            f"Custom variable '{name}' must have a 'value' field"
                        )
                    value = var.get("value")
                else:
                    value = var

                # Validate TTL values for any variable named ttl
                if name == "ttl" or name.endswith("_ttl"):
                    try:
                        ttl = int(value)
                        if ttl < 0:
                            result.add_error(
                                f"TTL value for '{name}' must be non-negative"
                            )
                        elif ttl > 2147483647:  # Max 32-bit signed int
                            result.add_error(f"TTL value for '{name}' is too large")
                    except (ValueError, TypeError):
                        result.add_error(
                            f"TTL value for '{name}' must be a valid integer"
                        )

        return result

    async def _validate_records(
        self, records: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> ValidationResult:
        """Internal method to validate template records.

        Args:
            records: Records to validate

        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult()

        if records is None:
            records = self.template_data.get("records", {})

        if not isinstance(records, dict):
            result.add_error("Records must be a dictionary")
            return result

        # First find all A records to check for CNAME conflicts
        seen_names = set()
        for record_type, record_list in records.items():
            if record_type == "A" and isinstance(record_list, list):
                for record in record_list:
                    if isinstance(record, (dict, RecordModel)):
                        name = (
                            record.name
                            if isinstance(record, RecordModel)
                            else record.get("name", "@")
                        )
                        seen_names.add(name)

        # Validate each record
        for record_type, record_list in records.items():
            # Validate record type
            if record_type not in [
                "A",
                "AAAA",
                "CNAME",
                "MX",
                "NS",
                "PTR",
                "SOA",
                "SRV",
                "TXT",
                "CAA",
            ]:
                result.add_error(f"Invalid record type: {record_type}")
                continue

            if not isinstance(record_list, list):
                result.add_error(f"Records for type {record_type} must be a list")
                continue

            for record in record_list:
                try:
                    # Convert RecordModel to dict if needed
                    if isinstance(record, RecordModel):
                        record_dict = {
                            "name": record.name,
                            "value": record.value,
                            "ttl": record.ttl,
                            "type": record.type,
                        }
                    elif isinstance(record, dict):
                        record_dict = dict(record)
                        record_dict["type"] = record_type
                    else:
                        result.add_error("Record must be a dictionary or RecordModel")
                        continue

                    # Validate hostname
                    name = record_dict.get("name", "@")
                    name_result = self.validate_record_name(name)
                    result.merge(name_result)

                    # Check for CNAME conflicts
                    if record_type == "CNAME":
                        if name in seen_names:
                            result.add_error(
                                f"CNAME record conflict: {name} already has an A record"
                            )

                    # Validate record value based on type
                    value = record_dict.get("value", "")
                    value_result = await self.validate_record_value(record_type, value)
                    result.merge(value_result)

                    # Check variable references
                    for field in ["value", "ttl"]:
                        if field in record_dict:
                            value = str(record_dict[field])
                            refs = self.find_variable_references(value)
                            for ref in refs:
                                if ref not in self.variables:
                                    result.add_error(
                                        f"Undefined variable reference in record: {ref}"
                                    )

                except Exception as e:
                    result.add_error(f"Record validation failed: {str(e)}")

        return result

    async def validate_record_value(
        self, record_type: str, value: str
    ) -> ValidationResult:
        """Validate a record value based on its type.

        Args:
            record_type: Type of the record (A, AAAA, CNAME, etc.)
            value: Value to validate

        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult()

        try:
            # Skip validation if using variable reference
            if self.find_variable_references(value):
                return result

            if record_type == "A":
                try:
                    ip = ipaddress.IPv4Address(value)
                except ValueError:
                    result.add_error(f"Invalid IPv4 address: {value}")

            elif record_type == "AAAA":
                try:
                    ip = ipaddress.IPv6Address(value)
                except ValueError:
                    result.add_error(f"Invalid IPv6 address: {value}")

            elif record_type == "CNAME":
                if not self.is_valid_hostname(value) and value != "@":
                    result.add_error(f"Invalid hostname in CNAME record: {value}")

            elif record_type == "MX":
                if not self.is_valid_hostname(value):
                    result.add_error(f"Invalid hostname in MX record: {value}")

            elif record_type == "SRV":
                parts = value.split(" ")
                if len(parts) != 4:
                    result.add_error(
                        "SRV record must have priority, weight, port, and target"
                    )
                else:
                    try:
                        priority, weight, port = map(int, parts[:3])
                        target = parts[3]
                        if any(x < 0 for x in [priority, weight, port]):
                            result.add_error(
                                "SRV priority, weight, and port must be non-negative"
                            )
                        if not self.is_valid_hostname(target):
                            result.add_error(
                                f"Invalid hostname in SRV target: {target}"
                            )
                    except ValueError:
                        result.add_error(
                            "SRV priority, weight, and port must be integers"
                        )

            elif record_type == "CAA":
                parts = value.split(" ", 2)
                if len(parts) != 3:
                    result.add_error("CAA record must have flag, tag, and value")
                else:
                    flag, tag, caa_value = parts
                    if not flag.isdigit() or int(flag) not in [0, 128]:
                        result.add_error("CAA flag must be 0 or 128")
                    if tag not in ["issue", "issuewild", "iodef"]:
                        result.add_error("CAA tag must be issue, issuewild, or iodef")

            elif record_type == "NS":
                if not self.is_valid_hostname(value):
                    result.add_error(f"Invalid hostname in NS record: {value}")

            elif record_type == "PTR":
                if not self.is_valid_hostname(value):
                    result.add_error(f"Invalid hostname in PTR record: {value}")

            elif record_type == "SOA":
                parts = value.split(" ")
                if len(parts) != 7:
                    result.add_error("SOA record must have all required fields")
                else:
                    if not self.is_valid_hostname(parts[0]):
                        result.add_error("Invalid primary nameserver in SOA record")
                    if not self.is_valid_hostname(parts[1]):
                        result.add_error("Invalid hostmaster in SOA record")
                    # Validate serial, refresh, retry, expire, minimum
                    for i, field in enumerate(
                        ["serial", "refresh", "retry", "expire", "minimum"]
                    ):
                        try:
                            val = int(parts[i + 2])
                            if val < 0:
                                result.add_error(f"SOA {field} must be non-negative")
                        except ValueError:
                            result.add_error(f"SOA {field} must be an integer")

        except Exception as e:
            result.add_error(f"Record value validation failed: {str(e)}")

        return result

    async def validate_environments(self) -> ValidationResult:
        """Validate template environments.

        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult()
        if "environments" not in self.template_data:
            return result  # Environments are optional

        environments = self.template_data["environments"]
        if not isinstance(environments, dict):
            result.add_error("Environments must be a dictionary")
            return result

        seen_env_names = set()
        for env_name, env_data in environments.items():
            try:
                # Check for duplicate environment names
                env_display_name = env_data.get("name", env_name)
                if env_display_name in seen_env_names:
                    result.add_error(f"Duplicate environment name: {env_display_name}")
                seen_env_names.add(env_display_name)

                # Create a copy of env_data to avoid modifying the original
                env_dict = dict(env_data)
                env_dict["name"] = env_display_name

                env_model = EnvironmentModel(**env_dict)

                # Validate environment variables
                if "variables" in env_dict:
                    for var_name, var_value in env_dict["variables"].items():
                        if isinstance(var_value, str):
                            refs = self.find_variable_references(var_value)
                            for ref in refs:
                                # Check if reference is to a global variable
                                if "." in ref:
                                    scope, var = ref.split(".", 1)
                                    if scope == "global":
                                        if var not in self.template_data.get(
                                            "variables", {}
                                        ):
                                            result.add_error(
                                                f"Undefined global variable reference in environment {env_name}: {var}"
                                            )
                                    else:
                                        result.add_error(
                                            f"Invalid variable scope in environment {env_name}: {scope}"
                                        )
                                else:
                                    if ref not in self.variables:
                                        result.add_error(
                                            f"Undefined variable reference in environment {env_name}: {ref}"
                                        )

            except Exception as e:
                result.add_error(f"Invalid environment {env_name}: {str(e)}")

        return result

    def is_valid_hostname(self, hostname: str) -> bool:
        """Check if a hostname is valid.

        Args:
            hostname: Hostname to validate

        Returns:
            bool: True if hostname is valid, False otherwise
        """
        if not hostname:
            return False

        if hostname == "@":
            return True

        if len(hostname) > 255:
            return False

        if hostname[-1] == ".":
            hostname = hostname[:-1]

        if hostname[0] == "-" or hostname[-1] == "-":
            return False

        labels = hostname.split(".")
        for label in labels:
            if not label:  # Empty label (consecutive dots)
                return False
            if label.startswith("-") or label.endswith("-"):
                return False
            if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$", label):
                return False
        return True

    def find_variable_references(self, text: str) -> Set[str]:
        """Find variable references in a string.

        Args:
            text: Text to search for variable references

        Returns:
            Set of variable references found
        """
        if not text:
            return set()

        refs = set()

        # Match ${var} pattern
        pattern1 = r"\${([^}]+)}"
        matches1 = re.findall(pattern1, text)
        refs.update(matches1)

        # Match {{variables.var}} pattern
        pattern2 = r"\{\{variables\.([^}]+)\}\}"
        matches2 = re.findall(pattern2, text)
        refs.update(matches2)

        return refs

    def strip_variable_syntax(self, ref: str) -> str:
        """Strip variable reference syntax.

        Args:
            ref: Variable reference with syntax (e.g., ${var} or {{variables.var}})

        Returns:
            Variable name without syntax
        """
        if ref.startswith("${") and ref.endswith("}"):
            return ref[2:-1]
        if ref.startswith("{{variables.") and ref.endswith("}}"):
            return ref[12:-2]
        return ref

    def validate_record_name(self, name: str) -> ValidationResult:
        """Validate record name.

        Args:
            name: Record name to validate

        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult()
        if not self.is_valid_hostname(name):
            result.add_error(f"Invalid hostname: {name}")
        return result

    async def validate_variable_references(
        self,
        references: Optional[Union[Set[str], List[str]]] = None,
        valid_vars: Optional[Union[Set[str], List[str]]] = None,
    ) -> ValidationResult:
        """Validate variable references.

        Args:
            references: Optional set or list of variable references to validate
            valid_vars: Optional set or list of valid variable names

        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult()

        # Convert inputs to sets if needed
        if references is not None:
            references = {self.strip_variable_syntax(ref) for ref in references}
        if valid_vars is not None:
            valid_vars = set(valid_vars)

        # If references and valid_vars are provided directly, validate them
        if references is not None:
            if valid_vars is None:
                valid_vars = self.variables

            for ref in references:
                if ref not in valid_vars:
                    result.add_error(f"Undefined variable reference: {ref}")
            return result

        # Otherwise, validate all references in the template
        all_refs = set()

        # Collect all variable references from records
        if "records" in self.template_data:
            for record_list in self.template_data["records"].values():
                for record in record_list:
                    if isinstance(record, dict):
                        for field in ["value", "ttl"]:
                            if field in record:
                                value = str(record[field])
                                refs = self.find_variable_references(value)
                                all_refs.update(refs)

        # Collect all variable references from environments
        if "environments" in self.template_data:
            for env_data in self.template_data["environments"].values():
                if isinstance(env_data, dict) and "variables" in env_data:
                    for var_value in env_data["variables"].values():
                        if isinstance(var_value, str):
                            refs = self.find_variable_references(var_value)
                            all_refs.update(refs)

        # Validate all collected references
        for ref in all_refs:
            ref = self.strip_variable_syntax(ref)
            if ref not in self.variables:
                result.add_error(f"Undefined variable reference: {ref}")

        return result
