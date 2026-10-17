"""Release artifacts contain the reviewed source, not the research workspace."""

import importlib.util
import json
import zipfile
from pathlib import Path


def load_builder():
    path = Path(__file__).parents[1] / "tools/build_release.py"
    spec = importlib.util.spec_from_file_location("release_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_archive_is_deterministic_and_contains_no_research(tmp_path):
    root = Path(__file__).parents[1]
    builder = load_builder()
    first = builder.build_archives(root, tmp_path / "one")
    second = builder.build_archives(root, tmp_path / "two")
    assert first["runtime"].read_bytes() == second["runtime"].read_bytes()
    with zipfile.ZipFile(first["runtime"]) as z:
        names = z.namelist()
        assert "custom_components/bestway_spa_local/manifest.json" in names
        assert "LICENSE" in names
        assert not any(x.startswith(("analysis/", "references/", "tests/", ".git/")) for x in names)
        assert not any(x.endswith((".apk", ".so", ".pyc")) or "__pycache__" in x for x in names)
        manifest = json.loads(z.read("custom_components/bestway_spa_local/manifest.json"))
        assert manifest["domain"] == "bestway_spa_local"


def test_source_archive_has_tests_credit_and_standalone_recovery(tmp_path):
    root = Path(__file__).parents[1]
    files = load_builder().build_archives(root, tmp_path)
    with zipfile.ZipFile(files["source"]) as z:
        names = z.namelist()
        assert "tools/recover_wifi.py" in names
        assert "tests/test_protocol.py" in names
        assert "docs/extending.md" in names
        assert "vibe-coded" in z.read("README.md").decode()
        assert not any(".git/" in x or "__pycache__" in x or x.startswith("dist/") for x in names)
