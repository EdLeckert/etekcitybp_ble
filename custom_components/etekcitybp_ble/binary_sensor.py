"""Support for EtekcityBP sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EtekcityConfigEntry, EtekcityBPCoordinator
from .entity import EtekcityBPEntity

import logging

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: dict[str, BinarySensorEntityDescription] = {
    "irregular_heartbeat0": BinarySensorEntityDescription(
        key="irregular_heartbeat0",
        name ="Irregular Heartbeat User 1",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    "irregular_heartbeat1": BinarySensorEntityDescription(
        key="irregular_heartbeat1",
        name ="Irregular Heartbeat User 2",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtekcityConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor entities for the EtekcityBP integration."""
    coordinator = entry.runtime_data

    entities = [
        EtekcityBPBinarySensor(coordinator, sensor)
        for sensor in SENSOR_TYPES
    ]
    async_add_entities(entities)

   
class EtekcityBPBinarySensor(EtekcityBPEntity, BinarySensorEntity):
    """Representation of a EtekcityBP binary sensor."""
    def __init__(
        self,
        coordinator: EtekcityBPCoordinator,
        sensor: str,
    ) -> None:
        """Initialize the EtekcityBP binary sensor."""
        _LOGGER.debug(f"Initializing binary sensor: {sensor}")
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._sensor = sensor
        self._attr_unique_id = f"{coordinator.base_unique_id}-{sensor}"
        self.entity_description = SENSOR_TYPES[sensor]

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        value = self.sensor_data.get(self._sensor, self._attr_is_on)
        _LOGGER.debug(f"{self._sensor} is_on: {value}")
        return value

