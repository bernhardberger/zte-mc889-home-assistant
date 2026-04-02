# ZTE MC889 5G Modem — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)

Home Assistant custom integration for the **ZTE MC889** 5G outdoor CPE. Polls the modem's local API for signal quality, throughput, device status, and thermal data — no cloud, no scraping, fully local.

## Features

- **20 sensors** across signal, traffic, device, and thermal categories
- **Config flow** — set up entirely from the HA UI
- **Auto-reconnect** — sessions expire quickly; the client handles re-login transparently
- **Signal quality attributes** — RSRP, SINR, RSRQ sensors include a `quality` attribute (excellent/good/fair/poor)
- **HACS compatible** — install as a custom repository

### Sensors

| Sensor | Unit | Default |
|---|---|---|
| Signal bars | — | Enabled |
| Network type | — | Enabled |
| 5G RSRP | dBm | Enabled |
| 5G SINR | dB | Enabled |
| Download speed | Mbit/s | Enabled |
| Upload speed | Mbit/s | Enabled |
| Monthly download | GB | Enabled |
| Monthly upload | GB | Enabled |
| Provider | — | Disabled |
| 5G RSRQ | dB | Disabled |
| 5G band | — | Disabled |
| Cell ID | — | Disabled |
| LTE RSRP | dBm | Disabled |
| LTE SNR | dB | Disabled |
| WAN IP | — | Enabled |
| Firmware | — | Disabled |
| MTU | — | Disabled |
| WAN mode | — | Disabled |
| Connection status | — | Enabled |
| 5G temperature | °C | Disabled |

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the **three dots** menu (top right) → **Custom repositories**
3. Add `https://github.com/bernhardberger/zte-mc889-home-assistant` as type **Integration**
4. Search for "ZTE MC889" and install
5. Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration → ZTE MC889 5G Modem**

### Manual

1. Copy `custom_components/zte_mc889/` into your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration from the UI

## Configuration

The integration is configured entirely through the Home Assistant UI:

- **Host** — Modem IP address (default: `192.168.254.1`)
- **Password** — Admin password for the modem web interface

> **Warning**: The ZTE MC889 locks out after **5 consecutive failed login attempts**. A power cycle is required to reset the lockout. Double-check your password before submitting.

## How it works

The integration uses the modem's local HTTP API (the same one the web interface uses). Authentication is SHA256-based with session tokens. The client:

1. Fetches a nonce (LD) from the modem
2. Computes `SHA256(SHA256(password) + LD)` and POSTs a login request
3. Receives a session cookie (`stok`) and computes an AD token from a second nonce (RD)
4. Polls 20 fields every 30 seconds using the session

Sessions expire after ~60 seconds of inactivity. The client detects this and re-authenticates automatically.

## Compatibility

- **Tested on**: ZTE MC889 firmware `BD_ATMC889V1.0.0B19`
- **Mode**: LTE_BRIDGE (bridge mode)
- **Connection**: HTTPS to modem management IP (`192.168.254.1`)
- **Home Assistant**: 2026.4+

## Known limitations

- `pm_sensor_mdm` (modem temperature) is not available on firmware B19 — querying it crashes the entire API response. The integration excludes it and only exposes `pm_modem_5g` (5G temperature).
- The modem only supports one active web session at a time. If you're logged into the web UI, the integration may get "duplicate session" errors until the web session expires.
- LTE signal sensors will be empty when the modem is connected via 5G SA (standalone).

## Related

- [zte-mc889-api](https://github.com/bernhardberger/zte-mc889-api) — Standalone Python library and CLI tool for the ZTE MC889

## License

MIT
