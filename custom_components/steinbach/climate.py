"""Climate platform for Steinbach Pool heat pumps."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SteinbachDataUpdateCoordinator
from .entity import SteinbachEntity, model_property_specs

if TYPE_CHECKING:
    from . import SteinbachConfigEntry

# Tuya `mode` enum value <-> Home Assistant HVAC mode.
TUYA_TO_HVAC = {"Heating": HVACMode.HEAT, "Cooling": HVACMode.COOL}
HVAC_TO_TUYA = {value: key for key, value in TUYA_TO_HVAC.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SteinbachConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a climate entity per heat pump."""
    coordinator = entry.runtime_data
    entities = []
    for device_id, model in coordinator.models.items():
        specs = model_property_specs(model)
        if "switch" in specs and "temp_set" in specs:
            entities.append(SteinbachClimate(coordinator, device_id, specs))
    async_add_entities(entities)


class SteinbachClimate(SteinbachEntity, ClimateEntity):
    """A Steinbach pool heat pump as a climate entity."""

    _attr_name = None
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        coordinator: SteinbachDataUpdateCoordinator,
        device_id: str,
        specs: dict[str, dict],
    ) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_climate"
        self._has_mode = "mode" in specs

        target_spec = specs["temp_set"].get("typeSpec", {})
        self._target_scale = 10 ** int(target_spec.get("scale", 0))
        self._attr_target_temperature_step = (
            target_spec.get("step", 1) / self._target_scale
        )
        self._attr_min_temp = target_spec.get("min", 10) / self._target_scale
        self._attr_max_temp = target_spec.get("max", 45) / self._target_scale

        current_spec = specs.get("temp_current", {}).get("typeSpec", {})
        self._current_scale = 10 ** int(current_spec.get("scale", 0))

        modes: list[HVACMode] = [HVACMode.OFF]
        mode_range = specs.get("mode", {}).get("typeSpec", {}).get("range", [])
        for value in mode_range:
            if value in TUYA_TO_HVAC and TUYA_TO_HVAC[value] not in modes:
                modes.append(TUYA_TO_HVAC[value])
        if len(modes) == 1:
            modes.append(HVACMode.HEAT)
        self._attr_hvac_modes = modes

    @property
    def temperature_unit(self) -> str:
        if self._value("temp_unit_convert") == "f":
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> float | None:
        value = self._value("temp_current")
        if value is None:
            value = self._value("inwt_temp")
        if value is None:
            return None
        return value / self._current_scale

    @property
    def target_temperature(self) -> float | None:
        value = self._value("temp_set")
        if value is None:
            return None
        return value / self._target_scale

    @property
    def hvac_mode(self) -> HVACMode:
        if not self._value("switch"):
            return HVACMode.OFF
        return TUYA_TO_HVAC.get(self._value("mode"), HVACMode.HEAT)

    @property
    def hvac_action(self) -> HVACAction:
        if not self._value("switch"):
            return HVACAction.OFF
        frequency = self._value("operating_frequency")
        if frequency is not None and frequency == 0:
            return HVACAction.IDLE
        if self._value("mode") == "Cooling":
            return HVACAction.COOLING
        return HVACAction.HEATING

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        value = int(round(temperature * self._target_scale))
        await self._send([{"code": "temp_set", "value": value}])

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send([{"code": "switch", "value": False}])
            return
        commands: list[dict] = [{"code": "switch", "value": True}]
        if self._has_mode and hvac_mode in HVAC_TO_TUYA:
            commands.append({"code": "mode", "value": HVAC_TO_TUYA[hvac_mode]})
        await self._send(commands)

    async def async_turn_on(self) -> None:
        await self._send([{"code": "switch", "value": True}])

    async def async_turn_off(self) -> None:
        await self._send([{"code": "switch", "value": False}])

    async def _send(self, commands: list[dict]) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.api.send_commands, self._device_id, commands
        )
        await self.coordinator.async_request_refresh()
