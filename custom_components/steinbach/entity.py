"""Shared base entity and model helpers for Steinbach Pool."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SteinbachDataUpdateCoordinator


def model_property_specs(model: dict | None) -> dict[str, dict]:
    """Flatten a device model into a ``code -> property spec`` mapping."""
    specs: dict[str, dict] = {}
    if not model:
        return specs
    for service in model.get("services", []):
        for prop in service.get("properties", []):
            specs[prop["code"]] = prop
    return specs


class SteinbachEntity(CoordinatorEntity[SteinbachDataUpdateCoordinator]):
    """Base entity tying an entity to one Tuya device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SteinbachDataUpdateCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        info = self.coordinator.devices.get(self._device_id, {})
        model = self.coordinator.models.get(self._device_id)
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=MANUFACTURER,
            name=info.get("name"),
            model=info.get("product_name"),
            sw_version=model.get("modelId") if model else None,
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data is not None
            and self._device_id in self.coordinator.data
        )

    def _value(self, code: str) -> Any:
        return (self.coordinator.data or {}).get(self._device_id, {}).get(code)
