"""Binary sensor platform for Steinbach Pool heat pumps."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import FAULT_CODE
from .coordinator import SteinbachDataUpdateCoordinator
from .entity import SteinbachEntity, model_property_specs


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a fault binary sensor for every device that reports one."""
    coordinator = entry.runtime_data
    entities = []
    for device_id, model in coordinator.models.items():
        specs = model_property_specs(model)
        if FAULT_CODE in specs:
            labels = specs[FAULT_CODE].get("typeSpec", {}).get("label", [])
            entities.append(SteinbachFault(coordinator, device_id, labels))
    async_add_entities(entities)


class SteinbachFault(SteinbachEntity, BinarySensorEntity):
    """Problem sensor backed by the device's fault bitmap."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "fault"

    def __init__(
        self,
        coordinator: SteinbachDataUpdateCoordinator,
        device_id: str,
        labels: list[str],
    ) -> None:
        super().__init__(coordinator, device_id)
        self._labels = labels
        self._attr_unique_id = f"{device_id}_fault"

    @property
    def is_on(self) -> bool | None:
        value = self._value(FAULT_CODE)
        if value is None:
            return None
        return int(value) != 0

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        value = self._value(FAULT_CODE)
        raw = int(value) if value is not None else 0
        active = [
            self._labels[bit] if bit < len(self._labels) else f"fault_bit{bit}"
            for bit in range(raw.bit_length())
            if raw & (1 << bit)
        ]
        return {"raw": raw, "active_faults": active}
