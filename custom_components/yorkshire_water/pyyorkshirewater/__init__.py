"""pyyorkshirewater - A package to interact with Yorkshire Water smart meters."""

import asyncio
import logging
from datetime import date, timedelta
from typing import Callable

from .api import API
from .auth import YorkshireWaterAuth
from .meter import SmartMeter

_LOGGER = logging.getLogger(__name__)


class YorkshireWater:
    """Main interface for Yorkshire Water smart meter data."""

    def __init__(self, authenticator: YorkshireWaterAuth):
        self.api = API(authenticator)
        self.meters: dict[str, SmartMeter] = {}
        self._callbacks: list[Callable] = []

    async def update(
        self,
        account_reference: str,
        days: int = 7,
    ) -> dict:
        """Fetch meter details and recent daily consumption, update meter cache."""
        # Get meter details
        meter_data = await self.api.get_meter_details(account_reference)
        meter_reference = meter_data["meterReference"]

        # Fetch daily consumption
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        consumption = await self.api.get_daily_consumption(
            meter_reference, start_date, end_date
        )

        # Update meter cache
        if meter_reference not in self.meters:
            self.meters[meter_reference] = SmartMeter(meter_reference)
        self.meters[meter_reference].update_reading_cache(
            consumption.get("dailyUsageData", [])
        )

        # Trigger callbacks
        for callback in self._callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback(self.meters[meter_reference])
            else:
                callback(self.meters[meter_reference])

        _LOGGER.debug(
            "Updated meter %s with %d readings",
            meter_reference,
            len(consumption.get("dailyUsageData", [])),
        )
        return consumption

    def register_callback(self, callback: Callable) -> None:
        """Register a callback for data updates."""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove a registered callback."""
        self._callbacks.remove(callback)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "api": self.api.to_dict(),
            "meters": {k: v.to_dict() for k, v in self.meters.items()},
        }
