import os
import re

import pytest

from licheats.settings import Settings, SettingsError, _split_csv


def test_split_csv_trims_and_omits_empty_values():
    assert _split_csv(" http://a, ,http://b ", ("default",)) == ("http://a", "http://b")
    assert _split_csv(None, ("default",)) == ("default",)


def test_settings_from_env_parses_supported_values(monkeypatch):
    monkeypatch.setenv("LICHEATS_DB_URL", "sqlite:///:memory:")
    monkeypatch.setenv("LICHESS_BASE_URL", "https://lichess.test/")
    monkeypatch.setenv("LICHEATS_REQUEST_TIMEOUT", "7.5")
    monkeypatch.setenv("LICHEATS_CORS_ORIGINS", "http://127.0.0.1:8000, http://localhost:8000")
    monkeypatch.setenv("LICHEATS_CORS_ORIGIN_REGEX", "")

    settings = Settings.from_env()

    assert settings.db_url == "sqlite:///:memory:"
    assert settings.lichess_base_url == "https://lichess.test"
    assert settings.request_timeout == 7.5
    assert settings.cors_origins == ("http://127.0.0.1:8000", "http://localhost:8000")
    assert settings.cors_origin_regex is None


def test_default_cors_regex_allows_chrome_and_firefox_extension_origins():
    regex = Settings(db_url="sqlite:///:memory:").cors_origin_regex

    assert re.fullmatch(regex, "chrome-extension://abcdefghijklmnopabcdefghijklmnop")
    assert re.fullmatch(regex, "moz-extension://d5f2a3b1-1c2d-4e5f-8a9b-0c1d2e3f4a5b")
    assert not re.fullmatch(regex, "https://evil.example.com")


def test_settings_from_env_rejects_invalid_timeout(monkeypatch):
    monkeypatch.setenv("LICHEATS_REQUEST_TIMEOUT", "not-a-number")

    with pytest.raises(SettingsError, match="LICHEATS_REQUEST_TIMEOUT"):
        Settings.from_env()


def test_settings_from_env_rejects_non_positive_timeout(monkeypatch):
    monkeypatch.setenv("LICHEATS_REQUEST_TIMEOUT", "0")

    with pytest.raises(SettingsError, match="positive"):
        Settings.from_env()


def test_settings_from_env_uses_default_db_url_when_unset(monkeypatch, tmp_path):
    for key in list(os.environ):
        if key.startswith("LICHEATS_") or key in {"LICHESS_API_TOKEN", "LICHESS_BASE_URL"}:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    settings = Settings.from_env()

    assert settings.db_url.startswith("sqlite:///")
    assert str(tmp_path) in settings.db_url
