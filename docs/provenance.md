# Research provenance and publication boundaries

Recorded on 2026-10-17. This account describes the retained research evidence and
development process; it is not a legal opinion or a claim of manufacturer approval.

## Purpose and people

The owner wanted to provision and locally control their own Milan AirJet V01
without opening its control box, after official iOS pairing timed out. The owner
selected the requirements, ran the physical-device probes, and chose MIT for the
project. AI agents performed much of the investigation, implementation, test
writing, documentation and review. Human expert code review and legal review
have not been established. No upstream maintainer has endorsed this project or
been contacted on its behalf.

This was **not a formal clean-room implementation**. The AI development process
had access to readable app assets, decompiled Java/native output and community
reference code. A separate public repository does not remove that exposure or
prove that a work is legally independent. The implementation was written as new
Python code from the recovered wire behavior; no deliberate source transplant
was identified in the publication audit. That audit is limited and cannot prove
the absence of copyright infringement, including similarities introduced by AI.

## Artifact examined

| Item | Recorded value |
| --- | --- |
| App | Bestway Smart Hub |
| Android package | `com.layzspa.smartHome` (capital H) |
| Version / version code | `2.2.74` / `550074` |
| APK bytes | 31,659,734 |
| APK SHA-256 | `2352ca1297da492f9c958b8f9dfc72937ef574bb43eac3604e513a98d2d7ff1b` |
| Native library examined | `lib/arm64-v8a/libGizWifiDaemon.so` |
| Native library SHA-256 | `481a02561bffdce9174faf377879b5347537ca28c9574e585c1ed22cd95b0c96` |
| Tools recorded | REA 6.5.0, JADX headless MCP 0.7.1, Ghidra 12.1.4 |
| Acquisition | APKPure mirror, requested by package and version code; not extracted from the owner's phone |

The hash identifies the examined bytes; it does not establish authenticity,
permission to redistribute or a lawful right to use that particular mirror copy.
JAR verification reported success with certificate/ZIP warnings, but the signer
was not authenticated as Bestway and APK v2/v3 verification was not established.
The APK/native library was statically examined, not installed or executed in the
investigation. Only this version was examined; no superiority over other app
versions was established. This repository distributes neither artifact.

## How observations became implementation

| Input | What it informed | Where it appears here | Limitation |
| --- | --- | --- | --- |
| Readable Cordova product configuration | Product keys, hotspot families and app-selected onboarding modes | `docs/device-catalog.json`, supported-device guide | App listing is not proof of working LAN support |
| Shipped app UI/template logic | V01 command values, native temperature limits and status meanings | V01 codec and entity mappings | Static observations need hardware confirmation |
| JADX inspection of the app bridge | Distinction between Bluetooth-assisted and SoftAP provisioning | Recovery explanation | Not a guarantee about every pump firmware |
| Ghidra inspection of native provisioning functions | Credential lengths, framing, destination and acknowledgement | `tools/recover_wifi.py` | Recovered wire behavior, not redistributed decompiler output |
| Gizwits datapoint service | Field order/types, writable counts and candidate device definitions | V01 layout and curated catalog | Reachability is not a license to republish the full responses |
| Community protocol references | LAN framing, discovery, authentication, read/write and heartbeat behavior | Async protocol client and tests | Credit does not grant source-reuse permission |
| Owner-run UDP/TCP probes | Actual V01 identity, accepted onboarding, local login and status | Supported-device evidence and sanitized status fixture | No physical control-write or long-term deployment claim |
| Synthetic endpoints and HA fixtures | Malformed data, acknowledgement/readback, lifecycle, recovery and packaging regressions | Tests and CI | Simulation cannot establish hardware safety or compatibility |

Ghidra was particularly useful for confirming that the native SoftAP caller
sends only length-prefixed SSID/password fields to `10.10.100.254:12414` using
commands 1/2. The retained symbols were `softapDataPackage`,
`GizWifiSDKSetSoftAPConfig` and `GizWifiSDKBuildHead`. The published GAgent UDP
implementation provided a separate cross-check. The owner then received the
acknowledgement and successfully performed LAN login/status reads after joining
home Wi-Fi. The current recovery helper itself has automated packet/ACK tests;
the physically tested provisioning attempt used an earlier equivalent probe.

The datapoint requests used a Gizwits application-ID header read from the app,
without a user account/device token. We do not treat that identifier or the
service's unauthenticated reachability as authorization for arbitrary API use.
The integration makes no such cloud requests at runtime. Full request/response
dumps, decompiled output and device-specific captures remain outside this
repository. Some manufacturer legal URLs linked below contain the same app-level
identifier; it is not the owner's device passcode or Wi-Fi credential. The public
catalog is a curated factual summary with source URLs, not the original schema bundle.

## Community sources and rights boundaries

