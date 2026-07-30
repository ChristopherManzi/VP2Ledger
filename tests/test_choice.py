"""Persistence of the channel choice (channels.toml)."""

import pytest

from vp2ledger.channels import keys
from vp2ledger.choice import ChannelChoice


@pytest.fixture
def location(tmp_path):
    return tmp_path / "channels.toml"


def test_first_use_creates_the_file_with_everything_on(location):
    choice = ChannelChoice(location)
    assert location.is_file()
    assert choice.active() == list(keys())


def test_switching_off_survives_a_restart(location):
    ChannelChoice(location).switch("solar_rad", False)

    reloaded = ChannelChoice(location)
    assert not reloaded.is_active("solar_rad")
    assert "solar_rad" not in reloaded.active()
    assert reloaded.is_active("temp")


def test_unknown_key_is_rejected(location):
    with pytest.raises(KeyError):
        ChannelChoice(location).switch("flux_capacitor", True)


def test_old_files_gain_new_channels_but_keep_choices(location):
    # A file from an "older version" that only knew two channels.
    location.write_text("[channels]\ntemp = false\nhum = true\n", encoding="utf-8")

    choice = ChannelChoice(location)
    assert not choice.is_active("temp")           # kept
    assert choice.is_active("wind_speed_last")    # merged in, default on

    rewritten = location.read_text(encoding="utf-8")
    assert "temp = false" in rewritten
    assert "wind_speed_last = true" in rewritten


def test_active_keeps_column_order(location):
    choice = ChannelChoice(location)
    choice.switch("temp", False)
    active = choice.active()
    assert active == [key for key in keys() if key != "temp"]
