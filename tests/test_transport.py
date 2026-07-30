"""Decoding of the station's JSON answer (synthetic documents only)."""

import pytest

from vp2ledger.transport import Identity, ProbeError, decode


def answer(*blocks, did="F00F00F00F00", error=None):
    """Build a synthetic API answer around the given condition blocks."""
    return {"data": {"did": did, "ts": 1234567890, "conditions": list(blocks)}, "error": error}


OUTDOOR = {
    "lsid": 401,
    "data_structure_type": 1,
    "txid": 3,
    "temp": 50.0,
    "hum": 81.0,
    "rain_size": 3,
}
INDOOR = {"lsid": 402, "data_structure_type": 4, "temp_in": 71.2, "hum_in": 40.0}
BAROMETER = {"lsid": 403, "data_structure_type": 3, "bar_sea_level": 29.92}


class TestDecoding:
    def test_blocks_are_merged_into_one_mapping(self):
        sample = decode(answer(OUTDOOR, INDOOR, BAROMETER))
        assert sample.values["temp"] == 50.0
        assert sample.values["hum_in"] == 40.0
        assert sample.values["bar_sea_level"] == 29.92

    def test_identity_comes_from_the_outdoor_block(self):
        sample = decode(answer(OUTDOOR, INDOOR, BAROMETER))
        assert sample.identity == Identity(device="F00F00F00F00", sensor=401, transmitter=3)

    def test_structural_keys_do_not_leak_into_the_values(self):
        sample = decode(answer(OUTDOOR, BAROMETER))
        for key in ("lsid", "txid", "data_structure_type", "did"):
            assert key not in sample.values

    def test_earlier_block_wins_on_duplicate_keys(self):
        first = dict(OUTDOOR)
        shadowing = {"lsid": 9, "data_structure_type": 4, "temp": -999.0}
        sample = decode(answer(first, shadowing))
        assert sample.values["temp"] == 50.0

    def test_outdoor_block_need_not_come_first(self):
        sample = decode(answer(BAROMETER, OUTDOOR))
        assert sample.identity.sensor == 401


class TestComplaints:
    def test_error_field_raises(self):
        with pytest.raises(ProbeError):
            decode({"data": None, "error": {"code": 500, "message": "boom"}})

    def test_missing_conditions_raise(self):
        with pytest.raises(ProbeError):
            decode(answer())  # no blocks at all

    def test_data_may_be_null(self):
        with pytest.raises(ProbeError):
            decode({"data": None, "error": None})
