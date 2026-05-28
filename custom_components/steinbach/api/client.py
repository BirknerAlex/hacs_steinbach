"""HTTP client for the Tuya IoT Cloud OpenAPI.

Steinbach pool heat pumps are Tuya hardware. This client talks to the officially
supported Tuya OpenAPI using a project's Access ID + Access Secret. Requests are
signed with HMAC-SHA256 as documented by Tuya; the access token is fetched on
first use and refreshed shortly before it expires.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time

import requests

from ..const import DEFAULT_REGION, TUYA_ENDPOINTS
from .error import AuthenticationError, RequestError

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
# Refresh the access token this many seconds before it actually expires.
TOKEN_REFRESH_MARGIN = 60

# Tuya error codes that mean the token is no longer usable; a fresh token should
# be fetched and the request retried.
TOKEN_ERROR_CODES = frozenset({1010, 1011, 1012, 1013, 1014})
# Error codes that indicate an authentication/permission problem (bad Access
# ID/Secret, wrong region, missing API subscription) rather than a transient
# failure. These are surfaced as AuthenticationError.
AUTH_ERROR_CODES = frozenset({1004, 1106, 1109, 2406}) | TOKEN_ERROR_CODES


class TuyaOpenAPIClient:
    """Signed client for the Tuya IoT Cloud OpenAPI."""

    def __init__(
        self, access_id: str, access_secret: str, region: str = DEFAULT_REGION
    ) -> None:
        self.access_id = access_id
        self.access_secret = access_secret
        self.base_url = TUYA_ENDPOINTS.get(region, TUYA_ENDPOINTS[DEFAULT_REGION])
        self._session = requests.Session()
        self._token: str | None = None
        self._refresh_token: str | None = None
        self._expire_at: float = 0.0

    def _sign(self, method: str, path: str, token: str, body: str) -> dict[str, str]:
        """Build the signed request headers for a single call."""
        t = str(int(time.time() * 1000))
        content_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
        string_to_sign = f"{method}\n{content_sha256}\n\n{path}"
        message = self.access_id + token + t + string_to_sign
        sign = (
            hmac.new(
                self.access_secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )
        headers = {
            "client_id": self.access_id,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "nonce": "",
        }
        if token:
            headers["access_token"] = token
        return headers

    def _call(
        self, method: str, path: str, token: str, body: dict | None = None
    ) -> object:
        """Perform a single signed request and return its ``result`` payload."""
        body_str = json.dumps(body, separators=(",", ":")) if body is not None else ""
        headers = self._sign(method, path, token, body_str)
        if body is not None:
            headers["Content-Type"] = "application/json"

        try:
            res = self._session.request(
                method,
                self.base_url + path,
                headers=headers,
                data=body_str.encode("utf-8") if body_str else None,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as err:
            raise RequestError(f"{method} {path} failed: {err}") from err

        try:
            payload = res.json()
        except ValueError as err:
            raise RequestError(
                f"{method} {path} returned non-JSON ({res.status_code})"
            ) from err

        if payload.get("success"):
            return payload.get("result")

        code = payload.get("code")
        msg = payload.get("msg", "unknown error")
        if code in AUTH_ERROR_CODES:
            raise AuthenticationError(f"Tuya API auth error {code}: {msg}")
        raise RequestError(f"Tuya API error {code}: {msg}")

    def _store_token(self, result: dict) -> None:
        self._token = result["access_token"]
        self._refresh_token = result.get("refresh_token", self._refresh_token)
        self._expire_at = time.time() + int(result.get("expire_time", 7200))

    def _fetch_token(self) -> None:
        result = self._call("GET", "/v1.0/token?grant_type=1", token="")
        self._store_token(result)

    def _refresh(self) -> None:
        result = self._call("GET", f"/v1.0/token/{self._refresh_token}", token="")
        self._store_token(result)

    def _valid_token(self) -> str:
        """Return a non-expired access token, fetching or refreshing as needed."""
        if self._token is None:
            self._fetch_token()
        elif time.time() >= self._expire_at - TOKEN_REFRESH_MARGIN:
            try:
                self._refresh()
            except AuthenticationError:
                self._token = None
                self._fetch_token()
        assert self._token is not None
        return self._token

    def _authed_call(
        self, method: str, path: str, body: dict | None = None
    ) -> object:
        """Call a token-authenticated endpoint, retrying once on a token error."""
        try:
            return self._call(method, path, token=self._valid_token(), body=body)
        except AuthenticationError as err:
            if self._token is None:
                raise
            _LOGGER.debug("Token rejected (%s); refetching and retrying once", err)
            self._token = None
            return self._call(method, path, token=self._valid_token(), body=body)

    def authenticate(self) -> None:
        """Force-fetch an access token to validate the configured credentials."""
        self._fetch_token()

    def get_devices(self) -> list[dict]:
        """Return the devices linked to this Tuya project."""
        result = self._authed_call(
            "GET", "/v1.0/iot-01/associated-users/devices"
        )
        return result.get("devices", []) if isinstance(result, dict) else []

    def get_properties(self, device_id: str) -> list[dict]:
        """Return the current device-point properties for a device."""
        result = self._authed_call(
            "GET", f"/v2.0/cloud/thing/{device_id}/shadow/properties"
        )
        return result.get("properties", []) if isinstance(result, dict) else []

    def get_model(self, device_id: str) -> dict:
        """Return the parsed device model (services -> properties with typeSpec)."""
        result = self._authed_call("GET", f"/v2.0/cloud/thing/{device_id}/model")
        return json.loads(result["model"])

    def send_commands(self, device_id: str, commands: list[dict]) -> object:
        """Issue one or more device-point commands."""
        return self._authed_call(
            "POST",
            f"/v1.0/devices/{device_id}/commands",
            body={"commands": commands},
        )

    def close(self) -> None:
        """Drop cached state and close the HTTP session."""
        self._token = None
        self._refresh_token = None
        self._session.close()
