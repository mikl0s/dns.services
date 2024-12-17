"""Variable manager for DNS template configurations."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from dns_services_gateway.templates.models.base import (
    VariableModel,
    SingleVariableModel,
)


class VariableManager:
    """Manages variables for DNS templates."""

    def __init__(self, variables: Union[Dict[str, Any], VariableModel, None] = None):
        """Initialize variable manager.

        Args:
            variables: Initial variables
        """
        # Initialize with default values
        self._variables = {
            "domain": "",
            "ttl": 3600,
            "descriptions": {"domain": "Domain name", "ttl": "Default TTL"},
            "custom_vars": {},
        }

        # Update with provided variables
        if variables is not None:
            if isinstance(variables, VariableModel):
                self.update(variables)
            elif isinstance(variables, dict):
                # Update base variables
                if "domain" in variables:
                    self._variables["domain"] = variables["domain"]
                if "ttl" in variables:
                    self._variables["ttl"] = variables["ttl"]
                # Update descriptions if present
                if "descriptions" in variables:
                    desc_val = variables["descriptions"]
                    if isinstance(desc_val, dict):
                        self._variables["descriptions"].update(desc_val)
                # Update custom variables
                if "custom_vars" in variables:
                    if isinstance(variables["custom_vars"], dict):
                        self._variables["custom_vars"] = variables["custom_vars"]
                    else:
                        # If custom_vars is not a dict, try to convert it
                        try:
                            self._variables["custom_vars"] = dict(
                                variables["custom_vars"]
                            )
                        except (TypeError, ValueError):
                            self._variables["custom_vars"] = {}
                else:
                    # Add other variables as custom vars
                    for name, value in variables.items():
                        if name not in ["domain", "ttl", "descriptions", "custom_vars"]:
                            if isinstance(value, dict):
                                self._variables["custom_vars"][name] = value
                            else:
                                self._variables["custom_vars"][name] = {
                                    "value": value,
                                    "description": self._variables["descriptions"].get(
                                        name, ""
                                    ),
                                }

    @property
    def variables(self) -> Dict[str, Any]:
        """Direct access to variables for CLI compatibility."""
        return self._variables

    def get_variables(self, flatten_custom_vars: bool = False) -> Dict[str, Any]:
        """Get all variables.

        Args:
            flatten_custom_vars: If True, include custom variable values directly in result.
                               If False, keep them under 'custom_vars' key.
        """
        result = {
            "domain": self._variables["domain"],
            "ttl": self._variables["ttl"],
            "descriptions": self._variables["descriptions"],
        }
        if "custom_vars" in self._variables:
            if flatten_custom_vars:
                # Include custom variable values directly in the result
                for name, var in self._variables["custom_vars"].items():
                    if isinstance(var, dict) and "value" in var:
                        result[name] = var["value"]
                    else:
                        result[name] = var  # Handle case where var is already a value
            else:
                # Keep custom variables nested under custom_vars
                result["custom_vars"] = self._variables["custom_vars"]
        return result

    def get_variable(self, key: str) -> Optional[SingleVariableModel]:
        """Get a variable value.

        Args:
            key: Variable key

        Returns:
            SingleVariableModel if found, None otherwise
        """
        if key == "descriptions":
            return None

        if key in ["domain", "ttl"]:
            return SingleVariableModel(
                name=key,
                value=self._variables[key],
                description=self._variables["descriptions"].get(key, ""),
            )
        elif "custom_vars" in self._variables and key in self._variables["custom_vars"]:
            var = self._variables["custom_vars"][key]
            return SingleVariableModel(
                name=key, value=var["value"], description=var.get("description", "")
            )
        return None

    def set_variable(
        self, variable: Union[SingleVariableModel, Dict[str, Any]]
    ) -> None:
        """Set a variable value.

        Args:
            variable: Variable to set, either as SingleVariableModel or dict
        """
        if isinstance(variable, SingleVariableModel):
            name = variable.name
            if name in ["domain", "ttl"]:
                self._variables[name] = variable.value
                if variable.description:
                    self._variables["descriptions"][name] = variable.description
            else:
                if "custom_vars" not in self._variables:
                    self._variables["custom_vars"] = {}
                self._variables["custom_vars"][name] = {
                    "value": variable.value,
                    "description": variable.description or "",
                }
        elif isinstance(variable, dict):
            name = variable.get("name")
            if not name:
                raise ValueError("Variable dictionary must contain 'name' key")
            if name in ["domain", "ttl"]:
                self._variables[name] = variable.get("value")
                if variable.get("description"):
                    self._variables["descriptions"][name] = variable["description"]
            else:
                if "custom_vars" not in self._variables:
                    self._variables["custom_vars"] = {}
                self._variables["custom_vars"][name] = {
                    "value": variable.get("value"),
                    "description": variable.get("description", ""),
                }
        else:
            raise ValueError(
                "Variable must be a SingleVariableModel or a dictionary with 'name' and 'value' keys"
            )

    def delete_variable(self, name: str) -> None:
        """Delete a variable.

        Args:
            name: Variable name to delete
        """
        if name in ["domain", "ttl"]:
            raise ValueError("Cannot delete built-in variables")
        elif (
            "custom_vars" in self._variables and name in self._variables["custom_vars"]
        ):
            del self._variables["custom_vars"][name]
        else:
            raise KeyError(f"Variable {name} not found")

    def remove_variable(self, name: str) -> None:
        """Alias for delete_variable to match CLI expectations.

        Args:
            name: Variable name to remove
        """
        return self.delete_variable(name)

    def get_all_variables(self) -> List[SingleVariableModel]:
        """Get all variables.

        Returns:
            List of all variables as SingleVariableModel
        """
        variables = []
        # Add base variables
        for name in ["domain", "ttl"]:
            variables.append(
                SingleVariableModel(
                    name=name,
                    value=self._variables[name],
                    description=self._variables["descriptions"].get(name, ""),
                )
            )
        # Add custom variables
        if "custom_vars" in self._variables:
            for name, var in self._variables["custom_vars"].items():
                variables.append(
                    SingleVariableModel(
                        name=name,
                        value=var["value"],
                        description=var.get("description", ""),
                    )
                )
        return variables

    def update(self, variables: Union[Dict[str, Any], VariableModel]) -> None:
        """Update variables from dictionary or VariableModel.

        Args:
            variables: Variables to update from
        """
        if isinstance(variables, dict):
            # Update base variables
            if "domain" in variables:
                self._variables["domain"] = variables["domain"]
            if "ttl" in variables:
                self._variables["ttl"] = variables["ttl"]
            # Update descriptions if present
            if "descriptions" in variables:
                desc_val = variables["descriptions"]
                if isinstance(desc_val, dict):
                    self._variables["descriptions"].update(desc_val)
            # Update custom variables
            if "custom_vars" in variables:
                self._variables["custom_vars"] = variables["custom_vars"]
            else:
                # Add other variables as custom vars
                if "custom_vars" not in self._variables:
                    self._variables["custom_vars"] = {}
                for name, value in variables.items():
                    if name not in ["domain", "ttl", "descriptions"]:
                        if isinstance(value, dict) and "value" in value:
                            self._variables["custom_vars"][name] = value
                        else:
                            self._variables["custom_vars"][name] = {
                                "value": value,
                                "description": "",
                            }
        elif isinstance(variables, VariableModel):
            # Update base variables
            self._variables["domain"] = variables.domain
            self._variables["ttl"] = variables.ttl
            # Update descriptions if present
            if variables.descriptions:
                self._variables["descriptions"].update(variables.descriptions)
            # Update custom variables
            if variables.custom_vars:
                self._variables["custom_vars"] = variables.custom_vars
            elif "custom_vars" in self._variables:
                del self._variables["custom_vars"]
        else:
            raise ValueError("Variables must be a dictionary or VariableModel")

    def clear_variables(self) -> None:
        """Clear all variables except defaults."""
        descriptions = self._variables.get("descriptions", {})
        self._variables = {
            "domain": "",
            "ttl": 3600,
            "descriptions": {
                "domain": descriptions.get("domain", "Domain name"),
                "ttl": descriptions.get("ttl", "Default TTL"),
            },
        }

    def resolve_variable_references(self, text: str) -> str:
        """Resolve variable references in text.

        Args:
            text: Text containing variable references

        Returns:
            Text with resolved variables
        """
        result = text
        # Resolve base variables
        for name in ["domain", "ttl"]:
            result = result.replace(f"${{{name}}}", str(self._variables[name]))
        # Resolve custom variables
        if "custom_vars" in self._variables:
            for name, var in self._variables["custom_vars"].items():
                result = result.replace(f"${{{name}}}", str(var["value"]))
        return result

    def resolve_nested_variables(self, text: str) -> str:
        """Resolve nested variable references in text.

        Args:
            text: Text containing nested variable references

        Returns:
            Text with resolved variables
        """
        result = text
        prev_result = None

        # Keep resolving until no more changes are made
        while result != prev_result:
            prev_result = result
            result = self.resolve_variable_references(result)

        return result

    def __getitem__(self, key: str) -> Any:
        """Get a variable value."""
        if key == "descriptions":
            return None
        if key in ["domain", "ttl"]:
            return self._variables[key]
        if "custom_vars" in self._variables and key in self._variables["custom_vars"]:
            return self._variables["custom_vars"][key]["value"]
        raise KeyError(f"Variable not found: {key}")

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a variable value."""
        if key == "descriptions":
            return
        if key in ["domain", "ttl"]:
            self._variables[key] = value
        else:
            if "custom_vars" not in self._variables:
                self._variables["custom_vars"] = {}
            self._variables["custom_vars"][key] = {"value": value, "description": ""}

    def __delitem__(self, key: str) -> None:
        """Remove a variable."""
        self.delete_variable(key)

    def __contains__(self, key: str) -> bool:
        """Check if a variable exists."""
        if key == "descriptions":
            return False
        return key in ["domain", "ttl"] or (
            "custom_vars" in self._variables and key in self._variables["custom_vars"]
        )

    def list_variables(self) -> List[Dict[str, Any]]:
        """List all variables.

        Returns:
            List of dictionaries containing variable information
        """
        variables = []
        # Add base variables
        for name in ["domain", "ttl"]:
            variables.append(
                {"name": name, "value": self._variables[name], "environment": "global"}
            )
        # Add custom variables
        if "custom_vars" in self._variables:
            for name, var in self._variables["custom_vars"].items():
                variables.append(
                    {"name": name, "value": var["value"], "environment": "global"}
                )
        return variables

    def bulk_update_variables(self, variables: Dict[str, Any]) -> None:
        """Update multiple variables at once.

        Args:
            variables: Dictionary of variables to update
        """
        for name, value in variables.items():
            if name in ["domain", "ttl"]:
                self._variables[name] = value
            else:
                if "custom_vars" not in self._variables:
                    self._variables["custom_vars"] = {}
                if isinstance(value, dict) and "value" in value:
                    self._variables["custom_vars"][name] = value
                else:
                    self._variables["custom_vars"][name] = {
                        "value": value,
                        "description": "",
                    }

    def get_variable_value(self, name: str) -> Any:
        """Get variable value.

        Args:
            name: Variable name

        Returns:
            Variable value

        Raises:
            KeyError: If variable does not exist
        """
        if name in ["domain", "ttl"]:
            return self._variables[name]
        elif (
            "custom_vars" in self._variables and name in self._variables["custom_vars"]
        ):
            return self._variables["custom_vars"][name]["value"]
        raise KeyError(f"Variable does not exist: {name}")

    def variable_exists(self, name: str) -> bool:
        """Check if variable exists.

        Args:
            name: Variable name

        Returns:
            True if exists, False otherwise
        """
        return name in ["domain", "ttl"] or (
            "custom_vars" in self._variables and name in self._variables["custom_vars"]
        )

    def get_variable_type(self, name: str) -> type:
        """Get variable type.

        Args:
            name: Variable name

        Returns:
            Variable type

        Raises:
            KeyError: If variable does not exist
        """
        if name in ["domain", "ttl"]:
            return type(self._variables[name])
        elif (
            "custom_vars" in self._variables and name in self._variables["custom_vars"]
        ):
            return type(self._variables["custom_vars"][name]["value"])
        raise KeyError(f"Variable does not exist: {name}")

    def validate_variable_name(self, name: str) -> bool:
        """Validate variable name.

        Args:
            name: Variable name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name or not isinstance(name, str):
            return False
        if name == "descriptions":
            return False
        return True
