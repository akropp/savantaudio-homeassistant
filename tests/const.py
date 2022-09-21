"""Constants for savantaudio tests."""
from homeassistant.const import CONF_HOST, CONF_PORT

from custom_components.savantaudio.const import DEFAULT_PORT

# Mock config data to be used across multiple tests
MOCK_CONFIG = {CONF_HOST: "localhost", CONF_PORT: DEFAULT_PORT}
BAD_CONFIG = {CONF_PORT: DEFAULT_PORT}
