"""Provides the EtekcityBP ActiveBluetooth DataUpdateCoordinator."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from bleak import BleakClient

from typing import TYPE_CHECKING

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataUpdate,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant, callback

from .const import (
    CHARACTERISTIC_BLOOD_PRESSURE,
    CLIENT_CHARACTERISTIC_CONFIG_HANDLE,
    CLIENT_CHARACTERISTIC_CONFIG_DATA,
)
from .device import EtekcityBPDevice


if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)

DEVICE_STARTUP_TIMEOUT = 30

type EtekcityConfigEntry = ConfigEntry[EtekcityBPCoordinator]

class EtekcityBPCoordinator(
    ActiveBluetoothProcessorCoordinator [None]
):
    """Class to manage fetching data."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        address: str,
        device: EtekcityBPDevice,
        base_unique_id: str,
        device_name: str,
        connectable: bool,
    ) -> None:
        """Initialize data coordinator."""
        super().__init__(
            hass=hass,
            logger=logger,
            address=address,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            update_method=self._update_method,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_update,
            connectable=connectable,
        )
        self.address = address
        self.device = device
        self.device_name = device_name
        self.base_unique_id = base_unique_id
        self._ready_event = asyncio.Event()
        self._was_unavailable = True

        _LOGGER.debug("In EtekcityBPCoordinator init")
        _LOGGER.debug(f"Scanner count: {bluetooth.async_scanner_count(hass, connectable=True)}")

    @callback
    def _needs_poll(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        seconds_since_last_poll: float | None,
    ) -> bool:
        # Only poll if hass is running, we need to poll,
        # and we actually have a way to connect to the device
        _LOGGER.debug("In _needs_poll callback")
        needs_poll = (
            self.hass.state == CoreState.running
            and self.device.poll_needed(seconds_since_last_poll)
            and bool(
                bluetooth.async_ble_device_from_address(
                    self.hass, service_info.device.address, connectable=True
                )
            )
        )
        _LOGGER.debug(f"needs_poll1: {self.hass.state == CoreState.running}")
        _LOGGER.debug(f"needs_poll2: {self.device.poll_needed(seconds_since_last_poll)}")
        _LOGGER.debug(f"needs_poll3: {bool(bluetooth.async_ble_device_from_address(self.hass, service_info.device.address, connectable=True))}")
        return needs_poll

    def _update_method(self, service_info) -> PassiveBluetoothDataUpdate:
        """Update method for the coordinator."""
        _LOGGER.debug(f"In _update_method, service_info: {service_info}")
        # This method is called when the coordinator is updated.
        # It can be used to update the device state or perform other actions.
        if self._was_unavailable:
            _LOGGER.info("Device %s is now available", self.device_name)
            self._was_unavailable = False
            self._ready_event.set()

    async def _async_update(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Poll the device."""
        _LOGGER.debug("In _async_update")
        while self._available:
            try:
                _LOGGER.debug(f"Connecting to device {service_info.device.address}")
                async with BleakClient(service_info.device) as client:
                    if (not client.is_connected):
                        raise "client not connected"

                    _LOGGER.debug ("Starting notifications")
                    await client.start_notify(CHARACTERISTIC_BLOOD_PRESSURE, self._notification_handler)
                    await client.write_gatt_descriptor(CLIENT_CHARACTERISTIC_CONFIG_HANDLE, CLIENT_CHARACTERISTIC_CONFIG_DATA)
                    await asyncio.sleep(5)

                    _LOGGER.debug ("Pausing notification processing")
                    async with asyncio.timeout(10):
                        await client.stop_notify(CHARACTERISTIC_BLOOD_PRESSURE)
                    await asyncio.sleep(1)
            except Exception as e:
                _LOGGER.debug(f"Error {e}; Long pausing notification processing")
                await asyncio.sleep(30)

    @callback
    async def _notification_handler(self, handle, data):
        """Handle notifications from the device."""
        _LOGGER.debug("In _notification_handler")
        _LOGGER.debug(f"Handle: {handle}, Data: {data.hex()}")

        await self.device.update(data)

    @callback
    def _async_handle_unavailable(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""
        _LOGGER.debug("In _async_handle_unavailable")

        super()._async_handle_unavailable(service_info)
        self._was_unavailable = True
        self._available = False
        _LOGGER.info("Device %s is unavailable", self.device_name)


    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        super()._async_handle_bluetooth_event(service_info, change)
        # Process incoming advertisement data
        _LOGGER.debug("In _async_handle_bluetooth_event")
        _LOGGER.debug(f"service_info: {service_info}")
        _LOGGER.debug(f"change: {change}")

        if not (
            self.device.parse_advertisement_data(
                service_info.device, service_info.advertisement
            )
        ):
            return

        self._ready_event.set()
        self._was_unavailable = False

    async def async_wait_ready(self) -> bool:
        """Wait for the device to be ready."""
        _LOGGER.debug("In async_wait_ready")
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(DEVICE_STARTUP_TIMEOUT):
                _LOGGER.debug("Waiting for device to be ready")
                await self._ready_event.wait()
                _LOGGER.info("Device %s is online", self.device_name)
                self._available = True
                return True
        return False

    @callback
    def _async_handle_bluetooth_poll(self) -> None:
        """Handle a poll event."""
        _LOGGER.debug("In _async_handle_bluetooth_poll")
        self.async_update_listeners()
