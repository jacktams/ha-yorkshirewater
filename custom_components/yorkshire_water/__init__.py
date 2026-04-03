"""The Yorkshire Water integration."""

from __future__ import annotations

import logging
from datetime import date

import voluptuous as vol
from aiohttp import CookieJar

from .pyyorkshirewater import YorkshireWater
from .pyyorkshirewater.auth import YorkshireWaterAuth
from .pyyorkshirewater.exceptions import AuthError, ApiError

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_ACCOUNT_NUMBER, DOMAIN
from .coordinator import YorkshireWaterConfigEntry, YorkshireWaterUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
_PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_FORCE_REFRESH = "force_refresh"
SERVICE_FORCE_REFRESH_SCHEMA = vol.Schema(
    {
        vol.Required("start_date"): str,
        vol.Required("end_date"): str,
    }
)


async def async_setup_entry(
    hass: HomeAssistant, entry: YorkshireWaterConfigEntry
) -> bool:
    """Set up Yorkshire Water from a config entry."""
    auth = YorkshireWaterAuth(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=async_create_clientsession(
            hass,
            cookie_jar=CookieJar(),
        ),
    )

    try:
        await auth.login()
    except AuthError as err:
        raise ConfigEntryAuthFailed from err

    _yw = YorkshireWater(authenticator=auth)

    # Validate meter exists for this account
    try:
        await _yw.api.get_meter_details(entry.data[CONF_ACCOUNT_NUMBER])
    except ApiError as err:
        raise ConfigEntryError(
            translation_domain=DOMAIN, translation_key="smart_meter_unavailable"
        ) from err

    entry.runtime_data = coordinator = YorkshireWaterUpdateCoordinator(
        hass=hass, api=_yw, config_entry=entry
    )

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    async def handle_force_refresh(call: ServiceCall) -> None:
        """Handle the force_refresh service call."""
        start = date.fromisoformat(str(call.data["start_date"]))
        end = date.fromisoformat(str(call.data["end_date"]))
        days = (end - start).days

        _LOGGER.debug("Force refresh: %s to %s (%d days)", start, end, days)

        account_ref = entry.data[CONF_ACCOUNT_NUMBER]
        meter_data = await coordinator.api.api.get_meter_details(account_ref)
        meter_ref = meter_data["meterReference"]

        consumption = await coordinator.api.api.get_daily_consumption(
            meter_ref, start, end
        )

        if meter_ref not in coordinator.api.meters:
            from .pyyorkshirewater.meter import SmartMeter
            coordinator.api.meters[meter_ref] = SmartMeter(meter_ref)
        coordinator.api.meters[meter_ref].update_reading_cache(
            consumption.get("dailyUsageData", [])
        )

        await coordinator._insert_statistics()
        _LOGGER.info(
            "Force refresh complete: %d readings fetched",
            len(consumption.get("dailyUsageData", [])),
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_REFRESH,
        handle_force_refresh,
        schema=SERVICE_FORCE_REFRESH_SCHEMA,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: YorkshireWaterConfigEntry
) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_FORCE_REFRESH)
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
