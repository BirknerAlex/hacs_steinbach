"""Number platform for Steinbach Pool heat pumps (writable setpoints)."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SteinbachDataUpdateCoordinator
from .entity import SteinbachEntity, model_property_specs

# Writable numeric setpoints to expose as their own control. The target water
# temperature (`temp_set`) is also reachable via the climate entity; this gives
# a standalone slider/box with the min/max/step read straight from the model.
NUMBER_TRANSLATION_KEYS = {"temp_set": "target_temperature"}

_TEMPERATURE_UNITS = {"℃", "°C", "C"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a number entity for every writable numeric device point."""
    coordinator = entry.runtime_data
    entities = []
    for device_id, model in coordinator.models.items():
        for code, spec in model_property_specs(model).items():
            type_spec = spec.get("typeSpec", {})
            if type_spec.get("type") != "value":
                continue
            if "w" not in spec.get("accessMode", ""):
                continue
            entities.append(
                SteinbachNumber(coordinator, device_id, code, type_spec)
            )
    async_add_entities(entities)


class SteinbachNumber(SteinbachEntity, NumberEntity):
    """A writable numeric device point (e.g. target water temperature)."""

    _attr_mode = NumberMode.AUTO

    def __init__(
        self,
        coordinator: SteinbachDataUpdateCoordinator,
        device_id: str,
        code: str,
        type_spec: dict,
    ) -> None:
        super().__init__(coordinator, device_id)
        self._code = code
        self._attr_unique_id = f"{device_id}_{code}_number"
        self._scale = 10 ** int(type_spec.get("scale", 0))
        self._attr_native_min_value = type_spec.get("min", 0) / self._scale
        self._attr_native_max_value = type_spec.get("max", 100) / self._scale
        self._attr_native_step = type_spec.get("step", 1) / self._scale

        if (translation_key := NUMBER_TRANSLATION_KEYS.get(code)) is not None:
            self._attr_translation_key = translation_key
        else:
            self._attr_name = code.replace("_", " ").title()

        if type_spec.get("unit") in _TEMPERATURE_UNITS:
            self._attr_device_class = NumberDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        value = self._value(self._code)
        if value is None:
            return None
        return value / self._scale

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.api.send_commands,
            self._device_id,
            [{"code": self._code, "value": int(round(value * self._scale))}],
        )
        await self.coordinator.async_request_refresh()
