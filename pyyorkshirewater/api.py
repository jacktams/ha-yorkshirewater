"""API client for Yorkshire Water."""

import logging
from datetime import date

from .auth import YorkshireWaterAuth
from .const import ENDPOINTS
from .enum import TimePeriod

_LOGGER = logging.getLogger(__name__)


class API:
    """Yorkshire Water API client."""

    def __init__(self, auth: YorkshireWaterAuth):
        self._auth = auth

    @property
    def username(self) -> str:
        return self._auth.username

    async def get_meter_details(self, account_reference: str) -> dict:
        """Get smart meter details for an account."""
        return await self._auth.send_request(
            "GET",
            ENDPOINTS["meter_details"],
            params={"accountReference": account_reference},
        )

    async def get_daily_consumption(
        self,
        meter_reference: str,
        start_date: date,
        end_date: date,
        time_period: TimePeriod = TimePeriod.DAILY,
    ) -> dict:
        """Get daily consumption data for a meter."""
        return await self._auth.send_request(
            "GET",
            ENDPOINTS["daily_consumption"],
            params={
                "meterReference": meter_reference,
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "timePeriod": time_period.value,
            },
        )

    async def get_current_consumption(self, meter_reference: str) -> dict:
        """Get current consumption state for a meter."""
        return await self._auth.send_request(
            "GET",
            ENDPOINTS["current_consumption"],
            params={"meterReference": meter_reference},
        )

    async def get_your_usage(self, meter_reference: str) -> dict:
        """Get monthly usage summary for a meter."""
        return await self._auth.send_request(
            "GET",
            ENDPOINTS["your_usage"],
            params={"meterReference": meter_reference},
        )

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "username": self.username,
            "next_refresh": str(self._auth.token_expires_at),
        }
