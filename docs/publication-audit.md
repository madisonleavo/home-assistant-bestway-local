# Publication audit

Reviewed on 2026-10-17 using repository history through implementation commit
`b8c64fa` and the subsequent transparency-documentation change. This is an
AI-assisted technical/provenance review, not legal clearance or an independent
human expert review. See [provenance](provenance.md) for methods and open questions.

## History and privacy findings

The clean repository was cloned from the owner's GitHub repository. Its initial
commit `10259e6` contains the owner's MIT license and Python ignore file. Local
feature branch `feature/local-v01` then adds the integration in `b8c64fa`.
The earlier research/implementation repository's history was not imported.
That packaging choice is documented here; this public history is not a complete
chronological laboratory notebook and is not evidence of a clean-room process.

Checks covered every reachable commit across local/remote branches, not just
the current checkout. Before this documentation change that meant two commits
and 43 distinct file blobs. Git object checking found no unreachable objects.

- No APKs, native libraries, packet captures, decompiled listings, research
  folders, environments or generated release archives were present in that history.
- Targeted byte-pattern scans found no private-key blocks, GitHub/AWS credential
  patterns, credential-bearing URLs or the observed spa's MAC/LAN address.
- Passcodes in test fixtures are labeled synthetic. Product keys identify device
  families; the shared setup-AP password and `10.10.100.254` are protocol/setup
  constants, not the owner's Wi-Fi password or private device passcode.
- The original GitHub commit's author metadata is retained. Git author names and
  email addresses are public metadata when commits are published. The AI-created
  implementation commit identifies `Codex <codex@localhost>` rather than
  impersonating the human owner.
- The owner's MIT license is byte-for-byte unchanged.

These targeted scans are not an exhaustive secret detector. They cannot prove
that arbitrary text contains no secret, or examine unrelated remote systems,
backups or every possible AI training influence. `.gitignore` is preventive;
it cannot remove something that was already committed. The history checks above
are separate from that ignore file.

## Source and credit review

The distributed file list was inspected. It contains the new Python integration,
tests, helper/build tools, an original geometric icon, curated device metadata
and project documentation. No upstream repository or decompiler listing is vendored.

A limited literal comparison checked runtime Python against 28 retained community
reference/decompiled files. It found no run of three consecutive identical
nontrivial lines (blank/short lines excluded). This heuristic does **not** detect
translations, paraphrased derivation or all substantial similarity and is not
proof of independent authorship. The process was not clean-room. License review
identified the missing tubctl license as a restriction on future source reuse;
attribution alone would not cure unauthorized copying.

README/provenance name community projects, tool use, mirror acquisition, AI
involvement and hardware-validation limits. Outstanding acquisition/terms/legal
questions remain explicit. No contact with upstream authors, manufacturer
permission or lawyer approval is claimed.

## Rechecking before publication

Inspect `git log --all --stat`, every newly introduced file and
`git diff --cached --check`. Enumerate historical paths with
`git rev-list --objects --all` and inspect historical blobs with `git cat-file`;
do not rely only on the current tree. Run an appropriately configured secret
scanner as an additional check when available. Review alerts in context without
posting suspected credentials to a public issue or CI log.

Rebuild archives with `python tools/build_release.py`, inspect their contents and
retain the SHA-256 checksum file. Only allowlisted files enter the archives.
Keep the provenance and this audit with the distribution. Recheck source rights
and notices whenever copying/adapting third-party material or adding a device.
Do not turn this dated audit into a blanket claim that future commits are clean.
