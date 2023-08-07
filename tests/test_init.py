"""Initialization tests for savantaudio."""


from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

# from custom_components.savantaudio import async_setup_entry, async_unload_entry
from custom_components.savantaudio.const import DOMAIN

from .const import MOCK_CONFIG


# We can pass fixtures as defined in conftest.py to tell pytest to use the fixture
# for a given test. We can also leverage fixtures and mocks that are available in
# Home Assistant using the pytest_homeassistant_custom_component plugin.
# Assertions allow you to verify that the return value of whatever is on the left
# side of the assertion matches with the right side.
async def test_setup_unload_and_reload_entry(hass, bypass_get_data):
    """Test entry setup and unload."""
    m_instance = AsyncMock()
    m_instance.getitem = AsyncMock()

    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # # Unload the entry and verify that the data has been removed
    # assert await async_unload_entry(hass, config_entry)
    # assert config_entry.entry_id not in hass.data[DOMAIN]


# async def test_setup_entry_exception(hass, error_on_get_data):
#     """Test ConfigEntryNotReady when API raises an exception during entry setup."""
#     config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

#     # In this case we are testing the condition where async_setup_entry raises
#     # ConfigEntryNotReady using the `error_on_get_data` fixture which simulates
#     # an error.
#     with pytest.raises(ServiceNotFound):
#         assert await async_setup_entry(hass, config_entry)


# async def test_setup_entry_missing_data(hass, bypass_get_data):
#     """Test ConfigEntryNotReady when API raises an exception during entry setup."""
#     config_entry = MockConfigEntry(domain=DOMAIN, data=BAD_CONFIG, entry_id="test")

#     # In this case we are testing the condition where async_setup_entry raises
#     # ConfigEntryNotReady using the `error_on_get_data` fixture which simulates
#     # an error.
#     with pytest.raises(RequiredParameterMissing):
#         assert await async_setup_entry(hass, config_entry)
