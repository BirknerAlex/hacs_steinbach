"""DataUpdateCoordinator for the Steinbach Pool integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import TuyaOpenAPIClient
from .api.error import ApiError, AuthenticationError
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_REGION,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Mapping of device_id -> {device-point code -> value}.
type CoordinatorData = dict[str, dict[str, Any]]


class SteinbachDataUpdateCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Polls the Tuya OpenAPI for all heat pumps linked to the project."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.api = TuyaOpenAPIClient(
            config_entry.data[CONF_ACCESS_ID],
            config_entry.data[CONF_ACCESS_SECRET],
            config_entry.data.get(CONF_REGION, DEFAULT_REGION),
        )
        # device_id -> device descriptor from the device list (name, model, ...).
        self.devices: dict[str, dict] = {}
        # device_id -> parsed device model, fetched once during setup.
        self.models: dict[str, dict | None] = {}

        poll_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_interval=timedelta(seconds=poll_interval),
        )

    async def _async_setup(self) -> None:
        """Fetch the device list and each device's model once before polling.

        The device descriptors and models are static for the life of the entry,
        so they are fetched here rather than on every poll.
        """
        try:
            devices = await self.hass.async_add_executor_job(self.api.get_devices)
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(err) from err
        except ApiError as err:
            raise UpdateFailed(err) from err

        self.devices = {device["id"]: device for device in devices}
        for device_id in self.devices:
            try:
                self.models[device_id] = await self.hass.async_add_executor_job(
                    self.api.get_model, device_id
                )
            except ApiError as err:
                _LOGGER.warning(
                    "Could not fetch model for device %s: %s", device_id, err
                )
                self.models[device_id] = None

    async def _async_update_data(self) -> CoordinatorData:
        """Fetch fresh device-point values for every linked device.

        Reachability is judged by whether the property read succeeds, not by the
        device list's ``online`` flag — that flag is unreliable and reports
        offline (e.g. while the pump is switched off) even though the cloud still
        returns current values.
        """
        data: CoordinatorData = {}
        for device_id in self.devices:
            try:
                properties = await self.hass.async_add_executor_job(
                    self.api.get_properties, device_id
                )
            except AuthenticationError as err:
                raise ConfigEntryAuthFailed(err) from err
            except ApiError as err:
                _LOGGER.warning(
                    "Could not fetch properties for device %s: %s", device_id, err
                )
                # Keep the last known values across a transient hiccup.
                if self.data and device_id in self.data:
                    data[device_id] = self.data[device_id]
                continue

            data[device_id] = {prop["code"]: prop["value"] for prop in properties}

        return data
