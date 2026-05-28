"""Fixtures for Steinbach Pool integration tests."""

from __future__ import annotations

import copy
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.steinbach.const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_REGION,
    DOMAIN,
)
from tests.fixtures import DEVICE, MODEL, PROPERTIES

ACCESS_ID = "test_access_id"


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A config entry pre-populated with valid-looking Tuya credentials."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Steinbach Pool",
        data={
            CONF_ACCESS_ID: ACCESS_ID,
            CONF_ACCESS_SECRET: "secret",
            CONF_REGION: "eu",
        },
        options={CONF_SCAN_INTERVAL: 60},
        unique_id=ACCESS_ID,
    )


@pytest.fixture
def mock_client():
    """Patch TuyaOpenAPIClient everywhere it is instantiated."""
    with (
        patch(
            "custom_components.steinbach.coordinator.TuyaOpenAPIClient"
        ) as coord_cls,
        patch(
            "custom_components.steinbach.config_flow.TuyaOpenAPIClient"
        ) as flow_cls,
    ):
        instance = coord_cls.return_value
        instance.get_devices.return_value = [copy.deepcopy(DEVICE)]
        instance.get_model.return_value = copy.deepcopy(MODEL)
        instance.get_properties.return_value = copy.deepcopy(PROPERTIES)
        instance.authenticate.return_value = None
        instance.send_commands.return_value = None
        instance.close.return_value = None

        flow_cls.return_value = instance
        yield instance


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client,
    enable_custom_integrations,
) -> MockConfigEntry:
    """Set up the integration with a mocked Tuya client."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
