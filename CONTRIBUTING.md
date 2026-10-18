# Contributing

Small, reviewable contributions and shared protocol observations are welcome.
Credit prior work, describe whether code was AI-assisted, and have a human owner
review a change before proposing a release. AI-generated tests do not constitute
hardware verification or independent human review.

Read the README and device/extension guides first. Add a failing regression test
for a bug before changing behavior. Run the complete tests and Ruff using the
pinned development dependencies. A proposed feature must describe behavior at
startup, cancellation, shutdown, connectivity loss and recovery.

Report product key, firmware/model identifiers, integration/HA versions and
reproducible behavior. Do not include device passcodes, Wi-Fi credentials, local
IP/MAC/device IDs or unredacted backups. The diagnostics download uses an
allowlist; still inspect what you share. Synthetic packet fixtures are preferred.

For another model, submit an independent device profile and evidence; do not
relax the supported-product guard. Keep changes reusable by existing community
projects. A public API description may be more useful than another fork. Check
upstream licensing before copying source, and retain required notices.

Record sources, revisions, tool use and AI assistance honestly; see
[research provenance](docs/provenance.md). Do not call a change clean-room if its
authors/agents read decompiled or upstream implementation code. Publicly visible
code without a license is not permission to copy it. Never submit APKs,
decompiler output or vendor graphics as original MIT material. Describe any
adapted source and preserve its required license/copyright notices; attribution
alone does not authorize reuse. Use only devices/accounts you own or may access.

Contribution does not imply a promise of support for all Bestway products. No
automated CI job may operate real heating equipment. Physical validation is an
explicit human-run test with results recorded separately from software tests.
