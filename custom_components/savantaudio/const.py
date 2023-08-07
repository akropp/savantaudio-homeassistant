from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ENABLED,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    STATE_OFF,
    STATE_ON,
)
import homeassistant.helpers.config_validation as cv
import savantaudio.client as sa
import voluptuous as vol

DOMAIN = "savantaudio"
KNOWN_ZONES = "known_zones"
KNOWN_HOSTS = "known_hosts"
DEFAULT_PORT = 8085
DEFAULT_NAME = "Savant"
DEFAULT_SOURCE = "default"
CONF_NUMBER = "number"

SOURCE_RANGE = range(1,33)
ZONE_RANGE = range(1,21)

CONF_SOURCES = "sources"
CONF_ZONES = "zones"

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
