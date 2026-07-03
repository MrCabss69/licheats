import json
from pathlib import Path

EXTENSION_ROOT = Path("lichess-assistant-extension/chrome")


def test_manifest_exposes_local_backend_permissions():
    manifest = json.loads((EXTENSION_ROOT / "manifest.json").read_text())

    assert manifest["manifest_version"] == 3
    assert "https://*.lichess.org/*" in manifest["host_permissions"]
    assert "http://127.0.0.1:8000/*" in manifest["host_permissions"]
    assert "http://localhost:5000/*" not in manifest["host_permissions"]


def test_popup_uses_packaged_assets_and_modern_api_contract():
    popup_html = (EXTENSION_ROOT / "popup.html").read_text()
    popup_js = (EXTENSION_ROOT / "popup.js").read_text()

    assert "https://cdn" not in popup_html
    assert "stackpath" not in popup_html
    assert "cdn.jsdelivr" not in popup_html
    assert '<script src="popup.js" defer></script>' in popup_html
    assert "http://127.0.0.1:8000" in popup_js
    assert "/players/${encoded}/analysis" in popup_js
    assert "localhost:5000" not in popup_js
    assert "get_player_stats" not in popup_js
