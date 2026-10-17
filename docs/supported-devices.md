# Supported devices and research candidates

Only product key `d3ac9226d983470284b5d133cf4fd6b4` is enabled in the integration.
The initial physical device is a Milan AirJet V01 with hotspot family
`BW-Airjet-V01-…`. Its Wi-Fi firmware string was `04X3000B` and the datapoint
version/model field was `0x0497`. Marketing names and seat counts alone are not
reliable compatibility identifiers.

| Operation on initial physical V01 | Evidence |
| --- | --- |
| Explicit SoftAP Wi-Fi provisioning | Owner received command-2 acknowledgement and subsequently found the device on home Wi-Fi |
| LAN discovery and product key | Owner received valid command-4 reply |
| Local passcode/login | Owner's probe logged in successfully |
| V01 status | Owner received 46-byte response; current/target 104 °F, heater4, filter2, E32 set |
| New integration's control writes | Simulated protocol tests only; physical verification pending |
| HA OS deployment and long-term reconnect/reboot behavior | Automated lifecycle tests; owner installation validation pending |
| New standalone recovery helper | Packet/ACK tests; prior equivalent provisioning workflow physically verified |

No original device ID, MAC or LAN address is needed in public fixtures. The
fixture keeps only the product datapoint status layout.

## Other app-listed device families

Public Gizwits datapoint definitions were retrieved on 2026-10-17 for the
following product keys. They are **research candidates, not enabled controls or
claims of LAN compatibility**. The manufacturer API may change or disappear.
Machine-readable source links and counts are in [device-catalog.json](device-catalog.json).

| Family | Product key | App onboarding | Writable datapoints | Status |
| --- | --- | --- | --- | --- |
| AirJet V01 | `d3ac9226d983470284b5d133cf4fd6b4` | Bluetooth-assisted Wi-Fi; setup hotspot also observed | 29 | Initial confirmed device |
| Older AirJet | `fbc861733103419b9c2a09c71584cfe5` | SoftAP | 14 | Candidate; different layout |
| HydroJet | `095d319378614b7d81663c812f207288` | Bluetooth-assisted Wi-Fi | 29 | Candidate |
| HydroJet Pro | `3d718ac2d47f45778e591614ced793da` | Bluetooth-assisted Wi-Fi | 29 | Candidate |
| UltraFit | `ddb34fb0df8d4f75b3633d5277f82bb1` | Bluetooth-assisted Wi-Fi | 29 | Candidate |
| Flowclear pool filter | `8bc1c03fc3d64204b9925591664b5c20` | SoftAP | 2 | Candidate; not a spa |
| Built-in airbed pump | `99763dc38ea64178a71b509efbbb17ed` | SoftAP | 3 | Candidate; not a spa |

The four newer spa definitions contain the same number of datapoints, but that
does not establish identical behavior, available hardware, control values, or
local authentication. V02/AWS/SmartSpa products are not supported by this
Gizwits V01 integration. Do not add a product key to the registry solely because
its schema looks similar.
