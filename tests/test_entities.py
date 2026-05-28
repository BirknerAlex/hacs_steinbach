"""Entity tests against the real e1ktcz2k device model."""

import copy
from unittest.mock import patch

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant

from tests.fixtures import DEVICE, DEVICE_ID, MODEL, PROPERTIES


async def test_climate_entity(hass: HomeAssistant, setup_integration):
    """The heat pump should be a single climate entity off/heat/cool."""
    state = hass.states.get("climate.warmepumpe_startis_inverto")
    assert state is not None
    # switch is False in the fixtures -> OFF
    assert state.state == HVACMode.OFF
    assert set(state.attributes["hvac_modes"]) == {
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
    }
    assert state.attributes["temperature"] == 28
    assert state.attributes["current_temperature"] == 25
    assert state.attributes["min_temp"] == 10
    assert state.attributes["max_temp"] == 45


async def test_temperature_sensors(hass: HomeAssistant, setup_integration):
    """Inlet / outlet / ambient temperature sensors carry the captured values."""
    inlet = hass.states.get("sensor.warmepumpe_startis_inverto_inlet_temperature")
    outlet = hass.states.get("sensor.warmepumpe_startis_inverto_outlet_temperature")
    ambient = hass.states.get("sensor.warmepumpe_startis_inverto_ambient_temperature")

    assert inlet is not None and inlet.state == "25"
    assert outlet is not None and outlet.state == "0"
    assert ambient is not None and ambient.state == "13"
    assert inlet.attributes["unit_of_measurement"] == "°C"
    assert inlet.attributes["device_class"] == "temperature"


async def test_diagnostic_sensors(hass: HomeAssistant, setup_integration):
    """Compressor frequency and expansion valve are exposed as diagnostics."""
    freq = hass.states.get("sensor.warmepumpe_startis_inverto_compressor_frequency")
    valve = hass.states.get(
        "sensor.warmepumpe_startis_inverto_expansion_valve_opening"
    )
    assert freq is not None and freq.state == "0"
    assert valve is not None and valve.state == "350"


async def test_fault_binary_sensor(hass: HomeAssistant, setup_integration):
    """Fault bitmap of 0 means no problem."""
    state = hass.states.get("binary_sensor.warmepumpe_startis_inverto_fault")
    assert state is not None
    assert state.state == "off"
    assert state.attributes["raw"] == 0
    assert state.attributes["active_faults"] == []


async def test_set_temperature_sends_command(
    hass: HomeAssistant, setup_integration, mock_client
):
    """Setting target temperature issues a temp_set command."""
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": "climate.warmepumpe_startis_inverto",
            ATTR_TEMPERATURE: 30,
        },
        blocking=True,
    )
    mock_client.send_commands.assert_called_once_with(
        DEVICE_ID, [{"code": "temp_set", "value": 30}]
    )


async def test_set_hvac_mode_heat_sends_commands(
    hass: HomeAssistant, setup_integration, mock_client
):
    """Selecting HEAT switches the pump on and sets Heating mode."""
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {
            "entity_id": "climate.warmepumpe_startis_inverto",
            "hvac_mode": HVACMode.HEAT,
        },
        blocking=True,
    )
    mock_client.send_commands.assert_called_once_with(
        DEVICE_ID,
        [{"code": "switch", "value": True}, {"code": "mode", "value": "Heating"}],
    )


async def test_target_temperature_number(hass: HomeAssistant, setup_integration):
    """temp_set is exposed as a number with model-driven limits."""
    state = hass.states.get(
        "number.warmepumpe_startis_inverto_target_temperature"
    )
    assert state is not None
    assert float(state.state) == 28.0
    assert state.attributes["min"] == 10
    assert state.attributes["max"] == 45
    assert state.attributes["step"] == 1


async def test_set_number_sends_command(
    hass: HomeAssistant, setup_integration, mock_client
):
    """Setting the number issues a temp_set command."""
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": "number.warmepumpe_startis_inverto_target_temperature",
            "value": 31,
        },
        blocking=True,
    )
    mock_client.send_commands.assert_called_once_with(
        DEVICE_ID, [{"code": "temp_set", "value": 31}]
    )


async def test_mode_select(hass: HomeAssistant, setup_integration):
    """mode is exposed as a select with the Heating/Cooling options."""
    state = hass.states.get("select.warmepumpe_startis_inverto_mode")
    assert state is not None
    assert state.state == "Heating"
    assert state.attributes["options"] == ["Heating", "Cooling"]


async def test_select_mode_sends_command(
    hass: HomeAssistant, setup_integration, mock_client
):
    """Choosing Cooling issues a mode command."""
    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": "select.warmepumpe_startis_inverto_mode",
            "option": "Cooling",
        },
        blocking=True,
    )
    mock_client.send_commands.assert_called_once_with(
        DEVICE_ID, [{"code": "mode", "value": "Cooling"}]
    )


async def test_power_switch(hass: HomeAssistant, setup_integration):
    """switch is exposed as a standalone power switch (off in the fixtures)."""
    state = hass.states.get("switch.warmepumpe_startis_inverto_power")
    assert state is not None
    assert state.state == "off"


async def test_power_switch_turn_on_sends_command(
    hass: HomeAssistant, setup_integration, mock_client
):
    """Turning the switch on issues a switch command."""
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.warmepumpe_startis_inverto_power"},
        blocking=True,
    )
    mock_client.send_commands.assert_called_once_with(
        DEVICE_ID, [{"code": "switch", "value": True}]
    )


async def test_available_when_cloud_reports_offline(
    hass: HomeAssistant, enable_custom_integrations, mock_config_entry
):
    """Entities stay available even when the device list reports online=False.

    The Tuya online flag is unreliable (it flips false while the pump is off),
    so availability must follow a successful property read instead.
    """
    offline_device = copy.deepcopy(DEVICE)
    offline_device["online"] = False

    with patch(
        "custom_components.steinbach.coordinator.TuyaOpenAPIClient"
    ) as client_cls:
        instance = client_cls.return_value
        instance.get_devices.return_value = [offline_device]
        instance.get_model.return_value = copy.deepcopy(MODEL)
        instance.get_properties.return_value = copy.deepcopy(PROPERTIES)

        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(
        "sensor.warmepumpe_startis_inverto_inlet_temperature"
    )
    assert state is not None
    assert state.state == "25"
