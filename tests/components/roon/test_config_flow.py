"""Test the roon config flow."""
from homeassistant import config_entries, setup
from homeassistant.components.roon.config_flow import CannotConnect
from homeassistant.components.roon.const import DOMAIN

from tests.async_mock import patch


class roonApiMock:
    """Mock to handle returning tokens for testing the RoonApi."""

    def __init__(self, token):
        """Initialize."""
        self._token = token

    @property
    def token(self):
        """Return the auth token from the api."""
        return self._token

    def stop(self):
        """Close down the api."""
        return


async def test_form_and_auth(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch("homeassistant.components.roon.config_flow.TIMEOUT", 0,), patch(
        "homeassistant.components.roon.const.AUTHENTICATE_TIMEOUT", 0,
    ), patch(
        "homeassistant.components.roon.config_flow.RoonApi",
        return_value=roonApiMock("good_token"),
    ), patch(
        "homeassistant.components.roon.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.roon.async_setup_entry", return_value=True,
    ) as mock_setup_entry:
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "1.1.1.1"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Roon Labs Music Player"
    assert result2["data"] == {"host": "1.1.1.1", "api_key": "good_token"}
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_no_token(hass):
    """Test we handle no token being returned (timeout or not authorized)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch("homeassistant.components.roon.config_flow.TIMEOUT", 0,), patch(
        "homeassistant.components.roon.const.AUTHENTICATE_TIMEOUT", 0,
    ), patch(
        "homeassistant.components.roon.config_flow.RoonApi",
        return_value=roonApiMock(None),
    ):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "1.1.1.1"}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.roon.config_flow.RoonApi", side_effect=CannotConnect,
    ):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "1.1.1.1"}
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}