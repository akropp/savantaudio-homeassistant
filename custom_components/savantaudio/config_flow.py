from copy import deepcopy
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries, core
from homeassistant.components import dhcp
from homeassistant.const import CONF_ENABLED, CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)
import savantaudio.client as sa
import voluptuous as vol

from custom_components.savantaudio.media_player import (
    CONF_SOURCES,
    CONF_ZONES,
    DEFAULT_ZONES,
    SOURCE_IDS,
    SOURCE_SCHEMA,
    ZONE_IDS,
    ZONE_SCHEMA,
)

from .const import (
    CONF_NUMBER,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SOURCE,
    DOMAIN,
    SOURCE_RANGE,
    ZONE_RANGE,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


class SavantAudioCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Savant Audio Custom config flow."""

    data: Optional[Dict[str, Any]]

    def __init__(self):
        self.discovered_ip = None
        self.discovered_name = None

    async def _async_validate_or_error(self, host, port: int = DEFAULT_PORT):
        _LOGGER.debug(f'_async_validate_or_error: {DOMAIN}, host={host}, port={port}')
        # self._async_abort_entries_match({CONF_HOST: host})

        info = {}
        try:
            switch = sa.Switch(host, port)
            await switch.connect()

            info = {CONF_HOST: host, CONF_PORT: port, "unique_id": switch.attributes['sn']}
        except ValueError:
            return None, "cannot_connect"

        return info, None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        _LOGGER.info(f'async_step_user: {DOMAIN}')
        errors: Dict[str, str] = {}
        if user_input is not None:
            info, error = await self._async_validate_or_error(user_input[CONF_HOST], user_input[CONF_PORT])
            if error:
                return self.async_abort(reason=error)

            _LOGGER.debug(f'async_step_user: {DOMAIN} got unique id {info["unique_id"]}')
            await self.async_set_unique_id(info["unique_id"], raise_on_progress=False)
            self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]})

            self.data = user_input
            # Return the form of the next step.
            _LOGGER.debug(f'async_step_user: {DOMAIN} creating entry data={self.data}')
            return self.async_create_entry(title="Savant Audio", data=self.data)

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> FlowResult:
        """Handle DHCP discovery."""
        self.discovered_ip = discovery_info.ip
        self.discovered_name = discovery_info.hostname
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self):
        """Confirm dhcp discovery."""
        errors: Dict[str, str] = {}
        # If we already have the host configured do
        # not open connections to it if we can avoid it.
        self.context[CONF_HOST] = self.discovered_ip
        for progress in self._async_in_progress():
            if progress.get("context", {}).get(CONF_HOST) == self.discovered_ip:
                return self.async_abort(reason="already_in_progress")

        self._async_abort_entries_match({CONF_HOST: self.discovered_ip})

        info, error = await self._async_validate_or_error(self.discovered_ip)
        if error:
            return self.async_abort(reason=error)

        await self.async_set_unique_id(info["unique_id"], raise_on_progress=False)
        self._abort_if_unique_id_configured({CONF_HOST: self.discovered_ip})

        return self.async_create_entry(title="Savant Audio", data=info)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._updated_sources = {}
        self._updated_zones = {}

    async def async_step_init(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the source names."""
        config = dict(self.config_entry.data)
        if self.config_entry.options:
            config.update(self.config_entry.options)
        self._updated_sources = deepcopy(config[CONF_SOURCES]) if CONF_SOURCES in config else {}
        for source_id in SOURCE_RANGE:
            if str(source_id) not in self._updated_sources:
                self._updated_sources[str(source_id)] = {CONF_NAME: f'Input {source_id}', CONF_ENABLED: False}
        self._updated_zones = {}
        if CONF_ZONES in config:
            for entity_id, zone_entry in config[CONF_ZONES].items():
                entry = deepcopy(zone_entry)
                entry["__entity_id"] = entity_id
                self._updated_zones[str(zone_entry[CONF_NUMBER])] = entry
        for zone_id in ZONE_RANGE:
            if str(zone_id) not in self._updated_zones:
                self._updated_zones[str(zone_id)] = {CONF_NUMBER: zone_id, CONF_NAME: f'Zone {zone_id}', CONF_ENABLED: False, DEFAULT_SOURCE: None}
        return await self.async_step_sources()

    async def async_step_sources(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            sources = user_input["enabled_sources"]
            for source_id in SOURCE_RANGE:
                self._updated_sources[str(source_id)][CONF_ENABLED] = str(source_id) in sources

            if not errors:
                # Value of data will be set on the options property of our config_entry
                # instance.
                return await self.async_step_source_names()

        enabled_sources = [str(source_id) for source_id in SOURCE_RANGE if str(source_id) in self._updated_sources and self._updated_sources[str(source_id)][CONF_ENABLED]]
        all_sources = {str(source_id): f'Source {source_id} ({self._updated_sources[str(source_id)][CONF_NAME]})' for source_id in SOURCE_RANGE}
        # sources_list = {}
        # for source_id in SOURCE_RANGE:
            # entry = self._updated_sources.get(source_id, None)
            # sources_list[vol.Required(f'enable_input_{source_id}', default=entry[CONF_ENABLED] if entry is not None else True)] = bool

        return self.async_show_form(
            step_id="sources", data_schema=vol.Schema({vol.Optional('enabled_sources', default=enabled_sources): cv.multi_select(all_sources)}), errors=errors
        )

    async def async_step_source_names(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            for source_id in SOURCE_RANGE:
                self._updated_sources[str(source_id)][CONF_NAME] = user_input.get(f'input_{source_id}',f'Input {source_id}')

            if not errors:
                # Value of data will be set on the options property of our config_entry
                # instance.
                return await self.async_step_zones()

        sources_list = {}
        for source_id in SOURCE_RANGE:
            entry = self._updated_sources.get(str(source_id), None)
            if entry[CONF_ENABLED]:
                sources_list[vol.Required(f'input_{source_id}', default=entry[CONF_NAME] if entry is not None else f'Input {source_id}')] = str

        return self.async_show_form(
            step_id="source_names", data_schema=vol.Schema(sources_list), errors=errors
        )


    async def async_step_zones(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            zones = user_input["enabled_zones"]
            for zone_id in ZONE_RANGE:
                self._updated_zones[str(zone_id)][CONF_ENABLED] = str(zone_id) in zones

            # for zone_id in ZONE_RANGE:
            #     self._updated_zones[str(zone_id)][CONF_ENABLED] = user_input.get(f'enable_zone_{zone_id}',True)

            if not errors:
                # Value of data will be set on the options property of our config_entry
                # instance.
                return await self.async_step_zone_names()

        # zones_list = {}
        # for zone_id in ZONE_RANGE:
        #     entry = self._updated_zones.get(zone_id, None)
        #     zones_list[vol.Required(f'enable_zone_{zone_id}', default=entry[CONF_ENABLED] if entry is not None else True)] = bool

        # return self.async_show_form(
        #     step_id="zones", data_schema=vol.Schema(zones_list), errors=errors
        # )

        enabled_zones = [str(zone_id) for zone_id in ZONE_RANGE if str(zone_id) in self._updated_zones and self._updated_zones[str(zone_id)][CONF_ENABLED]]
        all_zones = {str(zone_id): f'Zone {zone_id} ({self._updated_zones[str(zone_id)][CONF_NAME]})' for zone_id in ZONE_RANGE}
        return self.async_show_form(
            step_id="zones", data_schema=vol.Schema({vol.Optional('enabled_zones', default=enabled_zones): cv.multi_select(all_zones)}), errors=errors
        )

    async def async_step_zone_names(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            for zone_id in ZONE_RANGE:
                self._updated_zones[str(zone_id)][CONF_NAME] = user_input.get(f'zone_{zone_id}',f'Zone {zone_id}')

            if not errors:
                # Value of data will be set on the options property of our config_entry
                # instance.
                return await self.async_step_zone_defaults()

        zones_list = {}
        for zone_id in ZONE_RANGE:
            entry = self._updated_zones.get(str(zone_id), None)
            if entry[CONF_ENABLED]:
                zones_list[vol.Required(f'zone_{zone_id}', default=entry[CONF_NAME] if entry is not None else f'Zone {zone_id}')] = str

        return self.async_show_form(
            step_id="zone_names", data_schema=vol.Schema(zones_list), errors=errors
        )

    async def async_step_zone_defaults(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}

        source_names = ["-- None --"] + [s[CONF_NAME] for id, s in self._updated_sources.items() if s[CONF_ENABLED]]
        source_map = {self._updated_sources[str(s)][CONF_NAME]: s for s in SOURCE_RANGE}
        source_map['-- None --'] = None

        if user_input is not None:
            for zone_id in ZONE_RANGE:
                dflt = user_input.get(f'default_zone_{zone_id}','-- None --')
                self._updated_zones[str(zone_id)][DEFAULT_SOURCE] = source_map.get(dflt, None)

            # Grab all configured repos from the entity registry so we can populate the
            # multi-select dropdown that will allow a user to remove a repo.
            entity_registry = er.async_get(self.hass)
            entries = async_entries_for_config_entry(
                entity_registry, self.config_entry.entry_id
            )
            # Default value for our multi-select.
            all_zones = {e.entity_id: e.original_name for e in entries}
            zone_map = {e.entity_id: e for e in entries}

            update_map = {f"media_player.{z['__entity_id']}": zone_id for zone_id, z in self._updated_zones.items() if '__entity_id' in z}

            # Remove any unchecked repos.
            removed_zones = [
                entity_id
                for entity_id in zone_map.keys()
                if entity_id not in update_map or self._updated_zones.get(update_map[entity_id], {CONF_ENABLED: False}).get(CONF_ENABLED, False) is False
            ]
            for entity_id in removed_zones:
                # Unregister from HA
                entity_registry.async_remove(entity_id)
                # Remove from our configured repos.
                zone_id = update_map.get(entity_id, None)
                if zone_id is not None:
                    self._updated_zones.pop(zone_id, None)

            base_name = str(self.config_entry.data[CONF_NAME]).lower().replace(' ','_')
            new_zones = {z.get('__entity_id',f'{base_name}_zone_{zone_id}'): z for zone_id, z in self._updated_zones.items()}
            for zone_id, z in new_zones.items():
                z.pop('__entity_id', None)

            if not errors:
                # Value of data will be set on the options property of our config_entry
                # instance.
                return self.async_create_entry(
                    title="",
                    data={CONF_ZONES: new_zones, CONF_SOURCES: self._updated_sources},
                )

        zones_list = {}
        for zone_id in ZONE_RANGE:
            entry = self._updated_zones.get(str(zone_id), None)
            if entry[CONF_ENABLED]:
                src = entry.get(DEFAULT_SOURCE, 0) if entry is not None else None
                src_conf = self._updated_sources.get(str(src), None)
                src_name = src_conf[CONF_NAME] if src_conf is not None and src_conf[CONF_ENABLED] else "-- None --"
                zones_list[vol.Required(f'default_zone_{zone_id}', default=src_name)] = vol.In(source_names)

        return self.async_show_form(
            step_id="zone_defaults", data_schema=vol.Schema(zones_list), errors=errors
        )
