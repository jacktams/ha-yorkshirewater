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
        """Insert daily consumption and cost statistics into Home Assistant."""
        _LOGGER.debug(
            "insert_statistics called, meters: %s",
            list(self.api.meters.keys()),
        )
        for meter in self.api.meters.values():
            _LOGGER.debug(
                "Meter %s has %d readings", meter.serial_number, len(meter.readings)
            )
            id_prefix = (
                f"{self.config_entry.data[CONF_ACCOUNT_NUMBER]}_{meter.serial_number}"
            )
            usage_statistic_id = f"{DOMAIN}:{id_prefix}_usage".lower()
            cost_statistic_id = f"{DOMAIN}:{id_prefix}_cost".lower()

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
            cost_metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name=f"{name_prefix} Cost",
                source=DOMAIN,
                statistic_id=cost_statistic_id,
                unit_of_measurement="GBP",
            )

            # Get last recorded statistics to avoid duplicates
            last_usage_stat = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, usage_statistic_id, True, {"sum"}
            )
            last_cost_stat = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, cost_statistic_id, True, {"sum"}
            )

            _LOGGER.debug("last_usage_stat: %s", last_usage_stat)
            if not last_usage_stat or not last_usage_stat.get(usage_statistic_id):
                usage_sum = 0.0
                last_stats_time = None
                _LOGGER.debug("No existing usage stats, starting fresh")
            else:
                stats = last_usage_stat[usage_statistic_id]
                usage_sum = float(stats[0].get("sum", 0))
                last_stats_time = stats[0].get("start")

            if not last_cost_stat or not last_cost_stat.get(cost_statistic_id):
                cost_sum = 0.0
                last_cost_stats_time = None
            else:
                stats = last_cost_stat[cost_statistic_id]
                cost_sum = float(stats[0].get("sum", 0))
                last_cost_stats_time = stats[0].get("start")

            usage_statistics = []
            cost_statistics = []
            for reading in meter.readings:
                reading_date = reading.get("date")
                if not reading_date:
                    continue

                # Parse the date string (YYYY-MM-DD) as a local date
                # The reading represents the full day's usage, so place it
                # at 23:00 local time (end of day hourly bucket)
                try:
                    local_tz = dt_util.get_default_time_zone()
                    start = datetime.fromisoformat(reading_date).replace(
                        hour=23, minute=0, second=0, microsecond=0,
                        tzinfo=local_tz,
                    )
                except ValueError:
                    _LOGGER.debug("Could not parse date %s, skipping", reading_date)
                    continue

                raw_litres = reading.get("totalConsumptionLitres")
                raw_cost = reading.get("totalCostIncludingSewerage")
                if raw_litres is None or raw_cost is None:
                    _LOGGER.debug("Skipping %s: missing consumption or cost data", reading_date)
                    continue
                litres = float(raw_litres)
                cost = float(raw_cost)
                ts = start.timestamp()

                if last_stats_time is None or ts > last_stats_time:
                    usage_sum += litres
                    usage_statistics.append(
                        StatisticData(
                            start=start,
                            state=litres,
                            sum=usage_sum,
                        )
                    )

                if last_cost_stats_time is None or ts > last_cost_stats_time:
                    cost_sum += cost
                    cost_statistics.append(
                        StatisticData(
                            start=start,
                            state=cost,
                            sum=cost_sum,
                        )
                    )

            if usage_statistics:
                _LOGGER.debug(
                    "Adding %s usage statistics for %s",
                    len(usage_statistics),
                    usage_statistic_id,
                )
                async_add_external_statistics(
                    self.hass, usage_metadata, usage_statistics
                )
            if cost_statistics:
                _LOGGER.debug(
                    "Adding %s cost statistics for %s",
                    len(cost_statistics),
                    cost_statistic_id,
                )
                async_add_external_statistics(
                    self.hass, cost_metadata, cost_statistics
                )
