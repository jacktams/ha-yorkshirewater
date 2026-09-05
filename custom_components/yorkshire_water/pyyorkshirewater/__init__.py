"""pyyorkshirewater - A package to interact with Yorkshire Water smart meters."""

import asyncio
import logging
from datetime import date, timedelta
from typing import Awaitable, Callable

from .api import API
from .auth import YorkshireWaterAuth
from .meter import SmartMeter
from .utils import parse_meter_move_dates

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
        resolve_start_date: Callable[[str], Awaitable[date]] | None = None,
    ) -> dict:
        """Fetch meter details and recent daily consumption, update meter cache.

        The fetch window ends today. Its start is either ``days`` before today
        (the default) or, when ``resolve_start_date`` is supplied, whatever date
        that callback returns for the resolved meter reference. The coordinator
        uses the callback to start from the last statistic already stored in
        Home Assistant so gaps since the last successful poll are backfilled.
        """
        # Get meter details
        meter_data = await self.api.get_meter_details(account_reference)
        meter_reference = meter_data["meterReference"]
        move_in_date, move_out_date = parse_meter_move_dates(meter_data)

        # Fetch daily consumption
        end_date = date.today()
        if resolve_start_date is not None:
            start_date = await resolve_start_date(meter_reference)
            if start_date > end_date:
                start_date = end_date
        else:
            start_date = end_date - timedelta(days=days)
        consumption = await self.api.get_daily_consumption(
            meter_reference, start_date, end_date, move_in_date, move_out_date
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
