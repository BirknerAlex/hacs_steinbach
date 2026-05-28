"""Switch platform for Steinbach Pool heat pumps (writable boolean device points)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SteinbachDataUpdateCoordinator
from .entity import SteinbachEntity, model_property_specs

SWITCH_TRANSLATION_KEYS = {"switch": "power"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a switch entity for every writable boolean device point."""
    coordinator = entry.runtime_data
    entities = []
    for device_id, model in coordinator.models.items():
        for code, spec in model_property_specs(model).items():
            if spec.get("typeSpec", {}).get("type") != "bool":
                continue
            if "w" not in spec.get("accessMode", ""):
                continue
            entities.append(SteinbachSwitch(coordinator, device_id, code))
    async_add_entities(entities)


class SteinbachSwitch(SteinbachEntity, SwitchEntity):
    """A writable boolean device point (e.g. power)."""

    def __init__(
        self,
        coordinator: SteinbachDataUpdateCoordinator,
        device_id: str,
        code: str,
    ) -> None:
        super().__init__(coordinator, device_id)
        self._code = code
        self._attr_unique_id = f"{device_id}_{code}_switch"

        if (translation_key := SWITCH_TRANSLATION_KEYS.get(code)) is not None:
            self._attr_translation_key = translation_key
        else:
            self._attr_name = code.replace("_", " ").title()

    @property
    def is_on(self) -> bool | None:
        value = self._value(self._code)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, value: bool) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.api.send_commands,
            self._device_id,
            [{"code": self._code, "value": value}],
        )
        await self.coordinator.async_request_refresh()
