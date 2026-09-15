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
    assert './frontend/auth.js' in html
    assert './pwa/register.js' in html
    assert 'id="screen-home"' in html
    assert 'id="global-bottom-nav"' in html
    assert 'id="auth-gate"' in html
    assert 'id="auth-login-form"' in html
    assert 'id="auth-signup-form"' in html
    assert 'id="logout-button"' in html


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
    assert "credentials: 'include'" in client
    assert "register:" in client
    assert "resetPassword:" in client


def test_auth_frontend_files_are_in_the_pwa_shell() -> None:
    service_worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
    auth = (ROOT / "frontend/auth.js").read_text(encoding="utf-8")

    assert "havcan-shell-v2-auth" in service_worker
    assert "./frontend/auth.js" in service_worker
    assert "global.HavcanAuth" in auth
    assert "global.HavcanAPI.me()" in auth