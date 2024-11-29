"""Authentication module for DNS Services Gateway."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Union, Any

import requests
from pydantic import BaseModel

from .config import DNSServicesConfig
from .exceptions import AuthenticationError, TokenError

import getpass
import stat


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that can handle datetime objects."""

    def default(self, obj: Any) -> Any:
        """Convert datetime objects to ISO format strings.

        Args:
            obj: Object to encode

        Returns:
            ISO format string for datetime objects, or default encoding for other types
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class Token(BaseModel):
    """Token model for storing JWT information."""

    token: str
    created_at: datetime
    expires_at: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class TokenManager:
    """Manages JWT token operations including download and storage.

    This class handles all token-related operations including:
    - Downloading new tokens from the API
    - Securely storing tokens to disk
    - Loading and validating existing tokens
    - Checking token expiration
    """

    def __init__(self, config: DNSServicesConfig):
        """Initialize the token manager.

        Args:
            config: DNS Services configuration object containing authentication
                   settings and token storage preferences.
        """
        self.config = config
        self._session = requests.Session()
        self._session.verify = self.config.verify_ssl

    @staticmethod
    def _secure_write_token(token_data: Dict, token_path: Union[str, Path]) -> None:
        """Securely write token to file with proper permissions."""
        token_path = Path(token_path).expanduser()
        token_path.parent.mkdir(parents=True, exist_ok=True)

        # Write token with restricted permissions
        token_path.write_text(json.dumps(token_data, cls=DateTimeEncoder))
        os.chmod(token_path, 0o600)  # 0600 permissions

    def download_token(
        self,
        username: str,
        output_path: Optional[Union[str, Path]] = None,
        password: Optional[str] = None,
    ) -> Optional[str]:
        """
        Download and save authentication token.

        Args:
            username: DNS.services account username
            output_path: Optional path to save token to
            password: Optional password override

        Returns:
            Optional[str]: Path where token was saved, or None if no path was provided

        Raises:
            AuthenticationError: If authentication fails
            TokenError: If token cannot be saved
        """
        if not password:
            password = getpass.getpass("Enter your DNS.services password: ")

        try:
            response = self._session.post(
                f"{self.config.base_url}/api/login",
                data={"username": username, "password": password},
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            token_data = response.json()
            if "token" not in token_data:
                raise AuthenticationError("No token in response")

            # Create token model
            token = Token(
                token=token_data["token"], created_at=datetime.now(timezone.utc)
            )

            # Save token to file if path is provided
            token_json = token.model_dump()
            if output_path:
                path = Path(output_path)
                self._secure_write_token(token_json, str(path))
                # Set file permissions
                path.chmod(0o600)
                return str(path.expanduser())
            elif self.config.token_path:
                path = Path(self.config.token_path)
                self._secure_write_token(token_json, str(path))
                # Set file permissions
                path.chmod(0o600)
                return str(path.expanduser())
            return None

        except requests.RequestException as e:
            raise AuthenticationError(f"Failed to obtain token: {str(e)}") from e

    @staticmethod
    def load_token(token_path: Union[str, Path]) -> Token:
        """
        Load and validate token from file.

        Args:
            token_path: Path to token file

        Returns:
            Token: Loaded token object

        Raises:
            TokenError: If token file is invalid or has incorrect permissions
        """
        try:
            token_path = Path(token_path).expanduser()
            if not token_path.exists():
                raise TokenError(f"Token file not found: {token_path}")

            # Check file permissions
            stat_info = os.stat(token_path)
            if stat_info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise TokenError(
                    f"Token file {token_path} has incorrect permissions. "
                    f"Should be accessible only by owner."
                )

            token_data = json.loads(token_path.read_text())
            token_data["created_at"] = datetime.fromisoformat(token_data["created_at"])
            if token_data.get("expires_at"):
                token_data["expires_at"] = datetime.fromisoformat(
                    token_data["expires_at"]
                )
            return Token(**token_data)

        except (json.JSONDecodeError, TypeError) as e:
            raise TokenError(f"Invalid token file format: {str(e)}") from e
