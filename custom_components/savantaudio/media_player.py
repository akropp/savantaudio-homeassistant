"""Support for Savant Audio Switches (SSA-3220)."""
from __future__ import annotations

import datetime
from http.client import SWITCHING_PROTOCOLS
import logging

# from homeassistant.components.media_player.const import DOMAIN
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ENABLED,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryError, HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify
import savantaudio.client as sa
from typing_extensions import Required
import voluptuous as vol

from .const import (
    CONF_NUMBER,
    CONF_SOURCES,
    CONF_ZONES,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SOURCE,
    DOMAIN,
    KNOWN_ZONES,
)

_LOGGER = logging.getLogger(__name__)


ATTR_PASSTHRU = "passthru"
ATTR_STEREO = "stereo"
ATTR_DELAY_LEFT = "delay_left"
ATTR_DELAY_RIGHT = "delay_right"


SUPPORT_SAVANTAUDIO = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    | MediaPlayerEntityFeature.GROUPING
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_STEP
)

KNOWN_HOSTS: list[str] = []

SOUND_MODE_LIST = ['stereo', 'mono', 'stereo,passthru', 'mono,passthru']

DEFAULT_SOURCES = { n: {"name": f'Source {n}'} for n in range(1,32) }
DEFAULT_ZONES = { n: {"name": f'Zone {n}', DEFAULT_SOURCE: None} for n in range(1,20) }

SOURCE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=32))
SOURCE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default="Unknown Source"): cv.string,
    vol.Required(CONF_ENABLED, default=True): bool,
})

ZONE_IDS = vol.All( vol.Coerce(int), vol.Range(min=1, max=20) )
ZONE_SCHEMA = vol.Schema({
    vol.Required(CONF_NUMBER): ZONE_IDS,
    vol.Required(CONF_NAME, default="Audio Zone"): cv.string,
    vol.Optional(DEFAULT_SOURCE): cv.positive_int,
    vol.Required(CONF_ENABLED, default=True): bool,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_ZONES): vol.Schema({cv.string: ZONE_SCHEMA}),
        vol.Required(CONF_SOURCES): vol.Schema({SOURCE_IDS: SOURCE_SCHEMA}),
    }
)

SOURCE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=32))
SOURCE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default="Unknown Source"): cv.string,
    vol.Required(CONF_ENABLED, default=True): bool,
})

ZONE_IDS = vol.All( vol.Coerce(int), vol.Range(min=1, max=20) )
ZONE_SCHEMA = vol.Schema({
    vol.Required(CONF_NUMBER): ZONE_IDS,
    vol.Required(CONF_NAME, default="Audio Zone"): cv.string,
    vol.Optional(DEFAULT_SOURCE): cv.positive_int,
    vol.Required(CONF_ENABLED, default=True): bool,
})


SCAN_INTERVAL = datetime.timedelta(minutes=1)


