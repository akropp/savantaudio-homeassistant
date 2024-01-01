import savantaudio.client as sa

NAME = "Savant Audio Switch Custom Component"
DOMAIN = "savantaudio"
VERSION = "1.0.1"

ISSUE_URL = "https://github.com/akropp/savantaudio-homeassistant/issues"

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

# platforms
MEDIA_PLAYER = "media_player"
PLATFORMS = [MEDIA_PLAYER]

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
