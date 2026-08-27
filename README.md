# Control Savant Audio Switches from Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

Home Assistant custom component to control Savant Audio switches (SSA-3220, SSA-3220D) via TCP/IP.  Based on the [savantaudio-client](https://github.com/akropp/savantaudio-client) package.

**Current features**

- select which inputs/outputs should be available in Home Assistant
- give meaningful names to inputs/outputs
- creates one device/entity per enabled output, which appears as a media_player receiver entity 
- outputs can be joined/unjoined to play from a single input

## Tested Devices

Tested against SSA-3220D.  

## Installation

[HACS](https://hacs.xyz/) > Integrations > Plus > **SavantAudio**

Or manually copy `savantaudio` folder from [latest release](https://github.com/akropp/savantaudio-homeassistant/releases/latest) to `custom_components` folder in your config folder.

## Configuration

Configuration > [Integrations](https://my.home-assistant.io/redirect/integrations/) > Add Integration > [SavantAudio](https://my.home-assistant.io/redirect/config_flow_start/?domain=savantaudio)

*If the integration is not in the list, you need to clear the browser cache.*

You can setup multiple integrations with different hostnames/ip addresses.

## Configuration UI

Configuration > [Integrations](https://my.home-assistant.io/redirect/integrations/) > **SavantAudio** > Configure

**This is how sources and zones are configured.** The Configure wizard walks
through selecting which inputs are in use, naming them, selecting which outputs
are in use, naming them, and choosing a default source per zone. Entities are
created for enabled outputs only, so a freshly added integration shows a device
with no entities until this flow is completed.

## Configuration YAML

Adding a `savantaudio:` block to `configuration.yaml` has **no effect**. The
integration defines no `CONFIG_SCHEMA`, so such a block is parsed and discarded;
all settings come from the config entry created by the flows above.

The schema below describes the shape of that stored configuration, for reference
when inspecting `.storage/core.config_entries` or when using the legacy
`media_player` platform setup.

```yaml
savantaudio:
  host: <hostname>    # hostname/ip of switch
  port: 8085          # default port
  name: Savant        # name of switch device; will also be part of zone entity names
  sources:
    5:
        name: Sonos
        enabled: True
    6:
        name: Record Player
        enabled: True
  zones:
    11:
        name: Living Room # Name of zone -- will be included in entity name
        enabled: True     # Enable this zone -- will create a device
        default: 5        # Default Source when this zone is turned on
    12:
        name: Family Room
        enabled: True
        default: 6
```

## Useful Links

- https://github.com/akropp/savantaudio-client
- [Savant Audio Switch API](https://sav-documentation.s3.amazonaws.com/Product%20Application%20Notes/API_Application%20Note.pdf)
