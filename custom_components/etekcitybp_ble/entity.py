"""An abstract class common to all EtekcityBP entities."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.const import (
    ATTR_CONNECTIONS, 
    STATE_UNAVAILABLE, 
    STATE_UNKNOWN
)
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EtekcityBPCoordinator
from .device import EtekcityBPDevice

IGNORED_STATES = {STATE_UNAVAILABLE, STATE_UNKNOWN}

_LOGGER = logging.getLogger(__name__)


class EtekcityBPEntity(RestoreEntity):
    """Generic entity encapsulating common features of EtekcityBP device."""

    _device: EtekcityBPDevice
    _attr_has_entity_name = True

    def __init__(self, coordinator: EtekcityBPCoordinator) -> None:
        """Initialize the entity."""
        self._device = coordinator.device
        self._last_run_success: bool | None = None
        self._address = coordinator.address
        self._attr_unique_id = coordinator.base_unique_id
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_BLUETOOTH, self._address)},
            manufacturer=MANUFACTURER,
            name=coordinator.device_name,
        )
        if ":" not in self._address:
            # MacOS Bluetooth addresses are not mac addresses
            return
        # If the bluetooth address is also a mac address,
        # add this connection as well to prevent a new device
        # entry from being created when upgrading from a previous
        # version of the integration.
        self._attr_device_info[ATTR_CONNECTIONS].add(
            (dr.CONNECTION_NETWORK_MAC, self._address)
        )

    @property
    def sensor_data(self) -> dict[str, Any]:
        """Return parsed device data for this entity."""
        return self.coordinator.device.sensor_data

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        return {"last_run_success": self._last_run_success}

    @callback
    def _async_update_attrs(self) -> None:
        """Update the entity attributes."""
        _LOGGER.debug("In EtekcityBPEntity _async_update_attrs")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        _LOGGER.debug(
            "_handle_coordinator_update: Updating entity %s with data: %s",
            self._attr_unique_id,
            self.sensor_data,
        )  
        self._async_update_attrs()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        _LOGGER.debug("async_added_to_hass: Adding entity %s", self._attr_unique_id)
        await super().async_added_to_hass()
        self.async_on_remove(self._device.subscribe(self._handle_coordinator_update))

        # Set initial state based on the last known state and sensor data
        last_state = await self.async_get_last_state()
        # last_sensor_data = await self.async_get_last_sensor_data()
        _LOGGER.debug(f"last_state: {last_state}")
        # _LOGGER.debug(f"last_sensor_data: {last_sensor_data}")

        # if not last_state or not last_sensor_data or last_state.state in IGNORED_STATES:
        if not last_state or last_state.state in IGNORED_STATES:
            return
        # _LOGGER.debug(f"Restoring sensor to {last_sensor_data.native_value}")
        _LOGGER.debug(f"Restoring sensor to {last_state.state}")
        self._attr_native_value = last_state.state
        self._device.update_value(self._sensor, last_state.state)
