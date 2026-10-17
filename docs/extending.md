# Extending device support

The runtime protocol code is dependency-free in
`custom_components/bestway_spa_local/protocol.py`. HA lifecycle/configuration
and entities wrap it; neither the framing nor the codec imports Home Assistant.
The standalone recovery helper intentionally carries its own small provisioning
packet encoder so it can run on an iPhone without installing the integration.

## Product profiles

The `PROFILES` registry selects a `ProductProfile` by the product key returned
by discovery. Initially it contains only V01. A profile supplies the model and
its status decoder/control encoder. The client continues to own identity,
authentication, sequencing, heartbeat, stream framing and lifecycle.

To add another spa:

1. Obtain an actual discovery reply, its product key and firmware identifiers.
   Sanitize device IDs, MACs, IPs and credentials before sharing it.
2. Obtain the corresponding product datapoint definition and record its source
   and retrieval date. Identify native units, bit/byte order, writable attribute
   IDs, raw writable prefix length, fault/indicator meanings and state enums.
3. Add a separate codec/profile with those facts. Do not change V01 offsets or
   loosen identity guards to accommodate a new layout. `SpaState` is the common
   spa entity model; non-spa families require their own entity design.
4. Add a real sanitized status fixture and tests for every mapped field. Check
   byte boundaries, malformed lengths, native-unit limits, and all reserved bits.
5. Add a control-vector test for each exposed writable field. It must patch only
   the selected value in a fresh raw snapshot, set the correct mask bit, preserve
   everything else, and verify state readback after a matching acknowledgement.
6. Verify startup, read-only connection, a small reversible physical write,
   control readback, reconnect after pump/HA restart, and local-panel operation.
   Keep these physical observations separate from simulator results.
7. Add the profile explicitly to the registry, update compatibility/release
   notes, and get review. Document unknowns and hardware-specific omissions.

The original profile functions `decode_status(payload)` and
`encode_control(state, updates)` remain available for focused tests and reuse.
Transport tests use local fake UDP/TCP devices and do not connect to a spa.

## Lifecycle rules for contributors

- Network work belongs in async methods, never entity properties or import time.
- One config entry owns one client; do not add a timer per entity.
- Always bound frames, response waits, discovery and reconnect intervals.
- Keep commands serialized; never retry an ambiguous control write.
- Stop must prevent a pending opener from creating resources afterward.
- Close the client after failed setup and after partially loaded platforms fail.
- Preserve cancellation; do not turn `CancelledError` into a successful command.
- Retain no home Wi-Fi password. Keep cached device passcodes out of repr/logs,
  diagnostics, state attributes, tests and public issue reports.
- Unload/reload/removal must not operate the physical spa.

Potential upstream work includes V01 profile support, provisioning documentation
and reusable packet fixtures. Credit existing projects and check their licenses
before incorporating source. A separately maintained deployment adapter should
not become a second incompatible implementation of the same protocol facts.
