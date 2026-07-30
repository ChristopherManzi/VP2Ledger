"""Day-by-day CSV ledger: <root>/YYYY/MM/YYYY-MM-DD.csv.

Every daily file starts with a small header block (site name and the
device identifiers), a blank line and a caption row in which each cell
holds the channel key plus its unit, separated by a line break. After
that, one row per reading.

Robustness rules:

* The file is opened, appended to and closed again for every single row,
  so a crash or reboot can never leave a corrupt file behind.
* While a row is written the file is locked, allowing several processes
  to feed the same daily file without shredding each other's rows.
* Once a daily file exists, its caption row is authoritative: if the
  program is restarted during the day with a different channel choice,
  the existing columns stay as they are (missing values become empty
  cells) and newly chosen channels only appear from the next day on.
  That way every file is consistent from the first to the last row.
"""

from __future__ import annotations

import csv
import io
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from .channels import unit_of
from .transport import Identity

_logger = logging.getLogger(__name__)

STAMP_PATTERN = "%Y.%m.%d %H:%M:%S"
STAMP_CAPTION = "Date & Time\n[YYYY.MM.DD hh:mm:ss]"

#: Labels of the header block, in file order.
_HEADER_LABELS = ("Site", "Device ID", "Internal sensor ID", "ISS transmitter number")


def _hold(handle: io.IOBase) -> None:
    """Take an exclusive lock on the open file (blocks until granted)."""
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _release(handle: io.IOBase) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def render_cell(value: Any, decimal_mark: str) -> str:
    """Text form of one value, floats with the configured decimal mark."""
    if isinstance(value, float) and decimal_mark != ".":
        return str(value).replace(".", decimal_mark)
    return str(value)


class Ledger:
    """Appends readings to daily CSV files below a root directory."""

    def __init__(
        self,
        root: str | os.PathLike,
        metric: bool = True,
        column_mark: str = ";",
        decimal_mark: str = ",",
    ):
        self.root = Path(root)
        self.metric = metric
        self.column_mark = column_mark
        self.decimal_mark = decimal_mark
        self._already_reported: set[str] = set()

    def file_for(self, day: date) -> Path:
        """Location of the daily file for the given day."""
        return self.root / f"{day:%Y}" / f"{day:%m}" / f"{day:%Y-%m-%d}.csv"

    def append(
        self,
        moment: datetime,
        row: Mapping[str, Any],
        site: str = "",
        identity: Identity = Identity(),
    ) -> Path:
        """Add one reading to the daily file, creating the file if needed.

        For a brand-new file the keys of ``row`` define the columns; for an
        existing file the caption row inside the file defines them.
        """
        target = self.file_for(moment.date())
        target.parent.mkdir(parents=True, exist_ok=True)

        # "a+" creates the file when missing and lets us read the caption row.
        with target.open("a+", encoding="utf-8", newline="") as handle:
            _hold(handle)
            try:
                handle.seek(0, os.SEEK_END)
                fresh = handle.tell() == 0
                if fresh:
                    columns = list(row)
                    self._start_file(handle, columns, site, identity)
                else:
                    columns = self._columns_of(handle)
                    self._report_unknown(row, columns, target)
                    handle.seek(0, os.SEEK_END)

                cells = [moment.strftime(STAMP_PATTERN)]
                cells += [
                    render_cell(row[name], self.decimal_mark) if name in row else ""
                    for name in columns
                ]
                csv.writer(handle, delimiter=self.column_mark).writerow(cells)
                handle.flush()
            finally:
                _release(handle)
        return target

    def _start_file(self, handle, columns: list[str], site: str, identity: Identity) -> None:
        """Header block, blank line and caption row of a new daily file."""
        writer = csv.writer(handle, delimiter=self.column_mark)
        width = len(columns) + 1  # plus the timestamp column
        padding = [""] * (width - 2)
        for label, content in zip(
            _HEADER_LABELS,
            (site, identity.device, identity.sensor, identity.transmitter),
        ):
            writer.writerow([label, content, *padding])
        writer.writerow([""] * width)

        captions = [STAMP_CAPTION]
        for name in columns:
            unit = unit_of(name, self.metric)
            captions.append(f"{name}\n[{unit}]" if unit else name)
        writer.writerow(captions)

    def _columns_of(self, handle) -> list[str]:
        """Column names of an existing file, read from its caption row."""
        handle.seek(0)
        for cells in csv.reader(handle, delimiter=self.column_mark):
            if cells and cells[0].startswith("Date & Time"):
                # Cell layout is "<key>\n[<unit>]" - only the key matters here.
                return [cell.partition("\n")[0].strip() for cell in cells[1:]]
        return []

    def _report_unknown(self, row: Mapping[str, Any], columns: list[str], target: Path) -> None:
        """Warn once per channel that is recorded but not in the file."""
        for name in row:
            if name not in columns and name not in self._already_reported:
                self._already_reported.add(name)
                _logger.warning(
                    "channel '%s' is selected but %s has no such column; "
                    "it will only be recorded from tomorrow's file on",
                    name, target.name,
                )
