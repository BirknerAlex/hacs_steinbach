"""Test Steinbach Pool integration setup and unload."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.steinbach.coordinator import SteinbachDataUpdateCoordinator


async def test_setup_entry(hass: HomeAssistant, setup_integration):
    """Setting up a valid entry should leave the integration LOADED."""
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, SteinbachDataUpdateCoordinator)


async def test_unload_entry(hass: HomeAssistant, setup_integration):
    """Unloading should return the entry to NOT_LOADED."""
    entry = setup_integration

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
