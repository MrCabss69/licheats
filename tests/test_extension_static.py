import json
import subprocess
from pathlib import Path

EXTENSION_ROOT = Path("lichess-assistant-extension/chrome")


def test_manifest_exposes_local_backend_permissions():
    manifest = json.loads((EXTENSION_ROOT / "manifest.json").read_text())

    assert manifest["manifest_version"] == 3
    assert "https://*.lichess.org/*" in manifest["host_permissions"]
    assert "http://127.0.0.1:8000/*" in manifest["host_permissions"]
    assert "http://localhost:5000/*" not in manifest["host_permissions"]


def test_manifest_is_cross_browser():
    manifest = json.loads((EXTENSION_ROOT / "manifest.json").read_text())

    # A single MV3 manifest serves Chromium (ignores the gecko key) and Firefox.
    assert manifest["manifest_version"] == 3
    gecko = manifest["browser_specific_settings"]["gecko"]
    assert gecko["id"] == "licheats@local"
    assert gecko["strict_min_version"] == "115.0"
    # We rely on having no background worker: Firefox < 121 lacks MV3 service workers.
    assert "background" not in manifest


def test_popup_uses_packaged_assets_and_modern_api_contract():
    popup_html = (EXTENSION_ROOT / "popup.html").read_text()
    popup_js = (EXTENSION_ROOT / "popup.js").read_text()

    assert "https://cdn" not in popup_html
    assert "stackpath" not in popup_html
    assert "cdn.jsdelivr" not in popup_html
    assert '<script src="popup.js" defer></script>' in popup_html
    assert 'role="tablist"' in popup_html
    assert 'data-tab="prep"' in popup_html
    assert 'data-tab="style"' in popup_html
    assert 'data-tab="trends"' in popup_html
    assert 'id="heroVerdict"' in popup_html
    assert "http://127.0.0.1:8000" in popup_js
    assert "/players/${encoded}/profile-summary" in popup_js
    assert "/players/${encoded}/analysis" in popup_js
    assert "/players/${encoded}/sync-jobs" in popup_js
    assert "/sync-jobs/${encodeURIComponent(jobId)}" in popup_js
    assert "include_moves=false" in popup_js
    assert "page_size=${SYNC_BATCH_SIZE}" in popup_js
    assert "games_count" in popup_js
    assert "coverage" in popup_js
    assert "coverage-meter" in popup_js
    assert "win_rate" in popup_js
    assert "avg_opponent_rating" in popup_js
    # Color-aware prep (point 2) consumes the per-color opening split.
    assert "openings_by_color" in popup_js
    assert "localhost:5000" not in popup_js
    assert "get_player_stats" not in popup_js


def test_content_script_detects_opponent_and_color():
    content_js = (EXTENSION_ROOT / "content.js").read_text()

    script = f"""
const vm = require('node:vm');
const source = {json.dumps(content_js)};

function rootWithName(name) {{
  return {{
    textContent: name,
    querySelector(selector) {{
      if (selector === 'a.user-link, a[href^="/@/"]') return {{ textContent: name }};
      return null;
    }},
  }};
}}

let listener = null;
const top = rootWithName('@Opponent 1800');
const bottom = rootWithName('@Me 1700');
const wrap = {{ classList: {{ contains(cls) {{ return cls === 'orientation-white'; }} }} }};
const document = {{
  querySelector(selector) {{
    if (selector === '.ruser-top') return top;
    if (selector === '.ruser-bottom') return bottom;
    if (selector === '.cg-wrap, .round__app .cg-wrap') return wrap;
    return null;
  }},
}};
const chrome = {{
  runtime: {{ onMessage: {{ addListener(callback) {{ listener = callback; }} }} }},
}};

vm.runInNewContext(source, {{ document, chrome }});
let response = null;
listener({{ action: 'fetchNickname' }}, null, (payload) => {{ response = payload; }});
console.log(JSON.stringify(response));
"""
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)

    assert json.loads(result.stdout) == {
        "nickname": "Opponent",
        "yourColor": "white",
        "opponentColor": "black",
    }


def test_content_script_fallback_has_no_color_context():
    content_js = (EXTENSION_ROOT / "content.js").read_text()

    script = f"""
const vm = require('node:vm');
const source = {json.dumps(content_js)};
let listener = null;
const fallback = {{
  textContent: '@SpectatedPlayer',
  querySelector(selector) {{
    if (selector === 'a.user-link, a[href^="/@/"]') return {{ textContent: '@SpectatedPlayer' }};
    return null;
  }},
}};
const document = {{
  querySelector(selector) {{
    if (selector === 'a.user-link[href^="/@/"]') return fallback;
    return null;
  }},
}};
const chrome = {{
  runtime: {{ onMessage: {{ addListener(callback) {{ listener = callback; }} }} }},
}};

vm.runInNewContext(source, {{ document, chrome }});
let response = null;
listener({{ action: 'fetchNickname' }}, null, (payload) => {{ response = payload; }});
console.log(JSON.stringify(response));
"""
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)

    assert json.loads(result.stdout) == {
        "nickname": "SpectatedPlayer",
        "yourColor": None,
        "opponentColor": None,
    }
