"""Yorkshire Water sensor platform."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .pyyorkshirewater.meter import SmartMeter

from homeassistant.components.sensor import (
    EntityCategory,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import YorkshireWaterConfigEntry, YorkshireWaterUpdateCoordinator
from .entity import YorkshireWaterEntity

PARALLEL_UPDATES = 0


class YorkshireWaterSensor(StrEnum):
    """Keys for Yorkshire Water sensors."""

    LATEST_CONSUMPTION = "latest_consumption"
    LATEST_COST = "latest_cost"
    YESTERDAY_CONSUMPTION = "yesterday_consumption"
    YESTERDAY_COST = "yesterday_cost"
    LAST_UPDATED = "last_updated"


@dataclass(frozen=True, kw_only=True)
class YorkshireWaterSensorEntityDescription(SensorEntityDescription):
    """Describes Yorkshire Water sensor entity."""

    value_fn: Callable[[SmartMeter], float | datetime | None]


ENTITY_DESCRIPTIONS: tuple[YorkshireWaterSensorEntityDescription, ...] = (
    YorkshireWaterSensorEntityDescription(
        key=YorkshireWaterSensor.LATEST_CONSUMPTION,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        value_fn=lambda meter: meter.latest_consumption,
        state_class=SensorStateClass.TOTAL,
        translation_key=YorkshireWaterSensor.LATEST_CONSUMPTION,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    YorkshireWaterSensorEntityDescription(
        key=YorkshireWaterSensor.LATEST_COST,
        native_unit_of_measurement="GBP",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda meter: meter.latest_cost,
        translation_key=YorkshireWaterSensor.LATEST_COST,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    YorkshireWaterSensorEntityDescription(
        key=YorkshireWaterSensor.YESTERDAY_CONSUMPTION,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        value_fn=lambda meter: meter.yesterday_consumption,
        state_class=SensorStateClass.TOTAL,
        translation_key=YorkshireWaterSensor.YESTERDAY_CONSUMPTION,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    YorkshireWaterSensorEntityDescription(
        key=YorkshireWaterSensor.YESTERDAY_COST,
        native_unit_of_measurement="GBP",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda meter: meter.yesterday_cost,
        translation_key=YorkshireWaterSensor.YESTERDAY_COST,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    YorkshireWaterSensorEntityDescription(
        key=YorkshireWaterSensor.LAST_UPDATED,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda meter: meter.last_updated,
        translation_key=YorkshireWaterSensor.LAST_UPDATED,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YorkshireWaterConfigEntry,
    async_add_devices: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_devices(
        YorkshireWaterSensorEntity(
            coordinator=entry.runtime_data,
            description=entity_description,
            smart_meter=smart_meter,
        )
        for entity_description in ENTITY_DESCRIPTIONS
        for smart_meter in entry.runtime_data.api.meters.values()
    )


class YorkshireWaterSensorEntity(YorkshireWaterEntity, SensorEntity):
    """Defines a Yorkshire Water sensor."""

    entity_description: YorkshireWaterSensorEntityDescription

    def __init__(
        self,
        coordinator: YorkshireWaterUpdateCoordinator,
        smart_meter: SmartMeter,
        description: YorkshireWaterSensorEntityDescription,
    ) -> None:
        """Initialize Yorkshire Water sensor."""
        super().__init__(coordinator, smart_meter, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | datetime | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.smart_meter)
