"""Utility functions for pyyorkshirewater."""

import base64
import hashlib
import json
import os
import re


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge pair."""
    code_verifier = os.urandom(48).hex()
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def decode_jwt(token: str) -> dict:
    """Decode a JWT token without verification."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token")
    payload = parts[1]
    # Add padding
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    decoded = base64.urlsafe_b64decode(payload)
    return json.loads(decoded)


def extract_csrf_token(html: str) -> str:
    """Extract __RequestVerificationToken from login page HTML."""
    match = re.search(
        r'name="__RequestVerificationToken"\s+type="hidden"\s+value="([^"]+)"',
        html,
    )
    if not match:
        raise ValueError("Could not find CSRF token in login page")
    return match.group(1)
