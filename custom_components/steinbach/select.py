"""Select platform for Steinbach Pool heat pumps (writable enum device points)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SteinbachDataUpdateCoordinator
from .entity import SteinbachEntity, model_property_specs

# Enum device points kept internal / handled elsewhere.
EXCLUDED_SELECT_CODES = {"temp_unit_convert"}

SELECT_TRANSLATION_KEYS = {"mode": "mode"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a select entity for every writable enum device point."""
    coordinator = entry.runtime_data
    entities = []
    for device_id, model in coordinator.models.items():
        for code, spec in model_property_specs(model).items():
            if code in EXCLUDED_SELECT_CODES:
                continue
            type_spec = spec.get("typeSpec", {})
            if type_spec.get("type") != "enum":
                continue
            if "w" not in spec.get("accessMode", ""):
                continue
            options = type_spec.get("range", [])
            if not options:
                continue
            entities.append(
                SteinbachSelect(coordinator, device_id, code, list(options))
            )
    async_add_entities(entities)


class SteinbachSelect(SteinbachEntity, SelectEntity):
    """A writable enum device point (e.g. heat/cool mode)."""

    def __init__(
        self,
        coordinator: SteinbachDataUpdateCoordinator,
        device_id: str,
        code: str,
        options: list[str],
    ) -> None:
        super().__init__(coordinator, device_id)
        self._code = code
        self._attr_unique_id = f"{device_id}_{code}_select"
        self._attr_options = options

        if (translation_key := SELECT_TRANSLATION_KEYS.get(code)) is not None:
            self._attr_translation_key = translation_key
        else:
            self._attr_name = code.replace("_", " ").title()

    @property
    def current_option(self) -> str | None:
        value = self._value(self._code)
        return value if value in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.api.send_commands,
            self._device_id,
            [{"code": self._code, "value": option}],
        )
        await self.coordinator.async_request_refresh()
