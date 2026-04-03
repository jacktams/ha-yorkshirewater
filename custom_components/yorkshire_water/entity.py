"""Yorkshire Water entity."""

from __future__ import annotations

import logging

from .pyyorkshirewater.meter import SmartMeter

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YorkshireWaterUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class YorkshireWaterEntity(CoordinatorEntity[YorkshireWaterUpdateCoordinator]):
    """Defines a Yorkshire Water entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YorkshireWaterUpdateCoordinator,
        smart_meter: SmartMeter,
        key: str,
    ) -> None:
        """Initialize Yorkshire Water entity."""
        super().__init__(coordinator)
        self.smart_meter = smart_meter
        self._attr_unique_id = f"{smart_meter.serial_number}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, smart_meter.serial_number)},
            name=smart_meter.serial_number,
            manufacturer="Yorkshire Water",
            serial_number=smart_meter.serial_number,
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.coordinator.api.register_callback(self._handle_update)
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        self.coordinator.api.remove_callback(self._handle_update)
        await super().async_will_remove_from_hass()

    def _handle_update(self, _meter: SmartMeter) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
