"""Which channels get recorded - stored in a small TOML file.

The file (default name: ``channels.toml``) holds one ``true``/``false``
line per channel and can be edited with any text editor. It is created on
first use with every channel switched on; when a newer program version
brings additional channels they are merged in without losing the user's
own choices.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from .channels import LAYOUT

TABLE = "channels"

_PREAMBLE = (
    "# Channel choice for VP2Ledger\n"
    "# true  = channel is recorded\n"
    "# false = channel is skipped\n"
)


class ChannelChoice:
    """On/off switch per channel, persisted as TOML."""

    def __init__(self, location: str | os.PathLike):
        self.location = Path(location)
        self.switches: dict[str, bool] = {}
        self.reload()

    def reload(self) -> None:
        """Read the file (if any) and merge it with the channel table."""
        recorded_on_disk: dict = {}
        if self.location.is_file():
            with self.location.open("rb") as handle:
                recorded_on_disk = tomllib.load(handle).get(TABLE, {})

        self.switches = {
            channel.key: bool(recorded_on_disk.get(channel.key, True))
            for channel in LAYOUT
        }
        # First start, or new channels appeared: bring the file up to date.
        if recorded_on_disk.keys() != self.switches.keys():
            self.store()

    def store(self) -> None:
        lines = [_PREAMBLE, f"[{TABLE}]"]
        for channel in LAYOUT:
            note = f"{channel.caption} [{channel.metric_unit}]".strip()
            state = "true" if self.switches[channel.key] else "false"
            lines.append(f"{channel.key} = {state}  # {note}")
        self.location.parent.mkdir(parents=True, exist_ok=True)
        self.location.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def active(self) -> list[str]:
        """Keys of all switched-on channels, in column order."""
        return [channel.key for channel in LAYOUT if self.switches[channel.key]]

    def is_active(self, key: str) -> bool:
        return self.switches.get(key, False)

    def switch(self, key: str, on: bool) -> None:
        """Flip one channel and persist the change."""
        if key not in self.switches:
            raise KeyError(f"no such channel: {key}")
        self.switches[key] = bool(on)
        self.store()
