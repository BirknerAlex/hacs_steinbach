"""Tests for the Steinbach Pool config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.steinbach.api.error import AuthenticationError
from custom_components.steinbach.const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

USER_INPUT = {
    CONF_ACCESS_ID: "test_access_id",
    CONF_ACCESS_SECRET: "secret",
    CONF_REGION: "eu",
}


async def test_user_flow_success(hass: HomeAssistant, enable_custom_integrations):
    """A valid project should create an entry keyed by the Access ID."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.steinbach.config_flow.TuyaOpenAPIClient"
    ) as client_cls:
        client = client_cls.return_value
        client.get_devices.return_value = []

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Steinbach Pool"
    assert result["data"] == USER_INPUT
    assert result["options"] == {CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL}
    assert result["result"].unique_id == USER_INPUT[CONF_ACCESS_ID]


async def test_user_flow_invalid_auth(
    hass: HomeAssistant, enable_custom_integrations
):
    """A signing/credential failure should surface as invalid_auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.steinbach.config_flow.TuyaOpenAPIClient"
    ) as client_cls:
        client_cls.return_value.authenticate.side_effect = AuthenticationError("nope")

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, enable_custom_integrations, mock_config_entry
):
    """A second entry for the same Access ID should abort."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, setup_integration):
    """The options flow should persist a new scan interval."""
    result = await hass.config_entries.options.async_init(
        setup_integration.entry_id
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 120}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SCAN_INTERVAL: 120}