- [cdpuk/ha-bestway](https://github.com/cdpuk/ha-bestway): established HA integration
  and ecosystem/device research. Its checked license is MIT. Its source was not
  vendored into this integration.
- [fanuelsen/tubctl](https://github.com/fanuelsen/tubctl): local-control research
  and a useful legacy AirJet comparison. The checked snapshot had no license file
  and GitHub metadata reported no license. Public visibility and attribution do
  not authorize copying/adapting its protected source. No tubctl source is
  distributed here; permission/license clarification is required before any
  future source reuse. Its legacy datapoint layout was unsuitable for this V01.
- [Apollon77/node-ph803w](https://github.com/Apollon77/node-ph803w): published
  Gizwits LAN protocol research. The repository identifies MIT licensing. We
  consulted protocol documentation; its prose/source was not vendored here.
- [Gizwits GAgent](https://github.com/gizwits/Gizwits-GAgent): manufacturer-published
  C implementation consulted to cross-check wire behavior. No blanket reuse
  permission is inferred from public availability; no GAgent source is shipped.
- [visualapproach/WiFi-remote-for-Bestway-Lay-Z-SPA](https://github.com/visualapproach/WiFi-remote-for-Bestway-Lay-Z-SPA):
  prior community hardware/serial work, credited for context; no source vendored.
- [REA](https://github.com/morluto/rea),
  [JADX](https://github.com/skylot/jadx) and
  [Ghidra](https://github.com/NationalSecurityAgency/ghidra): analysis tools, not
  runtime dependencies or bundled components. Using a tool does not itself
  grant rights in the program being analyzed.

Future copied/adapted material needs a source, revision, license and retained
notices. MIT in this repository cannot relicense someone else's work. Product
names identify compatibility; the project has no manufacturer affiliation and
uses an original geometric icon rather than a vendor logo. Useful protocol
findings and fixes should be shared with existing projects when appropriate;
credit is not a claim of their endorsement or support commitment.

## Legal considerations and unresolved questions

Ghidra is a publicly released reverse-engineering framework under an Apache 2.0
license. Its use is not, by itself, proof of illegality or legal clearance.
The relevant questions include acquisition rights, copyright, access controls,
contracts, local law and what is distributed.

For US context, [17 U.S.C. §102(b)](https://www.law.cornell.edu/uscode/text/17/102)
distinguishes methods/systems from protected expression, and
[§1201(f)](https://www.law.cornell.edu/uscode/text/17/1201) provides conditional
interoperability exceptions, including lawful-use and noninfringement conditions.
The [Copyright Office's consumer-products study](https://www.copyright.gov/policy/software/)
discusses fair use in interoperability research. None of these establishes that
every reverse-engineering activity or resulting distribution is permitted.
An exception to copyright infringement does not automatically resolve contract,
access-control, patent or other legal issues.

On the review date, a
[Bestway manufacturer page](https://m.bestwaycorp.com.cy/DataActTransparencyDeclaration)
linked an [app user agreement](https://gwapi-1251025085.cos.ap-guangzhou.myqcloud.com/gdpr/98754e684ec045528b073876c34c7348_2_2.html).
That agreement restricts app-content copying/adaptation while recognizing
exceptions established by applicable law. The manufacturer page describes a
newer Connect app; whether that agreement/version governed the examined Smart
Hub APK, whether relevant terms were accepted, and their enforceability have
not been established. This link is evidence to examine, not a finding that the
terms either prohibit or authorize this project. Mirror acquisition rights and
the exact applicable terms remain unresolved. Qualified counsel would need the
actual jurisdiction, acquisition facts and terms to provide legal clearance.

The retained record describes static examination and normal local provisioning,
passcode retrieval and login on the owner's device. No DRM bypass, brute-force
credential attack, third-party account access or firmware modification is
documented. This is a factual description, not a legal conclusion that the
authentication or access-control rules cannot apply.

The MIT choice covers rights contributors can grant. The
[Copyright Office's AI guidance](https://www.copyright.gov/newsnet/2025/1060.html)
distinguishes human-authored contributions from purely generated expression.
AI assistance neither guarantees ownership nor erases third-party obligations.

## Ethical operating scope

Operate only equipment and networks you own or are authorized to administer.
Do not publish Wi-Fi credentials, device passcodes, account information or
identifying captures. Do not disable physical interlocks or claim that automated
tests replace physical validation. Unknown device profiles stay disabled.
Manufacturer firmware continues to enforce equipment behavior; this project
does not claim to have independently verified its safety interlocks.

Transparency means publishing an accurate method, evidence limits and attribution.
It does not require publishing proprietary binaries/decompiler listings or
personal data. Retained local research is kept separate for those reasons, not
to conceal the use of reverse engineering. Report a concrete rights/privacy
concern to the maintainer with the affected file and source; investigate and
correct it before further distribution.