TIMEOUT_MESSAGE = "Timeout waiting for response."

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.info(f'media_player.async_setup_entry: {DOMAIN}')
    config = hass.data[DOMAIN][config_entry.entry_id]
    known_zones = hass.data[DOMAIN].setdefault(KNOWN_ZONES, [])

    devices: list[SavantAudioZone] = []

    try:
        host = config[CONF_HOST]
        port = config.get(CONF_PORT, DEFAULT_PORT)
        if host is None or port is None:
            raise RequiredParameterMissing
            
        switch = sa.Switch(host=host, port=port)
        try:
            await switch.connect()
        except:
            raise HomeAssistantError

        # add device for switch
        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)

        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, switch.attributes['sn'])},
            manufacturer="Savant",
            name=config[CONF_NAME],
            model=str(switch.model),
            sw_version=switch.attributes['fwrev'],
            hw_version=switch.attributes['rev'],
        )

        sn = switch.attributes['sn']
        device_ids = []
        entity_ids = []
        if CONF_SOURCES in config and CONF_ZONES in config:
            sources = {
                int(source_id): extra[CONF_NAME] for source_id, extra in config[CONF_SOURCES].items() if extra.get(CONF_ENABLED, True)
            }
            for entity_id, extra in config[CONF_ZONES].items():
                if extra.get(CONF_ENABLED, True):
                    zonedevice = SavantAudioZone(
                            switch,
                            entity_id,
                            sources,
                            switch.output(int(extra[CONF_NUMBER])),
                            extra[CONF_NAME],
                            switch_name=config.get(CONF_NAME),
                            default_source=extra.get(DEFAULT_SOURCE, None),
                        )
                    known_zones.append(zonedevice)
                    devices.append(zonedevice)
                    device_ids.append(zonedevice.unique_id)
                    entity_ids.append(zonedevice.entity_id)
        if sn not in KNOWN_HOSTS:
            KNOWN_HOSTS.append(sn)
        unknown_entities = [zone for zone in known_zones if zone.switch.attributes['sn'] == sn and zone.entity_id not in entity_ids]
        for zone in unknown_entities:
            entity_registry.async_remove(zone.entity_id)
            _LOGGER.debug(f'Removed Zone Entity id={zone.entity_id}, name={zone.name}')
        unknown_zones = [zone for zone in known_zones if zone.switch.attributes['sn'] == sn and zone.unique_id not in device_ids]
        for zone in unknown_zones:
            known_zones.remove(zone)
            device = device_registry.async_get_device(zone.device_info["identifiers"])
            if device is not None:
                device_registry.async_remove_device(device.id)
            _LOGGER.debug(f'Removed Zone Device id={device.id}, name={zone.name}')

    except OSError:
        _LOGGER.error("Unable to connect to Savant Audio Switch at %s:%d", host, port)
    async_add_entities(devices, True)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f'media_player.async_unload_entry: {DOMAIN}')
    known_zones = hass.data[DOMAIN].setdefault(KNOWN_ZONES, [])
    to_remove = [ zone for zone in known_zones if zone.switch.attributes['sn'] == entry.unique_id ]
    for zone in to_remove:
        known_zones.remove(zone)

    return True

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the SAVANTAUDIO platform."""
    _LOGGER.info(f'media_player.async_setup_platform: {DOMAIN}')
    known_zones = hass.data[DOMAIN].setdefault(KNOWN_ZONES, [])

    devices: list[SavantAudioZone] = []

    try:
        host = config[CONF_HOST]
        port = config.get(CONF_PORT, DEFAULT_PORT)
        if host is None or port is None:
            raise ConfigEntryError(f'missing host or port')

        switch = sa.Switch(host=host, port=port)
        try:
            await switch.connect()
        except:
            raise HomeAssistantError

        if switch.attributes['sn'] in KNOWN_HOSTS:
            _LOGGER.info(f"Already added switch {switch.attributes['sn']} at {host}:{port}")
            return

        # add device for switch
        device_registry = dr.async_get(hass)

        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, switch.attributes['sn'])},
            manufacturer="Savant",
            name=config[CONF_NAME],
            model=str(switch.model),
            sw_version=switch.attributes['fwrev'],
            hw_version=switch.attributes['rev'],
        )

        if CONF_SOURCES in config:
            sources = { int(source_id): extra[CONF_NAME] for source_id, extra in config[CONF_SOURCES].items() }
        else:
            sources = { n: f'Input {n}' for n in range(1,33) }
        for entity_id, extra in config[CONF_ZONES].items():
            if extra.get(CONF_ENABLED, True):
                zonedevice = SavantAudioZone(
                        switch,
                        entity_id,
                        sources,
                        switch.output(int(extra[CONF_NUMBER])),
                        extra[CONF_NAME],
                        switch_name=config.get(CONF_NAME),
                        default_source=extra.get(DEFAULT_SOURCE, None),
                    )
                known_zones.append(zonedevice)
                devices.append(zonedevice)
        KNOWN_HOSTS.append(switch.attributes['sn'])
    except OSError:
        _LOGGER.error("Unable to connect to Savant Audio Switch at %s:%d", host, port)
    except:
        raise
    _LOGGER.info(f'media_player.async_setup_entry: {DOMAIN}: calling async_add_entities')
    async_add_entities(devices, True)


class SavantAudioZone(MediaPlayerEntity):
    """Representation of an SAVANTAUDIO device."""

    _attr_supported_features = SUPPORT_SAVANTAUDIO

    def __init__(
        self,
        switch,
        entity_id,
        sources,
        output,
        zone_name: str = None,
        switch_name: str = None,
        default_source: int = None
    ):
        """Initialize the SAVANTAUDIO Receiver."""
        self._switch = switch
        self._output = output
        self.entity_id = f'media_player.{entity_id}'
        async def _output_updated(event: str, obj):
            if event == 'output-updated' and obj.number == self._output.number:
                await self._sync_output()
            elif event == 'link-updated' and obj[1] == self._output.number:
                await self._sync_link()

        self._switch.add_callback(_output_updated)
        self._switch_name = switch_name if switch_name is not None else f'{switch.model}'
        self._default_source = default_source

        self._attr_unique_id = (
            f"{switch.attributes['sn']}_{output.number}"
        )

        if zone_name:
            self._attr_name = zone_name
        else:
            self._attr_name = f'{self._switch_name} Zone {output.number}'

        if sources is None:
            sources = DEFAULT_SOURCES
        self.set_sources(sources)
        self._current_source = None
        self._attributes = {}
        self._volume = 0
        self._mute = False
        self._pwstate = STATE_OFF

    def set_sources(self, sources):
        self._source_list = list(sources.values())
        self._source_mapping = sources
        self._reverse_mapping = {value: key for key, value in sources.items()}

    def set_name(self, name: str):
        self._attr_name = name

    async def _sync_link(self):
        self._current_source = await self._switch.get_link(self._output.number)
        if self._current_source is not None:
            self._pwstate = STATE_ON
        else:
            self._pwstate = STATE_OFF
            # self._attributes.pop(ATTR_PASSTHRU, None)
            # self._attributes.pop(ATTR_STEREO, None)
            # self._attributes.pop(ATTR_DELAY_LEFT, None)
            # self._attributes.pop(ATTR_DELAY_RIGHT, None)

    async def _sync_output(self):
        volume_raw = self._output.volume
        self._mute = self._output.mute

        # savant volume is between -38dB and 0dB
        self._volume = (volume_raw + 38.0) / 38.0

        self._attributes[ATTR_PASSTHRU] = self._output.passthru
        self._attributes[ATTR_STEREO] = self._output.stereo
        self._attributes[ATTR_DELAY_LEFT] = self._output.delay[0]
        self._attributes[ATTR_DELAY_RIGHT] = self._output.delay[1]

    async def async_update(self):
        """Get the latest state from the device."""
        await self._output.refresh()
        await self._switch.refresh_link(self._output.number)
        await self._sync_output()
        await self._sync_link()

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            "name": self.name,
            "manufacturer": "Savant",
            "model": str(self._switch.model),
            "sw_version": self._switch.attributes['fwrev'],
            "hw_version": self._switch.attributes['rev'],
            "via_device": (DOMAIN, self._switch.attributes['sn']),
        }

    @property
    def switch(self):
        return self._switch

    @property
    def number(self):
        return self._output.number

    @property
    def state(self):
        """Return the state of the device."""
        return self._pwstate

    @property
    def volume_level(self):
        """Return the volume level of the media player (0..1)."""
        return self._volume

    @property
    def is_volume_muted(self):
        """Return boolean indicating mute status."""
        return self._mute

    @property
    def source(self):
        """Return the current source source of the device."""
        if self._current_source is not None:
            return self._source_mapping[self._current_source]
        else:
            return None

    @property
    def source_list(self):
        """List of available source sources."""
        return self._source_list

    @property
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        return self._attributes

    @property
    def sound_mode(self):
        modes = []
        if self._output.stereo:
            modes.append('stereo')
        else:
            modes.append('mono')
        if self._output.passthru: modes.append('passthru')
        return ','.join(modes)

    @property
    def sound_mode_list(self):
        return SOUND_MODE_LIST

    @property
    def device_class(self):
        return MediaPlayerDeviceClass.RECEIVER

    async def async_turn_off(self):
        """Turn the media player off."""
        await self._switch.unlink(self._output.number)
        self._pwstate = STATE_OFF

    async def async_set_volume_level(self, volume):
        """
        Set volume level, source is range 0..1.

        For the switch, the actual volume level is -38..0
        """
        await self._output.set_volume(int(volume * 38.0 - 38.0))

    async def async_volume_up(self):
        """Increase volume by 1 step."""
        if self._output.volume < 0:
            await self._output.set_volume(self._output.volume + 1)

    async def async_volume_down(self):
        """Decrease volume by 1 step."""
        if self._output.volume > 38:
            await self._output.set_volume(self._output.volume - 1)

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        await self._output.set_mute(mute)

    async def async_turn_on(self):
        """Turn the media player on."""
        if self._pwstate == STATE_OFF:
            if self._current_source is not None:
                await self._switch.link(self._output.number, self._current_source)
            elif self._default_source is not None:
                await self._switch.link(self._output.number, self._default_source)
                self._current_source = self._default_source
            self._pwstate = STATE_ON

    async def async_select_source(self, source):
        """Set the source source."""
        if source is not None:
            if source in self._source_list:
                source = self._reverse_mapping[source]
            self._current_source = source
            if self._pwstate == STATE_ON:
                await self._switch.link(self._output.number, source)
        else:
            await self._switch.unlink(self._output.number)
            self._current_source = None

    async def async_select_sound_mode(self, sound_mode: str):
        """Set the sound mode."""
        stereo = False
        passthru = False
        for m in sound_mode.split(','):
            if m == 'stereo':
                stereo = True
            elif m == 'mono':
                stereo = False
            elif m == 'passthru':
                passthru = True
        await self._output.set_stereo(stereo)
        await self._output.set_passthru(passthru)

    async def async_join_players(self, group_members: list[str]) -> None:
        """Join `group_members` as a player group with the current player."""
        zone_ids = {
            p.entity_id: p for p in self.hass.data[DOMAIN][KNOWN_ZONES]
        }

        for other_player in group_members:
            if other := zone_ids.get(other_player) and other._switch.host == self._switch.host:
                await other.async_select_source(self.source)
            else:
                _LOGGER.info(
                    "Could not find player_id for %s. Not syncing", other_player
                )

    async def async_unjoin_player(self) -> None:
        """Remove this player from any group."""
        await self._switch.unlink(self._output.number)
        self._current_source = None

    @property
    def icon(self):
        if self.state == STATE_OFF or self.is_volume_muted:
            return 'mdi:speaker-off'
        else:
            return 'mdi:speaker'
