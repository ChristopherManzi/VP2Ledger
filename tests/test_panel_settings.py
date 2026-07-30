"""Round trip of the control panel's settings file."""

from vp2ledger.panel import read_settings, write_settings


def test_round_trip(tmp_path):
    location = tmp_path / "vp2ledger_settings.json"
    settings = {"host": "198.51.100.7", "pace": 120.0, "metric": False}
    write_settings(settings, location)
    assert read_settings(location) == settings


def test_absent_file_yields_empty_settings(tmp_path):
    assert read_settings(tmp_path / "nowhere.json") == {}


def test_garbage_file_yields_empty_settings(tmp_path):
    location = tmp_path / "mangled.json"
    location.write_text("{not json at all", encoding="utf-8")
    assert read_settings(location) == {}
