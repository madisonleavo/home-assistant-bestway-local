#!/usr/bin/env python3
"""Build deterministic, allowlisted local archives; never publish or read secrets."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

DOMAIN = "bestway_spa_local"
SOURCE_DIRS = {"custom_components", "tests", "tools", "docs", "examples", ".github"}
SOURCE_FILES = {
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "hacs.json",
    "pyproject.toml",
    "requirements-dev.txt",
    ".gitignore",
}
SUFFIXES = {".py", ".json", ".md", ".txt", ".toml", ".yaml", ".yml", ".hex", ".svg", ".png"}


def _write_zip(destination, root, files):
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(files):
            name = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def build_archives(root: Path, output: Path) -> dict[str, Path]:
    """Only known source directories and suffixes enter a release."""
    root, output = root.resolve(), output.resolve()
    manifest = json.loads((root / "custom_components" / DOMAIN / "manifest.json").read_text())
    if manifest["domain"] != DOMAIN:
        raise ValueError("Unexpected integration domain")
    version = manifest["version"]
    output.mkdir(parents=True, exist_ok=True)
    source = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_symlink() or not path.is_file() or "__pycache__" in relative.parts:
            continue
        if relative.as_posix() in SOURCE_FILES or (
            relative.parts[0] in SOURCE_DIRS
            and path.suffix in SUFFIXES
            and not any(part.startswith(".") for part in relative.parts[1:-1])
        ):
            source.append(path)
    runtime = [
        path
        for path in source
        if path.relative_to(root).as_posix() in {"LICENSE", "README.md"}
        or path.relative_to(root).parts[:2] == ("custom_components", DOMAIN)
    ]
    result = {
        "runtime": output / f"{DOMAIN}-{version}.zip",
        "source": output / f"home-assistant-bestway-local-{version}-source.zip",
    }
    _write_zip(result["runtime"], root, runtime)
    _write_zip(result["source"], root, source)
    checksums = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in result.values()
    )
    (output / "SHA256SUMS").write_text(checksums)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = build_archives(root, args.output or root / "dist")
    for kind, path in paths.items():
        print(f"{kind}: {path}")


if __name__ == "__main__":
    main()
