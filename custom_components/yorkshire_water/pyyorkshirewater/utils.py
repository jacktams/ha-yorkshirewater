"""Utility functions for pyyorkshirewater."""

import base64
import hashlib
import json
import os
import re
from datetime import date, datetime


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


def parse_meter_move_dates(meter_data: dict) -> tuple[date, date]:
    """Extract move-in/out dates from meter_details.

    The API returns endDate as 0001-01-01 for meters that haven't been moved
    out of; in that case the web app sends today as moveOutDate.
    """
    move_in = datetime.fromisoformat(meter_data["startDate"]).date()
    move_out_raw = datetime.fromisoformat(meter_data["endDate"]).date()
    if move_out_raw.year < 1900:
        move_out_raw = date.today()
    return move_in, move_out_raw


def extract_csrf_token(html: str) -> str:
    """Extract __RequestVerificationToken from login page HTML."""
    match = re.search(
        r'name="__RequestVerificationToken"\s+type="hidden"\s+value="([^"]+)"',
        html,
    )
    if not match:
        raise ValueError("Could not find CSRF token in login page")
    return match.group(1)
