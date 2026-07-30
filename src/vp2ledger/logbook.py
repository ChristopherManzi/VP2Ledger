"""Ties station, channel choice and ledger together.

:meth:`Logbook.capture` is exactly one measuring cycle: poll the station,
project the reading onto the chosen channels, append the row. The module
also contains the endless loop for unattended 24/7 operation.

Using the parts from your own script::

    from vp2ledger import ChannelChoice, Ledger, Logbook, Station

    book = Logbook(
        station=Station("192.0.2.1"),  # your station's address
        choice=ChannelChoice("channels.toml"),
        ledger=Ledger("."),
        site="My site",
    )
    book.capture()
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from . import channels
from .choice import ChannelChoice
from .ledger import Ledger
from .transport import ProbeError, Station

_logger = logging.getLogger(__name__)

# The device documentation allows continuous polling of the HTTP interface
# down to a 10 second spacing ("as often as every 10 seconds"); anything
# faster is only available via the UDP broadcast, which this program does
# not use. The upper bound of one hour guards against typos that would
# otherwise punch day-long holes into the record.
PACE_FLOOR = 10
PACE_CEILING = 3600


class Logbook:
    """One measuring setup: a station, a channel choice and a ledger."""

    def __init__(
        self,
        station: Station,
        choice: ChannelChoice,
        ledger: Ledger,
        site: str = "",
        metric: bool = True,
    ):
        self.station = station
        self.choice = choice
        self.ledger = ledger
        self.site = site
        self.metric = metric

    def capture(self, moment: datetime | None = None) -> dict[str, Any]:
        """One measuring cycle; returns the row that was written."""
        sample = self.station.poll()
        row = channels.project(sample.values, self.choice.active(), self.metric)
        self.ledger.append(moment or datetime.now(), row, self.site, sample.identity)
        return row


def keep_logging(book: Logbook, pace_s: float) -> None:
    """Capture forever, one reading every ``pace_s`` seconds, until Ctrl+C.

    A single failed reading (VPN down, station rebooting, disk hiccup)
    is logged and skipped - the loop itself carries on.
    """
    _logger.info(
        "logging every %.0f s, %d channels selected",
        pace_s, len(book.choice.active()),
    )
    try:
        while True:
            began = time.monotonic()
            try:
                book.capture()
            except ProbeError as trouble:
                _logger.warning("reading skipped: %s", trouble)
            except OSError:
                _logger.exception("could not write to the ledger")

            # Subtract the time the reading took so the pace stays steady.
            remaining = pace_s - (time.monotonic() - began)
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        _logger.info("logging stopped")
