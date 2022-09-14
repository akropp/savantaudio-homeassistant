"""Support for Savant Audio Switches (SSA-3220)."""
from __future__ import annotations

import logging

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.const import DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import savantaudio.client as sa

from .const import (
    DEFAULT_DEVICE,
    DEFAULT_INPUTS,
    DEFAULT_NAME,
    DEFAULT_OUTPUTS,
    DEFAULT_PORT,
    DOMAIN,
    KNOWN_OUTPUTS,
)

_LOGGER = logging.getLogger(__name__)


CONF_INPUTS = "inputs"
CONF_OUTPUTS = "outputs"

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

SCAN_INTERVAL = timedelta(seconds=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE, default=DEFAULT_DEVICE): cv.string,
        vol.Optional(CONF_INPUTS, default=DEFAULT_INPUTS): {cv.string: cv.string},
        vol.Optional(CONF_OUTPUTS, default=DEFAULT_OUTPUTS): {cv.string: cv.string},
    }
)

TIMEOUT_MESSAGE = "Timeout waiting for response."

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    known_outputs = hass.data[DOMAIN].setdefault(KNOWN_OUTPUTS, [])

    devices: list[SavantAudioOutput] = []

    if CONF_HOST in config and (host := config[CONF_HOST]) not in KNOWN_HOSTS:
        try:
            port = config[CONF_PORT]
            switch = sa.Switch(host=host, port=port, model=config[CONF_DEVICE])
            await switch.refresh()
            outputNames = conf.get(CONF_OUTPUTS)
            for output in switch.outputs:
                _name = f'Output{output.number}'
                outputdevice = SavantAudioOutput(
                        switch,
                        config.get(CONF_INPUTS),
                        output,
                        outputNames[_name] if _name in outputNames else None,
                        name=config.get(CONF_NAME),
                    )
                known_outputs.append(outputdevice)
                devices.append(outputdevice)
            KNOWN_HOSTS.append(host)
        except OSError:
            _LOGGER.error("Unable to connect to Savant Audio Switch at %s:%d", host, port)
    async_add_entities(devices, True)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the SAVANTAUDIO platform."""
    known_outputs = hass.data[DOMAIN].setdefault(KNOWN_OUTPUTS, [])

    devices: list[SavantAudioOutput] = []

    if CONF_HOST in config and (host := config[CONF_HOST]) not in KNOWN_HOSTS:
        try:
            port = config[CONF_PORT]
            switch = sa.Switch(host=host, port=port)
            await switch.refresh()
            outputNames = conf.get(CONF_OUTPUTS)
            for output in switch.outputs:
                _name = f'Output{output.number}'
                outputdevice = SavantAudioOutput(
                        switch,
                        config.get(CONF_INPUTS),
                        output,
                        outputNames[_name] if _name in outputNames else None,
                        name=config.get(CONF_NAME),
                    )
                known_outputs.append(outputdevice)
                devices.append(outputdevice)
            KNOWN_HOSTS.append(host)
        except OSError:
            _LOGGER.error("Unable to connect to Savant Audio Switch at %s:%d", host, port)
    async_add_entities(devices, True)

def _parse_source(source: str):
    if source.startswith('Input'):
        return int(source[5:])
    raise ValueError(f'Unknown Source {source}')

def _parse_output(output: str):
    if source.startswith('Output'):
        return int(output[6:])
    raise ValueError(f'Unknown Output {output}')

class SavantAudioOutput(MediaPlayerEntity):
    """Representation of an SAVANTAUDIO device."""

    _attr_supported_features = SUPPORT_SAVANTAUDIO

    def __init__(
        self,
        switch,
        inputs,
        output,
        outputName,
        switchName
    ):
        """Initialize the SAVANTAUDIO Receiver."""
        self._switch = switch
        self._output = output

        self._unique_id = (
            f"{switch.host}_{switch.port}_{output.number}"
        )
        if outputName:
            self._name = outputName
        else:
            self._name = self._unique_id

        self._current_source = None
        self._input_list = list(inputs.values())
        self._source_mapping = inputs
        self._reverse_mapping = {value: key for key, value in inputs.items()}
        self._attributes = {}

    async def async_update(self):
        """Get the latest state from the device."""
        self._output.refresh()
        self._switch.refresh_link(self._output.number)

        current_source_raw = self._switch.get_link(self._output.number)
        if current_source_raw is not None:
            self._pwstate = STATE_ON
        else:
            self._pwstate = STATE_OFF
            self._attributes.pop(ATTR_PASSTHRU, None)
            self._attributes.pop(ATTR_STEREO, None)
            self._attributes.pop(ATTR_DELAY_LEFT, None)
            self._attributes.pop(ATTR_DELAY_RIGHT, None)
            return

        volume_raw = self._output.volume
        self._mute = self._output.mute

        if not (volume_raw and mute_raw and current_source_raw):
            return

        source = f'Input{current_source_raw}'
        if source in self._source_mapping:
            self._current_source = self._source_mapping[source]

        # savant volume is between -38dB and 0dB
        self._volume = (volume_raw + 38.0) / 38.0

        self._attributes[ATTR_PASSTHRU] = self._output.passthru
        self._attributes[ATTR_STEREO] = self._output.stereo
        self._attributes[ATTR_DELAY_LEFT] = self._output.delay[0]
        self._attributes[ATTR_DELAY_RIGHT] = self._output.delay[1]

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

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
        return self._muted

    @property
    def source(self):
        """Return the current input source of the device."""
        return self._current_source

    @property
    def source_list(self):
        """List of available input sources."""
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

    async def async_set_volume_level(self, volume):
        """
        Set volume level, input is range 0..1.

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
        if self._current_source and self._current_source in self._source_list:
            source = self._reverse_mapping[source]
            await self._switch.link(self._output.number, _parse_source(source))

    async def async_select_source(self, source):
        """Set the input source."""
        if source in self._source_list:
            source = self._reverse_mapping[source]
        await self._switch.link(self._output.number, _parse_source(source))

    async def async_select_sound_mode(self, mode: str):
        """Set the sound mode."""
        stereo = False
        passthru = False
        for m in mode.split(','):
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
        output_ids = {
            p.entity_id: p for p in self.hass.data[DOMAIN][KNOWN_OUTPUTS]
        }

        for other_player in group_members:
            if other := output_ids.get(other_player) and other._switch.host == self._switch.host:
                await other.async_select_source(self._current_source)
            else:
                _LOGGER.info(
                    "Could not find player_id for %s. Not syncing", other_player
                )

    async def async_unjoin_player(self) -> None:
        """Remove this player from any group."""
        await self._switch.unlink(self._output.number)
