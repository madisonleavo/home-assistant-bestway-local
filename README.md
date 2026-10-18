# Bestway Spa Local

Local Home Assistant monitoring and control for a confirmed Bestway AirJet V01
profile. The Home Assistant integration is named **Bestway Spa** and uses the
domain `bestway_spa_local`. No Bestway account, cloud login, MQTT broker, or
control-box modification is required.

**Experimental first release.** One Milan AirJet V01 has demonstrated Wi-Fi
provisioning, LAN discovery, local login and status reads. The new integration's
physical control writes, Home Assistant OS installation, and long-term restart
behavior still need user validation. Automated simulations do not replace those
checks. See [supported devices](docs/supported-devices.md).

## Provenance, AI assistance and credit

This project is **largely vibe-coded with AI assistance**. AI agents generated
much of the code, tests and documentation, investigated a Bestway Smart Hub APK
using REA/JADX/Ghidra, and reviewed implementation changes. A human owner supplied
requirements and ran the initial network tests against their own spa. AI review
is not independent human expert review, and passing tests are not a promise of
hardware compatibility.

The investigation included reading decompiled app/native output; this was **not
a formal clean-room process**. Ghidra was instrumental in confirming the native
Wi-Fi provisioning packet. The APK came from a third-party mirror, with the
resulting authenticity and acquisition-rights limitations recorded rather than
treated as resolved. See the [research provenance and legal considerations](docs/provenance.md)
and [publication audit](docs/publication-audit.md) for the artifact hash, methods,
source relationships, history checks and remaining uncertainties.

This work sits alongside existing community efforts. It does not claim to be
the original Bestway integration, an official Bestway product, or a replacement
for anyone's passion project. Please use whichever project fits your equipment;
the reusable protocol findings and tests here are intended to be helpful.

