"""Talks to the WeatherLink Live over its local HTTP interface.

``GET http://<host>/v1/current_conditions`` answers with a JSON document
that groups the measurements into one block per sensor group (outdoor
transmitter, indoor console, barometer). :func:`decode` folds those blocks
into a single mapping and keeps the device identifiers apart from the
measurements, because they belong into the header of the CSV file rather
than into a column.

The interface needs no account, no API key and no internet connection - it
runs on the device in the local network, which is why a VPN tunnel is
enough to reach a remote station.
"""

from __future__ import annotations

import http.client
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

#: Path of the read-only endpoint on the device.
ENDPOINT = "/v1/current_conditions"

#: ``data_structure_type`` of the outdoor transmitter block (ISS).
OUTDOOR_BLOCK = 1

#: Keys that describe the block itself instead of the weather.
_STRUCTURAL_KEYS = ("lsid", "txid", "data_structure_type", "did")


class ProbeError(RuntimeError):
    """The station could not be read or refused to answer properly."""


@dataclass(frozen=True)
class Identity:
    """Device identifiers that end up in the header of a daily file."""

    device: Any = ""       # did - serial of the WeatherLink Live
    sensor: Any = ""       # lsid - internal sensor id of the transmitter
    transmitter: Any = ""  # txid - transmitter number of the ISS


@dataclass(frozen=True)
class Sample:
    """One complete reading of the station."""

    values: Mapping[str, Any] = field(default_factory=dict)
    identity: Identity = Identity()


def decode(document: Mapping[str, Any]) -> Sample:
    """Turn one API answer into a :class:`Sample`."""
    complaint = document.get("error")
    if complaint:
        raise ProbeError(f"the station reported an error: {complaint}")

    report = document.get("data") or {}
    blocks = report.get("conditions") or []
    if not blocks:
        raise ProbeError("the station answered without any measurements")

    identity = Identity(device=report.get("did", ""))
    values: dict[str, Any] = {}
    for block in blocks:
        if block.get("data_structure_type") == OUTDOOR_BLOCK:
            identity = Identity(
                device=identity.device,
                sensor=block.get("lsid", ""),
                transmitter=block.get("txid", ""),
            )
        for key, value in block.items():
            # Earlier blocks win, which keeps the outdoor sensor in front of
            # the indoor console for names both of them use.
            values.setdefault(key, value)

    for key in _STRUCTURAL_KEYS:
        values.pop(key, None)
    return Sample(values=values, identity=identity)


class Station:
    """A single WeatherLink Live, addressed by host name or IP."""

    def __init__(self, host: str, port: int = 80, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{ENDPOINT}"

    def poll(self) -> Sample:
        """Fetch and decode the current conditions.

        Raises :class:`ProbeError` for anything that goes wrong on the way -
        unreachable network, timeout, HTTP error, unparsable body.
        """
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            connection.request("GET", ENDPOINT)
            answer = connection.getresponse()
            body = answer.read()
            status = answer.status
        except (OSError, http.client.HTTPException) as cause:
            raise ProbeError(f"no answer from {self.url}: {cause}") from cause
        finally:
            connection.close()

        if status != http.client.OK:
            raise ProbeError(f"{self.url} answered with HTTP status {status}")
        try:
            document = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as cause:
            raise ProbeError(f"{self.url} sent an unreadable answer: {cause}") from cause
        return decode(document)
