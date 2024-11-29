"""DNS Services Gateway client implementation."""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import requests
from requests.exceptions import RequestException

from .config import DNSServicesConfig
from .exceptions import AuthenticationError, APIError
from .models import AuthResponse


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
            # Handle both 'expiration' and 'expires' fields for backward compatibility
            expires_str = data.get("expires") or data.get("expiration")
            if not expires_str:
                raise KeyError("No expiration field found")
            return AuthResponse(
                token=data["token"],
                expires=datetime.fromisoformat(expires_str),
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

        if not auth.expires:
            auth.expires = datetime.now(timezone.utc).replace(
                microsecond=0
            ) + timedelta(hours=1)

        token_path.write_text(
            json.dumps(
                {
                    "token": auth.token,
                    "expiration": auth.expiration or auth.expires.isoformat(),
                    "refresh_token": auth.refresh_token,
                }
            )
        )

    def authenticate(self, force: bool = False) -> None:
        """Authenticate with the API.

        Args:
            force: If True, force authentication even if a valid token exists

        Raises:
            AuthenticationError: If authentication fails
        """
        # Try to load existing token first
        auth = self._load_token()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        if not force and auth and auth.expires and auth.expires > now:
            self._token = auth.token
            self._token_expires = auth.expires
            return

        # Clear existing token before attempting authentication
        self._token = None
        self._token_expires = None

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
            data = response.json()

            # Handle both expiration and expires fields
            if "expiration" in data and "expires" not in data:
                data["expires"] = data["expiration"]

            # Create and validate the auth response
            auth = AuthResponse(**data)
            self._token = auth.token
            self._token_expires = auth.expires
            self._save_token(auth)

        except (requests.exceptions.RequestException, ValueError) as e:
            self._token = None
            self._token_expires = None
            raise AuthenticationError(
                "Authentication failed",
                details={"error": str(e)},
            ) from e

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.

        Returns:
            Dict[str, str]: Request headers

        Raises:
            AuthenticationError: If authentication fails
        """
        now = datetime.now(timezone.utc).replace(microsecond=0)
        # Check if token is expired
        if not self._token or not self._token_expires or self._token_expires < now:
            self.authenticate()

        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make an API request.

        Args:
            method: HTTP method
            path: API path
            **kwargs: Additional request arguments

        Returns:
            Dict[str, Any]: API response

        Raises:
            APIError: If the API request fails
        """
        headers = kwargs.pop("headers", {})
        headers.update(self._get_headers())

        try:
            response = self.session.request(
                method,
                f"{self.config.base_url}{path}",
                headers=headers,
                timeout=self.config.timeout,
                **kwargs,
            )
            response.raise_for_status()  # This will raise if status code is not 2xx
            try:
                return response.json()
            except ValueError as e:
                raise APIError(
                    f"Failed to parse JSON response: {str(e)}",
                    status_code=response.status_code,
                    response_body={"error": str(e)},
                )

        except RequestException as e:
            if e.response:
                if e.response.status_code >= 500:
                    raise APIError(
                        "Server error",
                        status_code=e.response.status_code,
                        response_body={"error": e.response.text},
                    )
                elif e.response.status_code >= 400:
                    # Correctly parse the response body as JSON
                    response_body = json.loads(e.response.text)
                    raise APIError(
                        "Client error",
                        status_code=e.response.status_code,
                        response_body=response_body,
                    )
                else:
                    raise APIError(
                        "Request failed",
                        status_code=e.response.status_code,
                        response_body={"error": e.response.text},
                    )
            else:
                raise APIError(
                    "API request failed",
                    status_code=None,
                    response_body={"error": str(e)},
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
