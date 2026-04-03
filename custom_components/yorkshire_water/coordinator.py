"""Yorkshire Water data coordinator."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from .pyyorkshirewater import YorkshireWater
from .pyyorkshirewater.exceptions import ApiError, AuthError

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.util.unit_conversion import VolumeConverter
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_ACCOUNT_NUMBER, DOMAIN

type YorkshireWaterConfigEntry = ConfigEntry[YorkshireWaterUpdateCoordinator]

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(minutes=60)


class YorkshireWaterUpdateCoordinator(DataUpdateCoordinator[None]):
    """Yorkshire Water data update coordinator."""

    config_entry: YorkshireWaterConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: YorkshireWater,
        config_entry: YorkshireWaterConfigEntry,
    ) -> None:
        """Initialize update coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=config_entry,
        )
        self.api = api

    async def _async_update_data(self) -> None:
        """Update data from Yorkshire Water's API."""
        try:
            await self.api.update(
                self.config_entry.data[CONF_ACCOUNT_NUMBER],
                days=7,
            )
            await self._insert_statistics()
        except (AuthError, ApiError) as err:
            raise UpdateFailed from err

    async def _insert_statistics(self) -> None:
        """Insert daily consumption statistics into Home Assistant."""
        for meter in self.api.meters.values():
            id_prefix = (
                f"{self.config_entry.data[CONF_ACCOUNT_NUMBER]}_{meter.serial_number}"
            )
            usage_statistic_id = f"{DOMAIN}:{id_prefix}_usage".lower()

            _LOGGER.debug("Updating statistics for meter %s", meter.serial_number)

            name_prefix = (
                f"Yorkshire Water {self.config_entry.data[CONF_ACCOUNT_NUMBER]} "
                f"{meter.serial_number}"
            )
            usage_metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name=f"{name_prefix} Usage",
                source=DOMAIN,
                statistic_id=usage_statistic_id,
                unit_class=VolumeConverter.UNIT_CLASS,
                unit_of_measurement=UnitOfVolume.LITERS,
            )

            # Get last recorded statistic to avoid duplicates
            last_stat = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, usage_statistic_id, True, {"sum"}
            )

            if not last_stat or not last_stat.get(usage_statistic_id):
                usage_sum = 0.0
                last_stats_time = None
            else:
                stats = last_stat[usage_statistic_id]
                usage_sum = float(stats[0].get("sum", 0))
                last_stats_time = stats[0].get("start")

            usage_statistics = []
            for reading in meter.readings:
                reading_date = reading.get("date")
                if not reading_date:
                    continue

                # Parse the date string (YYYY-MM-DD) and set to start of day
                try:
                    start = dt_util.as_local(
                        datetime.fromisoformat(reading_date)
                    ).replace(hour=0, minute=0, second=0, microsecond=0)
                except ValueError:
                    _LOGGER.debug("Could not parse date %s, skipping", reading_date)
                    continue

                # Skip if we already have this date
                if last_stats_time is not None and start.timestamp() <= last_stats_time:
                    continue

                litres = float(reading.get("totalConsumptionLitres", 0))
                usage_sum += litres

                usage_statistics.append(
                    StatisticData(
                        start=start,
                        state=litres,
                        sum=usage_sum,
                    )
                )

            if usage_statistics:
                _LOGGER.debug(
                    "Adding %s statistics for %s",
                    len(usage_statistics),
                    usage_statistic_id,
                )
                async_add_external_statistics(
                    self.hass, usage_metadata, usage_statistics
                )
