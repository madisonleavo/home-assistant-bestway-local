# Release and rollback checklist

Version 0.1.0 is experimental and unpublished. The GitHub repository exists;
source publication, HACS default inclusion, HA OS installation and physical
control validation are distinct steps.

1. Review changes, credits, MIT notices and AI provenance. A named human owns
   release decisions; independent AI review is documented as AI review.
   Recheck [provenance](provenance.md) and the [publication audit](publication-audit.md),
   including unresolved acquisition/terms questions. Neither an AI audit nor MIT
   is legal clearance. Check historical blobs as well as the current file list.
2. Run the pinned development test environment and Ruff. Check no task/timer
   cleanup failures or unexpected network calls are suppressed. Keep CI results.
3. Record exact live device product/firmware and which operations were verified.
   Do not turn simulator coverage into hardware claims. Confirm HA OS setup and
   a reversible write/readback before promoting a physically tested release.
4. Keep schema version1 for compatible updates. If a future schema migration
   prevents downgrade, announce that before release and provide a backup path.
5. Update manifest version, project version and changelog together.
6. Run `python tools/build_release.py`. Inspect both archives and checksums.
   The runtime archive uses an explicit file allowlist; it contains no research
   workspace, credentials, device discovery captures, binaries or environments.
7. Before publishing, review `git status` and the exact commit contents. Push
   only this repository. Keep experimental releases marked as such and retain
   older release files so users can reinstall a prior version.
8. Test an update and downgrade by replacing the integration directory as a
   whole and restarting HA. Unloading must close tasks/sockets without turning
   off power, heat or filtration on the physical spa.

The GitHub CI workflow runs tests/lint and builds artifacts; it has no deployment
job and no permission to operate a physical device. Generated local zips are not
committed. `hacs.json` supports custom-repository installation once code is
published. It does not apply to or guarantee inclusion in the HACS default list.
