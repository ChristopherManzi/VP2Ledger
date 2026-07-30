"""Daily CSV files: layout, header block, restart and multi-writer rules."""

import csv
from datetime import datetime

import pytest

from vp2ledger.ledger import Ledger, render_cell
from vp2ledger.transport import Identity

WHO = Identity(device="0011AABB", sensor=77, transmitter=2)


def rows_of(path, delimiter=";"):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle, delimiter=delimiter))


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path)


def test_files_are_nested_year_month_day(ledger, tmp_path):
    written = ledger.append(datetime(2026, 1, 5, 8, 30), {"temp": 3.0}, "Roof", WHO)
    assert written == tmp_path / "2026" / "01" / "2026-01-05.csv"


def test_header_block_carries_site_and_identity(ledger):
    path = ledger.append(datetime(2026, 1, 5, 8, 30), {"temp": 3.0, "hum": 80.0}, "Roof", WHO)
    rows = rows_of(path)
    assert rows[0][:2] == ["Site", "Roof"]
    assert rows[1][:2] == ["Device ID", "0011AABB"]
    assert rows[2][:2] == ["Internal sensor ID", "77"]
    assert rows[3][:2] == ["ISS transmitter number", "2"]
    assert rows[4] == [""] * 3  # blank separator line, full width
    assert rows[5] == ["Date & Time\n[YYYY.MM.DD hh:mm:ss]", "temp\n[°C]", "hum\n[% RH]"]


def test_reading_rows_use_stamp_and_decimal_mark(ledger):
    path = ledger.append(datetime(2026, 1, 5, 8, 30, 15), {"temp": 3.4, "hum": 80.0}, "Roof", WHO)
    assert rows_of(path)[6] == ["2026.01.05 08:30:15", "3,4", "80,0"]


def test_native_units_appear_in_captions(tmp_path):
    ledger = Ledger(tmp_path, metric=False)
    path = ledger.append(datetime(2026, 1, 5, 9, 0), {"bar_absolute": 29.9}, "Roof", WHO)
    assert rows_of(path)[5][1] == "bar_absolute\n[inHg]"


def test_custom_marks_survive_the_append_path(tmp_path):
    """Second write must parse the caption row with the custom column mark."""
    ledger = Ledger(tmp_path, column_mark="|", decimal_mark=".")
    ledger.append(datetime(2026, 1, 5, 9, 0), {"temp": 3.4}, "Roof", WHO)
    path = ledger.append(datetime(2026, 1, 5, 9, 1), {"temp": 3.5}, "Roof", WHO)
    rows = rows_of(path, delimiter="|")
    assert rows[6] == ["2026.01.05 09:00:00", "3.4"]
    assert rows[7] == ["2026.01.05 09:01:00", "3.5"]


def test_existing_caption_row_pins_the_columns(ledger, caplog):
    """A restart with a different channel choice must not reshape the file."""
    ledger.append(datetime(2026, 1, 5, 9, 0), {"temp": 3.4, "hum": 80.0}, "Roof", WHO)

    revised = Ledger(ledger.root)  # fresh instance, as after a restart
    path = revised.append(
        datetime(2026, 1, 5, 9, 1), {"temp": 3.5, "uv_index": 1.0}, "Roof", WHO
    )

    rows = rows_of(path)
    assert rows[5][1:] == ["temp\n[°C]", "hum\n[% RH]"]        # unchanged
    assert rows[7] == ["2026.01.05 09:01:00", "3,5", ""]       # hum empty
    assert "uv_index" in caplog.text                           # dropped channel is reported


def test_midnight_rolls_over_to_a_fresh_file(ledger):
    before = ledger.append(datetime(2026, 1, 5, 23, 59), {"temp": 1.0}, "Roof", WHO)
    after = ledger.append(datetime(2026, 1, 6, 0, 0), {"temp": 1.0, "hum": 90.0}, "Roof", WHO)
    assert before != after
    assert rows_of(after)[5][1:] == ["temp\n[°C]", "hum\n[% RH]"]  # new choice applies now


def test_two_ledgers_can_share_one_file(tmp_path):
    """Simulates two processes appending to the same daily file."""
    one, two = Ledger(tmp_path), Ledger(tmp_path)
    for minute in range(4):
        one.append(datetime(2026, 1, 5, 12, minute, 0), {"temp": float(minute)}, "Roof", WHO)
        two.append(datetime(2026, 1, 5, 12, minute, 30), {"temp": minute + 0.5}, "Roof", WHO)

    rows = rows_of(one.file_for(datetime(2026, 1, 5).date()))
    assert len(rows) == 6 + 8
    assert all(len(row) == 2 for row in rows[6:])


class TestRenderCell:
    def test_floats_get_the_decimal_mark(self):
        assert render_cell(3.4, ",") == "3,4"

    def test_dot_mark_needs_no_replacement(self):
        assert render_cell(3.4, ".") == "3.4"

    def test_integers_and_text_pass_through(self):
        assert render_cell(7, ",") == "7"
        assert render_cell("n/a", ",") == "n/a"