- [cdpuk/ha-bestway](https://github.com/cdpuk/ha-bestway): existing Home Assistant
  integration, device knowledge and Bestway ecosystem research.
- [fanuelsen/tubctl](https://github.com/fanuelsen/tubctl): a local-control project
  that helped identify the Gizwits LAN route and useful protocol references.
- [Apollon77/node-ph803w](https://github.com/Apollon77/node-ph803w/blob/master/PROTOCOL.md):
  published Gizwits LAN protocol research.
- [Gizwits GAgent](https://github.com/gizwits/Gizwits-GAgent): published protocol
  implementation used to cross-check provisioning behavior.
- [visualapproach/WiFi-remote-for-Bestway-Lay-Z-SPA](https://github.com/visualapproach/WiFi-remote-for-Bestway-Lay-Z-SPA):
  extensive community work on the hardware/serial-control approach.
- [REA](https://github.com/morluto/rea), JADX and Ghidra: tools used in the initial
  investigation of the shipped app.

This is a separate Python implementation informed by those sources and our device
observations. The distribution contains no APKs, decompiled proprietary app
code, copied upstream repositories, research bundles, Wi-Fi passwords or device
passcodes. Credits describe research context and are not endorsements by the
upstream maintainers. Contributors are encouraged to share useful findings
upstream and avoid unnecessary incompatible forks.

## Installation

Requires Home Assistant **2026.10.2 or newer**. The test environment uses
2026.10.2; later versions still require regression testing. No external Python
runtime dependencies are installed by this integration.

### Manual / local first install

1. Back up your Home Assistant configuration.
2. Copy only `custom_components/bestway_spa_local` into
   `/config/custom_components/bestway_spa_local`. Do not place the repository
   root itself under `custom_components`.
3. Restart Home Assistant to load the new integration.
4. Go to **Settings → Devices & services → Add integration → Bestway Spa**.
5. Enter the spa's home-network IPv4 address or hostname and a device name.

The setup flow verifies product identity and reads state. It does not turn on
power, heating, filtering or bubbles. Reserve the spa's IP in your router's DHCP
settings to make the configured address stable. A reservation does not improve
radio signal or prevent AP fallback.

### HACS custom repository

1. In HACS, open **⋮ → Custom repositories**.
2. Add `https://github.com/madisonleavo/home-assistant-bestway-local` with type
   **Integration**.
3. Find **Bestway Spa Local**, download it, and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → Bestway Spa** and
   enter the spa's home-network address.

Until a tagged release is published, HACS downloads the repository's default
branch. This is a custom-repository installation; the project is not listed in
HACS's default catalog. Initial setup reads state without operating the pump.

## Entities and operation

- A thermostat with water/target temperature, off/heat mode and heating/idle state.
- Power, heater, filter and panel-lock switches.
- Bubbles off/low/high selector (device levels 0/50/100).
- Water/target temperature, heater/filter state and bubbles-level sensors.
- Target-reached and fault indicators.

Temperatures follow the pump's current native Fahrenheit/Celsius setting. HA can
convert displayed temperatures; commands are rounded to the nearest whole native
degree. The native limits are 68–104 °F or 20–40 °C. Changing the physical panel's
unit setting is detected on a later read.

Thermostat **off disables heating**, not main power or filtering. Main power is
a separate switch. Turning the integration off, unloading it, restarting HA or
removing it never turns the physical spa off. Local panel controls remain the
authority for the equipment's interlocks and physical operating state.

The climate entity does not equate heater enabled with element energized:
maintaining-with-element-off is idle, while heating and
maintaining-with-element-on are heating. Filter waiting is distinguished from
running. V01 E32 is target-reached, not an alarm.

Add entities to your existing dashboard in the HA UI or adapt
[the standard-card example](examples/dashboard.yaml). No custom frontend card
or separate web dashboard is required.

## Startup, shutdown and network load

Each configured spa owns one serialized TCP client and one heartbeat task. State
polls default to every 15 seconds (configurable 10–300 seconds); heartbeats run
about every four seconds. Operations have timeouts and frame-size bounds.
Repeated failures back off up to five minutes and mark entities unavailable.
Sustained failures create one HA Repairs notice, cleared on recovery.

Commands read fresh state, preserve reserved fields, send one control request,
match its acknowledgement sequence and read state again. An uncertain outcome
is reported as an error, never automatically replayed. Startup/reconnect/unload
send no control commands. Shutdown closes owned sockets and stops owned tasks,
including an in-progress connection attempt. No polling loop spins while offline.

The integration stores the local device passcode in HA's private config-entry
storage to support reconnects after a physical binding window. It is not a home
Wi-Fi password. Treat HA configuration and backups as private; diagnostics omit
passcodes, host addresses, MAC addresses and device IDs.

## Wi-Fi recovery

If the spa returns to `BW-Airjet-V01-…` setup AP mode, see the
[iPhone/iPad recovery guide](docs/recovery.md). A small standalone Python helper
prompts locally for credentials and sends the same provisioning format that was
verified during the original device investigation.

HA can report an outage and reconnect when the device returns. An Ethernet-only
HA host cannot join a separate spa hotspot by itself. The integration does not
store your home Wi-Fi password, reset the pump, switch your networks, or send
provisioning credentials automatically. AP fallback alone does not prove the
pump erased its stored Wi-Fi settings.

## Updating, rollback and removal

Keep a copy of the previous release and a HA backup. For a manual update, replace
the integration directory as a whole, then restart HA; do not mix files from
different versions. For rollback, reinstall the previous version as a whole and
restart. Version 0.1 uses config-entry schema version 1 and performs no firmware
updates or irreversible device configuration migrations.

This first `bestway_spa_local` version has no compatibility promise for a future
config-entry schema migration. A future release that changes the schema must
document downgrade limitations before release. HACS version rollback also
depends on keeping the corresponding release available.

To remove it, delete its entry under Devices & services, remove the integration
files through HACS or manually, and restart HA. This removes monitoring/control
from HA; the physical pump continues its current behavior. It does not clear
the pump's Wi-Fi credentials.

## Development and extending support

Use Python 3.14.2+ and an isolated environment:

```sh
pip install -r requirements-dev.txt
pytest -q
ruff check .
ruff format --check .
python tools/build_release.py
```

Tests use synthetic local servers and the sanitized state layout captured from
the initial V01. They never operate a physical spa. The HA test fixtures check
for lingering tasks/timers and accidental network use; protocol tests explicitly
enable loopback sockets.

See [extension guide](docs/extending.md), [contribution guidance](CONTRIBUTING.md),
and [release checklist](docs/releasing.md). Keep each new product's identity,
codec, fixtures and actual hardware validation together. An unknown product key
is not a reason to try the existing write layout.

## License

[MIT](LICENSE), as selected by the repository owner. The license applies to the
rights contributors can grant in this project's code and documentation. AI
assistance does not establish ownership of third-party material or eliminate
third-party license obligations. Dependencies and referenced projects retain
their own licenses.

In the US, copyrightability of AI-assisted material depends on human authorship;
using AI does not automatically bar protection, and purely generated material
is a separate question. The MIT notice is not a claim that every generated line
has copyright protection. See the
[US Copyright Office's explanation](https://www.copyright.gov/newsnet/2025/1060.html)
and the [MIT text](https://opensource.org/license/mit).
