"""Support for Savant Audio Switches (SSA-3220)."""
import asyncio
import datetime
import logging

from homeassistant import config_entries, core
import homeassistant.helpers.config_validation as cv

from .const import CONF_SOURCES, CONF_ZONES, DOMAIN

CONFIG_SCHEMA = cv.platform_only_config_schema

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    _LOGGER.info(f'async_setup_entry: {DOMAIN}')
    hass.data.setdefault(DOMAIN, {})

    config = dict(entry.data)
    # Update our config to include new repos and remove those that have been removed.
    if entry.options:
        config.update(entry.options)

    hass.data[DOMAIN][entry.entry_id] = config
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Forward the setup to the media_player platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "media_player")
    )
    return True

async def async_unload_entry(
    hass: core.HomeAssistant, 
    entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f'async_unload_entry: {DOMAIN}')
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, "media_player")]
        )
    )

    # Remove config entry from domain.
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the GitHub Custom component from yaml configuration."""
    _LOGGER.info(f'async_setup: {DOMAIN}')
    hass.data.setdefault(DOMAIN, {})
    return True
