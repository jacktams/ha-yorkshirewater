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


def _parse_date(value: object) -> date | None:
    """Parse an ISO date string, returning None if absent/unparseable."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def parse_meter_move_dates(meter_data: dict) -> tuple[date, date]:
    """Derive move-in/out dates to bracket a daily-consumption query.

    Yorkshire Water's meter-details response no longer includes the meter's
    real move-in/out dates; it now returns only accountReference,
    meterReference and currentDate. The daily-consumption endpoint still
    requires moveInDate/moveOutDate params, but only uses them to bracket the
    request, whose real window is bounded by the start/end dates. So we anchor
    move-out to the API's own currentDate (falling back to today) and bracket
    move-in generously.

    Older/renamed responses may still carry explicit start/end dates, and the
    0001-01-01 sentinel means an active meter; both are honoured when present.
    """
    today = date.today()

    move_out = None
    for key in ("endDate", "moveOutDate", "meterEndDate", "currentDate"):
        move_out = _parse_date(meter_data.get(key))
        if move_out is not None:
            break
    # Sentinel 0001-01-01 (or any pre-1900 value) means an active meter.
    if move_out is None or move_out.year < 1900:
        move_out = today

    move_in = None
    for key in ("startDate", "moveInDate", "meterStartDate", "installDate"):
        move_in = _parse_date(meter_data.get(key))
        if move_in is not None:
            break
    if move_in is None:
        # Bracket generously; the real range is bounded by daily-consumption.
        move_in = move_out.replace(year=move_out.year - 10)

    return move_in, move_out


def extract_csrf_token(html: str) -> str:
    """Extract __RequestVerificationToken from login page HTML."""
    match = re.search(
        r'name="__RequestVerificationToken"\s+type="hidden"\s+value="([^"]+)"',
        html,
    )
    if not match:
        raise ValueError("Could not find CSRF token in login page")
    return match.group(1)
