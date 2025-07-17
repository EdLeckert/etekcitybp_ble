"""Support for EtekcityBP sensors."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.const import (
        EntityCategory,
        SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        UnitOfPressure,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BPM
from .coordinator import EtekcityConfigEntry, EtekcityBPCoordinator
from .entity import EtekcityBPEntity

import logging

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    "rssi": SensorEntityDescription(
        key="rssi",
        translation_key="bluetooth_signal",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "systolic0": SensorEntityDescription(
        key="systolic0",
        name ="Systolic Pressure User 1",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MMHG,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision = 0,
        suggested_unit_of_measurement=UnitOfPressure.MMHG,
    ),
    "diastolic0": SensorEntityDescription(
        key="diastolic0",
        name ="Diastolic Pressure User 1",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MMHG,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision = 0,
        suggested_unit_of_measurement=UnitOfPressure.MMHG,
    ),
    "pulse0": SensorEntityDescription(
        key="pulse0",
        name ="Pulse User 1",
        native_unit_of_measurement=BPM,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision = 0,
    ),
    "systolic1": SensorEntityDescription(
        key="systolic1",
        name ="Systolic Pressure User 2",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MMHG,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision = 0,
        suggested_unit_of_measurement=UnitOfPressure.MMHG,
    ),
    "diastolic1": SensorEntityDescription(
        key="diastolic1",
        name ="Diastolic Pressure User 2",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MMHG,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision = 0,
        suggested_unit_of_measurement=UnitOfPressure.MMHG,
    ),
    "pulse1": SensorEntityDescription(
        key="pulse1",
        name ="Pulse User 2",
        native_unit_of_measurement=BPM,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision = 0,
    ),
    "display_units": SensorEntityDescription(
        key="display_units",
        name ="Display Units",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EtekcityConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor entities for the EtekcityBP integration."""
    coordinator = entry.runtime_data

    entities = [
        EtekcityBPSensor(coordinator, sensor)
        for sensor in SENSOR_TYPES
        if sensor != "rssi" 
    ]
    entities.append(EtekcityBPRSSISensor(coordinator, "rssi"))
    _LOGGER.debug(f"Adding entities: {entities}")
    async_add_entities(entities)

   
class EtekcityBPSensor(EtekcityBPEntity, SensorEntity):
    """Representation of a EtekcityBP sensor."""
    def __init__(
        self,
        coordinator: EtekcityBPCoordinator,
        sensor: str,
    ) -> None:
        """Initialize the EtekcityBP sensor."""
        _LOGGER.debug(f"Initializing sensor: {sensor}")
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._sensor = sensor
        self._attr_unique_id = f"{coordinator.base_unique_id}-{sensor}"
        self.entity_description = SENSOR_TYPES[sensor]

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        value = self.sensor_data.get(self._sensor, self._attr_native_value)
        _LOGGER.debug(f"{self._sensor} native_value: {value}")
        return value



class EtekcityBPRSSISensor(EtekcityBPSensor):
    """Representation of a EtekcityBP RSSI sensor."""

    @property
    def native_value(self) -> str | int | None:
        """Return the state of the sensor."""
        if service_info := async_last_service_info(
            self.hass, self._address, self.coordinator.connectable
        ):
            _LOGGER.debug(f"rssi: {service_info.rssi}")
            return service_info.rssi
        return None