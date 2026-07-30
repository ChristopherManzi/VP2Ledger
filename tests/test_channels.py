"""Channel table, unit conversion and row projection."""

from vp2ledger import channels


class TestConversions:
    def test_fahrenheit_becomes_celsius(self):
        assert channels.project({"temp": 32.0}, ["temp"]) == {"temp": 0.0}

    def test_mph_becomes_kmh(self):
        row = channels.project({"wind_speed_hi_last_2_min": 20.0}, ["wind_speed_hi_last_2_min"])
        assert row["wind_speed_hi_last_2_min"] == 32.2

    def test_inhg_becomes_hpa(self):
        row = channels.project({"bar_absolute": 29.5}, ["bar_absolute"])
        assert row["bar_absolute"] == 999.0

    def test_indices_convert_like_temperatures(self):
        row = channels.project({"thsw_index": 86.0}, ["thsw_index"])
        assert row["thsw_index"] == 30.0

    def test_tip_counts_scale_with_the_announced_resolution(self):
        # resolution code 3 -> 0.1 mm per tip
        row = channels.project({"rainfall_last_60_min": 12, "rain_size": 3}, ["rainfall_last_60_min"])
        assert row["rainfall_last_60_min"] == 1.2

    def test_resolution_code_itself_becomes_mm_per_tip(self):
        assert channels.project({"rain_size": 4}, ["rain_size"]) == {"rain_size": 0.0254}

    def test_tip_counts_without_resolution_stay_raw(self):
        row = channels.project({"rainfall_daily": 7}, ["rainfall_daily"])
        assert row["rainfall_daily"] == 7

    def test_raw_mode_touches_nothing(self):
        raw = {"temp": 50.0, "bar_absolute": 29.5, "rain_size": 3}
        row = channels.project(raw, raw.keys(), metric=False)
        assert row == raw


class TestProjection:
    def test_row_follows_layout_order_not_input_order(self):
        raw = {"wind_dir_last": 270, "hum": 55.0, "temp": 50.0}
        row = channels.project(raw, ["wind_dir_last", "temp", "hum"])
        assert list(row) == ["temp", "hum", "wind_dir_last"]

    def test_unwanted_channels_are_dropped(self):
        row = channels.project({"temp": 50.0, "hum": 55.0}, ["hum"])
        assert list(row) == ["hum"]

    def test_missing_and_null_values_become_empty_cells(self):
        row = channels.project({"uv_index": None}, ["uv_index", "solar_rad"])
        assert row == {"uv_index": "", "solar_rad": ""}


class TestUnits:
    def test_unit_depends_on_unit_system(self):
        assert channels.unit_of("dew_point") == "°C"
        assert channels.unit_of("dew_point", metric=False) == "°F"

    def test_unitless_and_unknown_channels_answer_empty(self):
        assert channels.unit_of("rx_state") == ""
        assert channels.unit_of("no_such_channel") == ""

    def test_every_layout_entry_is_unique(self):
        assert len(channels.keys()) == len(set(channels.keys()))
