"""Static checks for the browser foundation added around the existing UI."""

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_existing_ui_has_foundation_hooks() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert '<title>HAVCAN - Creative Work, Handled.</title>' in html
    assert 'rel="manifest"' in html
    assert './frontend/api-client.js' in html
    assert './frontend/app-state.js' in html
    assert './pwa/register.js' in html
    assert 'id="screen-home"' in html
    assert 'id="global-bottom-nav"' in html


def test_pwa_assets_and_manifest_are_consistent() -> None:
    manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))

    assert manifest["name"].startswith("HAVCAN")
    assert manifest["start_url"] == "./index.html"
    assert (ROOT / "service-worker.js").exists()
    for icon in manifest["icons"]:
        assert (ROOT / icon["src"]).exists()


def test_api_client_exposes_health_boundary() -> None:
    client = (ROOT / "frontend/api-client.js").read_text(encoding="utf-8")

    assert "global.HavcanAPI" in client
    assert "health: () => request('/health')" in client