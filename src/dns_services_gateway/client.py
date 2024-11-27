"""DNS Services Gateway client implementation."""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import requests
from requests.exceptions import RequestException

from .config import DNSServicesConfig
from .models import AuthResponse, OperationResponse
from .exceptions import AuthenticationError, APIError


class DNSServicesClient:
    """DNS Services Gateway client."""

    def __init__(self, config: DNSServicesConfig) -> None:
        """Initialize the client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.session = requests.Session()
        self.session.verify = config.verify_ssl
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

        if config.debug:
            logging.basicConfig(level=logging.DEBUG)
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())

    def _load_token(self) -> Optional[AuthResponse]:
        """Load authentication token from file.

        Returns:
            Optional[AuthResponse]: Loaded token data or None if not available
        """
        token_path = self.config.get_token_path()
        if not token_path or not token_path.exists():
            return None

        try:
            data = json.loads(token_path.read_text())
            return AuthResponse(
                token=data["token"],
                expires=datetime.fromisoformat(data["expires"]),
                refresh_token=data.get("refresh_token"),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Failed to load token: {e}")
            return None

    def _save_token(self, auth: AuthResponse) -> None:
        """Save authentication token to file.

        Args:
            auth: Authentication response to save
        """
        token_path = self.config.get_token_path()
        if not token_path:
            return

        token_path.write_text(
            json.dumps(
                {
                    "token": auth.token,
                    "expires": auth.expires.isoformat(),
                    "refresh_token": auth.refresh_token,
                }
            )
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.

        Returns:
            Dict[str, str]: Request headers

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self._token or (
            self._token_expires
            and self._token_expires <= datetime.now(timezone.utc)
        ):
            self.authenticate()

        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def authenticate(self) -> None:
        """Authenticate with the API.

        Raises:
            AuthenticationError: If authentication fails
        """
        # First try to load existing token
        auth = self._load_token()
        if auth and auth.expires > datetime.now(timezone.utc):
            self._token = auth.token
            self._token_expires = auth.expires
            return

        try:
            response = self.session.post(
                f"{self.config.base_url}/auth",
                json={
                    "username": self.config.username,
                    "password": self.config.password.get_secret_value(),
                },
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            auth = AuthResponse(**response.json())
            self._token = auth.token
            self._token_expires = auth.expires
            self._save_token(auth)

        except RequestException as e:
            raise AuthenticationError(
                "Authentication failed",
                details={"error": str(e)},
            )

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the API.

        Args:
            method: HTTP method
            path: API path
            **kwargs: Additional request arguments

        Returns:
            Dict[str, Any]: API response data

        Raises:
            APIError: If the request fails
        """
        kwargs.setdefault("timeout", self.config.timeout)
        headers = self._get_headers()
        kwargs.setdefault("headers", {}).update(headers)

        try:
            response = self.session.request(
                method,
                f"{self.config.base_url}{path}",
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

        except RequestException as e:
            raise APIError(
                f"API request failed: {str(e)}",
                status_code=getattr(e.response, "status_code", None),
                response_body=getattr(e.response, "json", lambda: None)(),
            )

    def get(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a GET request to the API."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a POST request to the API."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a PUT request to the API."""
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a DELETE request to the API."""
        return self._request("DELETE", path, **kwargs)
