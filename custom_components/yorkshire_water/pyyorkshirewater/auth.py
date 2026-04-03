"""Authentication handler for Yorkshire Water."""

import logging
import urllib.parse
from datetime import datetime, timedelta

import aiohttp

from .const import (
    AUTHORIZE_URL,
    CLIENT_ID,
    LOGIN_PAGE,
    LOGIN_URL,
    REDIRECT_URI,
    SCOPES,
    TOKEN_URL,
)
from .exceptions import ApiError, LoginError, RateLimitError, TokenError, UnauthorizedError
from .utils import decode_jwt, extract_csrf_token, generate_pkce_pair

_LOGGER = logging.getLogger(__name__)


class YorkshireWaterAuth:
    """Handle authentication with Yorkshire Water."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ):
        self._session = session
        self._owns_session = session is None
        self.username = username
        self._password = password
        self.auth_data: dict | None = None
        self.next_refresh: datetime | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar()
            )
            self._owns_session = True
        return self._session

    @property
    def access_token(self) -> str | None:
        """Return the current access token."""
        if self.auth_data is None:
            return None
        return self.auth_data.get("access_token")

    @property
    def is_authenticated(self) -> bool:
        """Return True if we have a valid token."""
        return (
            self.access_token is not None
            and self.next_refresh is not None
            and self.next_refresh > datetime.now()
        )

    @property
    def token_expires_at(self) -> datetime | None:
        """Return when the current token expires."""
        return self.next_refresh

    @property
    def authenticated_headers(self) -> dict:
        """Return headers for authenticated API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    async def login(self) -> None:
        """Perform full login flow: form POST -> OAuth authorize -> token exchange."""
        session = await self._ensure_session()

        # Step 1: GET login page, extract CSRF token
        _LOGGER.debug("Getting login page")
        async with session.get(LOGIN_PAGE) as resp:
            if resp.status != 200:
                raise LoginError(f"Failed to load login page: {resp.status}")
            html = await resp.text()
        csrf_token = extract_csrf_token(html)

        # Step 2: POST login form (no reCAPTCHA needed)
        _LOGGER.debug("Submitting login form")
        async with session.post(
            LOGIN_PAGE,
            data={
                "Email": self.username,
                "Password": self._password,
                "__RequestVerificationToken": csrf_token,
                "g-recaptcha-response": "",
                "RedirectUrl": "https://my.yorkshirewater.com/account",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": LOGIN_URL,
                "Referer": LOGIN_PAGE,
            },
            allow_redirects=False,
        ) as resp:
            if resp.status != 302:
                raise LoginError(
                    f"Login failed (expected 302, got {resp.status}). Check credentials."
                )
            _LOGGER.debug("Login successful, got redirect")

        # Step 3: OAuth authorize with PKCE
        code_verifier, code_challenge = generate_pkce_pair()

        authorize_params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPES,
            "state": "pyyorkshirewater",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "response_mode": "query",
        }

        _LOGGER.debug("Requesting authorization code")
        async with session.get(
            AUTHORIZE_URL,
            params=authorize_params,
            allow_redirects=False,
        ) as resp:
            if resp.status != 302:
                raise TokenError(
                    f"Authorization failed (expected 302, got {resp.status})"
                )
            location = resp.headers.get("Location", "")

        # Extract auth code from redirect URL
        parsed = urllib.parse.urlparse(location)
        query = urllib.parse.parse_qs(parsed.query)
        code = query.get("code", [None])[0]
        if not code:
            raise TokenError(f"No authorization code in redirect: {location}")
        _LOGGER.debug("Got authorization code")

        # Step 4: Exchange code for tokens
        _LOGGER.debug("Exchanging code for access token")
        async with session.post(
            TOKEN_URL,
            data=urllib.parse.urlencode({
                "client_id": CLIENT_ID,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
            }),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://my.yorkshirewater.com",
            },
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise TokenError(f"Token exchange failed ({resp.status}): {text}")
            token_data = await resp.json()

        self.auth_data = token_data
        self.next_refresh = datetime.now() + timedelta(
            seconds=token_data["expires_in"]
        )
        self.auth_data = {**self.auth_data, **decode_jwt(self.access_token)}
        _LOGGER.debug(
            "Authenticated successfully, token expires at %s", self.next_refresh
        )

    async def send_request(
        self, method: str, url: str, **kwargs
    ) -> dict:
        """Send an authenticated API request. Re-logs in if token expired."""
        if not self.is_authenticated:
            _LOGGER.debug("Token expired or missing, re-authenticating")
            await self.login()
        if self.access_token is None:
            raise UnauthorizedError("Not authenticated")

        session = await self._ensure_session()
        headers = {**self.authenticated_headers, **kwargs.pop("headers", {})}

        async with session.request(
            method=method, url=url, headers=headers, **kwargs
        ) as resp:
            _LOGGER.debug("Request to %s returned %s", url, resp.status)
            if resp.ok and resp.content_type == "application/json":
                return await resp.json()
            if resp.status == 401:
                raise UnauthorizedError("Access token expired")
            if resp.status == 429:
                raise RateLimitError("Rate limited")
            raise ApiError(f"API error {resp.status}: {await resp.text()}")

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
