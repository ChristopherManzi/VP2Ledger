"""Command line entry point: ``python -m vp2ledger``.

The station address is given with ``--host`` (or typed into the control
panel); pace and output folder are further command line options.
"""

from __future__ import annotations

import argparse
import logging
import sys

from .choice import ChannelChoice
from .ledger import Ledger
from .logbook import PACE_CEILING, PACE_FLOOR, Logbook, keep_logging
from .transport import ProbeError, Station


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vp2ledger",
        description=(
            "Records a Davis Vantage Pro 2 weather station (WeatherLink Live) "
            "into daily CSV files."
        ),
    )
    parser.add_argument(
        "--host", default="", metavar="ADDRESS",
        help="IP address or host name of the WeatherLink Live (required unless --panel)",
    )
    parser.add_argument(
        "--site", default="", metavar="NAME",
        help="site name written into the header of every daily file",
    )
    parser.add_argument(
        "-p", "--pace", type=float, default=60, metavar="SECONDS",
        help=f"seconds between readings, {PACE_FLOOR}-{PACE_CEILING} (default: 60)",
    )
    parser.add_argument(
        "-o", "--out", default=".", metavar="FOLDER",
        help="folder the daily CSV files go into (default: current folder)",
    )
    parser.add_argument(
        "--raw-units", action="store_true",
        help="keep the station's US units (°F, mph, inHg, counts) instead of converting",
    )
    parser.add_argument(
        "--column-mark", default=";", metavar="CHAR",
        help="CSV column separator (default: ;)",
    )
    parser.add_argument(
        "--decimal-mark", default=",", metavar="CHAR",
        help="decimal mark for fractional numbers (default: ,)",
    )
    parser.add_argument(
        "--single", action="store_true",
        help="take one reading, print it and exit (good for a first test)",
    )
    parser.add_argument(
        "--panel", action="store_true",
        help="open the graphical control panel",
    )
    return parser


def main() -> None:
    options = build_parser().parse_args()

    if options.panel:
        from .panel import open_panel

        open_panel(options.site, options.host)
        return

    if not options.host:
        sys.exit("error: please give the station address with --host (see --help)")
    if not PACE_FLOOR <= options.pace <= PACE_CEILING:
        sys.exit(
            f"error: a pace of {options.pace:g} s is outside the allowed "
            f"range of {PACE_FLOOR}-{PACE_CEILING} seconds"
        )
    if len(options.column_mark) != 1 or len(options.decimal_mark) != 1:
        sys.exit("error: column and decimal mark must be exactly one character each")
    if options.column_mark == options.decimal_mark:
        sys.exit("error: column and decimal mark must differ")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    metric = not options.raw_units
    book = Logbook(
        station=Station(options.host),
        choice=ChannelChoice("channels.toml"),
        ledger=Ledger(
            options.out, metric=metric,
            column_mark=options.column_mark, decimal_mark=options.decimal_mark,
        ),
        site=options.site,
        metric=metric,
    )

    if options.single:
        try:
            row = book.capture()
        except ProbeError as trouble:
            sys.exit(f"error: {trouble}")
        for key, value in row.items():
            print(f"{key} = {value}")
    else:
        keep_logging(book, options.pace)


if __name__ == "__main__":
    main()
