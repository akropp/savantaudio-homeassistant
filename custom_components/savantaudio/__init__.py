"""Support for Savant Audio Switches (SSA-3220)."""
import asyncio
import datetime
import logging

from homeassistant import config_entries, core
import homeassistant.helpers.config_validation as cv

from .const import CONF_SOURCES, CONF_ZONES, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    _LOGGER.info(f'async_setup_entry: {DOMAIN}')
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    config = dict(entry.data)
    # Update our config to include new repos and remove those that have been removed.
    if entry.options:
        config.update(entry.options)

    hass.data[DOMAIN][entry.entry_id] = config
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Forward the setup to the media_player platform.
    for platform in PLATFORMS:
        hass.async_add_job(
            hass.config_entries.async_forward_entry_setup(entry, platform)
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
            *[hass.config_entries.async_forward_entry_unload(entry, platform)
              for platform in PLATFORMS]
        )
    )

    # Remove config entry from domain.
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry) -> None:
    """Update listener."""
    _LOGGER.info(f'update_listener: {DOMAIN}')
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Savant component from yaml configuration."""
    _LOGGER.info(f'async_setup: {DOMAIN}')
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
