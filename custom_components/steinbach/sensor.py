"""Sensor platform for Steinbach Pool heat pumps."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfFrequency,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CLIMATE_CODES, FAULT_CODE
from .coordinator import SteinbachDataUpdateCoordinator
from .entity import SteinbachEntity, model_property_specs

# Curated descriptions for the well-known Steinbach heat-pump device points.
SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "inwt_temp": SensorEntityDescription(
        key="inwt_temp",
        translation_key="inlet_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "outwt_temp": SensorEntityDescription(
        key="outwt_temp",
        translation_key="outlet_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "whj_temp": SensorEntityDescription(
        key="whj_temp",
        translation_key="ambient_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "return_temperature": SensorEntityDescription(
        key="return_temperature",
        translation_key="suction_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "cmp_temp": SensorEntityDescription(
        key="cmp_temp",
        translation_key="discharge_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "p_temp": SensorEntityDescription(
        key="p_temp",
        translation_key="coil_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "operating_frequency": SensorEntityDescription(
        key="operating_frequency",
        translation_key="operating_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "expansion_valve": SensorEntityDescription(
        key="expansion_valve",
        translation_key="expansion_valve",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}

_TEMPERATURE_UNITS = {"℃", "°C", "C"}


def _generic_description(code: str, type_spec: dict) -> SensorEntityDescription:
    """Build a fallback description for an unmapped numeric device point."""
    unit = type_spec.get("unit")
    if unit in _TEMPERATURE_UNITS:
        return SensorEntityDescription(
            key=code,
            name=code.replace("_", " ").title(),
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    return SensorEntityDescription(
        key=code,
        name=code.replace("_", " ").title(),
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a sensor for every read-only numeric device point."""
    coordinator = entry.runtime_data
    entities = []
    for device_id, model in coordinator.models.items():
        for code, spec in model_property_specs(model).items():
            if code in CLIMATE_CODES or code == FAULT_CODE:
                continue
            type_spec = spec.get("typeSpec", {})
            if type_spec.get("type") != "value":
                continue
            if "r" not in spec.get("accessMode", "ro"):
                continue
            description = SENSOR_DESCRIPTIONS.get(code) or _generic_description(
                code, type_spec
            )
            scale = 10 ** int(type_spec.get("scale", 0))
            entities.append(
                SteinbachSensor(coordinator, device_id, description, scale)
            )
    async_add_entities(entities)


class SteinbachSensor(SteinbachEntity, SensorEntity):
    """A read-only numeric device point as a sensor."""

    def __init__(
        self,
        coordinator: SteinbachDataUpdateCoordinator,
        device_id: str,
        description: SensorEntityDescription,
        scale: int,
    ) -> None:
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._scale = scale
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        value = self._value(self.entity_description.key)
        if value is None:
            return None
        if isinstance(value, (int, float)) and self._scale != 1:
            return value / self._scale
        return value
