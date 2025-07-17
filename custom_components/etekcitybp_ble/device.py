"""The EtekcityBP device."""

from __future__ import annotations
from dataclasses import dataclass

import logging

from collections.abc import Callable
from typing import Any

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .const import MFR_ID

_LOGGER = logging.getLogger(__name__)


@dataclass
class EtekcityBPData:
    """EtekcityBP data."""

    address: str | None = None
    device: BLEDevice | None = None
    rssi: int | None = None
    mfr_id: int | None = None
    mfr_data: bytes | None = None
    sensor_data: dict[str, Any] | None = None
    active: bool = False
    # systolic: int | None = None
    # diastolic: int | None = None
    # pulse: int | None = None
    # battery_percent: int | None = None
    # timestamp: int | None = None


class EtekcityBPDevice():

    def __init__(
        self,
    ) -> None:
        _LOGGER.debug("In EtekcityBPDevice init")
        self._data: EtekcityBPData = EtekcityBPData(
            sensor_data={
                "systolic0": None, 
                "diastolic0": None, 
                "pulse0": None, 
                "irregular_heartbeat0": None,
                "systolic1": None, 
                "diastolic1": None, 
                "pulse1": None,
                "irregular_heartbeat1": None,
                "display_units": None,
                }
            )
        self._callbacks: list[Callable[[], None]] = []
        self._user = None  # Placeholder for user

    def poll_needed(self, seconds_since_last_poll: float | None) -> bool:
        """Return if device needs polling."""
        _LOGGER.debug("In EtekcityBPDevice poll_needed")
        return True

    def parse_advertisement_data(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData,
    ) -> bool | None:
        """Parse advertisement data."""
        _LOGGER.debug("In EtekcityBPDevice parse_advertisement_data")
        _mfr_data = None
        if MFR_ID in advertisement_data.manufacturer_data:
            _mfr_data = advertisement_data.manufacturer_data[MFR_ID]

        if _mfr_data is None:
            return None

        self._data.address = device.address
        self._data.device = device
        self._data.rssi = advertisement_data.rssi
        self._data.mfr_id = MFR_ID
        self._data.mfr_data=_mfr_data

        return True

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to device notifications."""
        _LOGGER.debug("In EtekcityBPDevice subscribe")
        self._callbacks.append(callback)

        def _unsub() -> None:
            """Unsubscribe from device notifications."""
            self._callbacks.remove(callback)

        return _unsub

    async def update(self, data: bytes):
        """Update values from notification packet."""
        header = int.from_bytes(data[0:2], "big")
        if header == 0xA502 and len(data) == 13:
            _LOGGER.debug(f"Advertisement received")
            self.update_value("display_units", "kPa" if data[10] == 0x01 else "mmHg")
        elif header == 0xA522 and len(data) == 20:
            self._user = data[14]
            self.update_value(f"systolic{self._user}", data[15])
            self.update_value(f"diastolic{self._user}", data[17])
        elif data[0] == 0x00 and len(data) == 5:
            self.update_value(f"pulse{self._user}", data[1])
            self.update_value(f"irregular_heartbeat{self._user}", True if data[3] == 0x04 else False)

    def update_value(self, parameter: str, value: int):
        """Update single value."""
        _LOGGER.debug(f"Updating device {parameter} to {value}")
        self._data.sensor_data[parameter] = value

    def supported(self, discovery_info) -> bool:
        """Return if device is supported."""
        _LOGGER.debug("In EtekcityBPDevice supported")
        return discovery_info.manufacturer_data and MFR_ID in discovery_info.manufacturer_data

    @property
    def name(self) -> str:
        """Return device name."""
        _LOGGER.debug("In EtekcityBPDevice name")
        return f"{self._device.name} ({self._device.address})"

    @property
    def sensor_data(self) -> dict[str, Any]:
        """Return parsed device data."""
        return self._data.sensor_data if self._data else {}

    @property
    def rssi(self) -> int:
        """Return RSSI of device."""
        _LOGGER.debug("In EtekcityBPDevice rssi")
        if self._data:
            return self._data.rssi
        return -127

