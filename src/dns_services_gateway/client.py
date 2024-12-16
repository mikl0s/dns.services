"""DNS Services Gateway client implementation."""

import json
import logging
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import requests
from requests.exceptions import RequestException

from .config import DNSServicesConfig, AuthType
from .exceptions import AuthenticationError, APIError, RequestError
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

    def _get_basic_auth_header(self) -> str:
        """Get Basic Authentication header value.

        Returns:
            str: Base64 encoded credentials
        """
        credentials = (
            f"{self.config.username}:{self.config.password.get_secret_value()}"
        )
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.

        Returns:
            Dict[str, str]: Request headers

        Raises:
            AuthenticationError: If authentication fails
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.config.auth_type == AuthType.BASIC:
            headers["Authorization"] = self._get_basic_auth_header()
        else:  # JWT auth
            now = datetime.now(timezone.utc).replace(microsecond=0)
            # Check if token is expired
            if not self._token or not self._token_expires or self._token_expires < now:
                self.authenticate()
            if not self._token:
                raise AuthenticationError("Failed to obtain JWT token")
            headers["Authorization"] = f"Bearer {self._token}"

        return headers

    def authenticate(self, force: bool = False) -> None:
        """Authenticate with the API.

        Args:
            force: If True, force authentication even if a valid token exists

        Raises:
            AuthenticationError: If authentication fails
        """
        if self.config.auth_type == AuthType.BASIC:
            # Basic auth doesn't require token authentication
            return

        # JWT authentication
        if not force:
            auth = self._load_token()
            now = datetime.now(timezone.utc).replace(microsecond=0)
            if auth and auth.expires and auth.expires > now:
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

            if response.status_code != 200:
                raise AuthenticationError(f"Authentication failed: {response.text}")

            auth_data = response.json()
            expiration = auth_data.get("expiration") or auth_data.get("expires")
            if not expiration:
                raise AuthenticationError("No expiration time in response")

            # Parse expiration time from string to datetime
            if isinstance(expiration, str):
                expiration = datetime.fromisoformat(expiration)

            auth = AuthResponse(
                token=auth_data["token"],
                expiration=expiration,
                refresh_token=auth_data.get("refresh_token"),
            )
            self._token = auth.token
            self._token_expires = auth.expires
            self._save_token(auth)
        except (RequestException, KeyError, ValueError) as e:
            raise AuthenticationError(f"Authentication request failed: {e}")

    def _request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> requests.Response:
        """Make a request to the API.

        Args:
            method: HTTP method
            path: API path
            headers: Optional headers to include
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response from the API

        Raises:
            RequestError: If the request fails
        """
        url = f"{self.config.base_url}{path}"
        headers = headers or {}
        headers.update(self._get_headers())

        try:
            response = getattr(self.session, method.lower())(
                url,
                headers=headers,
                timeout=self.config.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as e:
            raise RequestError(f"Request timed out: {e}")
        except requests.exceptions.ConnectionError as e:
            raise RequestError(f"Connection failed: {e}")
        except requests.exceptions.HTTPError as e:
            raise RequestError(str(e))
        except RequestException as e:
            raise RequestError(f"Request failed: {e}")

    def _parse_json_response(self, response: requests.Response) -> Dict[str, Any]:
        """Parse JSON response from the API.

        Args:
            response: Response from the API

        Returns:
            Dict[str, Any]: Parsed JSON response

        Raises:
            APIError: If JSON parsing fails
        """
        try:
            return response.json()
        except ValueError as e:
            raise APIError(
                "Failed to parse JSON response",
                status_code=response.status_code,
                response_body={"error": "Invalid JSON"},
            )

    def get(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a GET request to the API."""
        response = self._request("GET", path, **kwargs)
        return self._parse_json_response(response)

    def post(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a POST request to the API."""
        response = self._request("POST", path, **kwargs)
        return self._parse_json_response(response)

    def put(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a PUT request to the API."""
        response = self._request("PUT", path, **kwargs)
        return self._parse_json_response(response)

    def delete(self, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a DELETE request to the API."""
        response = self._request("DELETE", path, **kwargs)
        return self._parse_json_response(response)
