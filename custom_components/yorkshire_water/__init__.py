"""The Yorkshire Water integration."""

from __future__ import annotations

from aiohttp import CookieJar
from .pyyorkshirewater import YorkshireWater
from .pyyorkshirewater.auth import YorkshireWaterAuth
from .pyyorkshirewater.exceptions import AuthError, ApiError

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_ACCOUNT_NUMBER, DOMAIN
from .coordinator import YorkshireWaterConfigEntry, YorkshireWaterUpdateCoordinator

_PLATFORMS: list[Platform] = [Platform.SENSOR]


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
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: YorkshireWaterConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
