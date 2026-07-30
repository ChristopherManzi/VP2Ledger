"""One capture cycle end to end, with a faked station."""

from datetime import datetime

from vp2ledger.choice import ChannelChoice
from vp2ledger.ledger import Ledger
from vp2ledger.logbook import Logbook
from vp2ledger.transport import Identity, Sample


class CannedStation:
    """Stands in for a real WeatherLink Live."""

    def __init__(self, sample):
        self.sample = sample
        self.polls = 0

    def poll(self):
        self.polls += 1
        return self.sample


def test_capture_writes_a_converted_row(tmp_path):
    sample = Sample(
        values={"temp": 68.0, "hum": 50.0, "rain_size": 2, "rainfall_daily": 5},
        identity=Identity(device="CAFE", sensor=1, transmitter=1),
    )
    station = CannedStation(sample)
    book = Logbook(
        station=station,
        choice=ChannelChoice(tmp_path / "channels.toml"),
        ledger=Ledger(tmp_path / "out"),
        site="Test bench",
    )

    row = book.capture(datetime(2026, 3, 1, 6, 0))

    assert station.polls == 1
    assert row["temp"] == 20.0          # converted
    assert row["rainfall_daily"] == 1.0  # 5 tips x 0.2 mm
    assert row["wind_speed_last"] == ""  # selected but not delivered
    assert book.ledger.file_for(datetime(2026, 3, 1).date()).is_file()


def test_capture_respects_the_channel_choice(tmp_path):
    sample = Sample(values={"temp": 68.0, "hum": 50.0})
    choice = ChannelChoice(tmp_path / "channels.toml")
    for key in choice.switches:
        choice.switches[key] = key == "hum"
    choice.store()

    book = Logbook(CannedStation(sample), choice, Ledger(tmp_path / "out"))
    row = book.capture(datetime(2026, 3, 1, 6, 0))

    assert list(row) == ["hum"]
