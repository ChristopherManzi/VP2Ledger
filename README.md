# VP2Ledger

An unattended CSV logger for a Davis Vantage Pro 2 weather station connected through a
WeatherLink Live hub. It polls the station's local HTTP interface at a configurable
pace, converts the readings to metric units (°C, km/h, hPa, mm) and appends them to
one CSV file per day.

A Vantage Vue on the same hub exposes the identical local API and works just as well.

## What it does

- **One file per day** — output is written to `<output folder>\2026\07\2026-07-30.csv`,
  and a fresh file is started automatically at midnight
- **Built for 24/7 operation** — restarts, crashes and even several instances running
  at the same time cannot corrupt the daily files
- **Metric by default** — the local API answers in US units; VP2Ledger converts unless
  `--raw-units` is given
- **Works across a VPN** — the poll pace ranges from 10 s to 3600 s
- **Selectable channels** — a plain `channels.toml` decides what is recorded
- **Standard library only** — no `pip install` step, no accounts, no API keys
- **Optional control panel** — everything the command line offers, in one window

## Requirements

| | |
|---|---|
| Runtime | Python 3.11 or newer ([python.org](https://www.python.org/downloads/) — tick "Add python.exe to PATH") |
| Dependencies | none, the Python standard library is enough |
| Hardware | Davis Vantage Pro 2 or Vantage Vue behind a WeatherLink Live hub |

## Getting started

Copy the `vp2ledger` folder (found under `src\` in this repository) anywhere you like,
for example `C:\WeatherData\vp2ledger\`. Then change into the folder that *contains*
it and take one test reading:

```bash
cd C:\WeatherData
```

```bash
python -m vp2ledger --host <station-ip> --single
```

`<station-ip>` is the address of your WeatherLink Live in the local network; its
display or your router will tell you.

## Usage

```bash
python -m vp2ledger --host <station-ip> --single
```

```bash
python -m vp2ledger --host <station-ip>
```

```bash
python -m vp2ledger --panel
```

The three forms take one reading and print it, run unattended at one reading every
60 s, and open the graphical control panel. Stop the unattended mode with **Ctrl+C**,
or with **Stop** in the control panel.

### Command line options

Except for `--host`, every option is optional and they can be combined freely.

| Option | Meaning | Default |
|---|---|---|
| `--host 192.0.2.10` | address of the WeatherLink Live (required unless `--panel`) | — |
| `--site "Roof east"` | site name written into the header of every daily file | empty |
| `-p 30` / `--pace 30` | seconds between readings (allowed: 10 to 3600) | 60 |
| `-o D:\Data` / `--out D:\Data` | folder the daily CSV files go into | current folder |
| `--raw-units` | store the station's raw US values (°F, mph, inHg, counts) instead of converting | metric |
| `--column-mark ","` | CSV column separator | `;` |
| `--decimal-mark "."` | decimal mark for fractional numbers | `,` |
| `--single` | take one reading, print it, exit | off |
| `--panel` | open the graphical control panel | off |
| `-h` / `--help` | show the built-in help | |

Examples:

```bash
python -m vp2ledger --host <station-ip> -p 30 -o D:\WeatherData
```

```bash
python -m vp2ledger --host <station-ip> --site "Roof east" --raw-units
```

### The control panel

`--panel` opens a window in which everything can be configured without touching the
command line: site name, station address, pace, output folder, unit handling (convert
or raw), CSV column and decimal marks, and a checkbox list of the channels to record
(ticked = recorded).

- **Start logging / Stop** — unattended mode on and off
- **Test reading** — one single reading with a success or failure dialog

Starting the logging stores all settings; they are loaded again the next time the
panel opens.

## Output format

Every daily file begins with a short info block (site name, device id, sensor id,
transmitter number), followed by the caption row (channel key + unit) and the reading
rows with a `YYYY.MM.DD hh:mm:ss` timestamp.

These files appear in the working folder, or in the folder given with `-o`:

| File | Purpose |
|---|---|
| `2026\07\2026-07-30.csv` etc. | the recorded data, one file per day |
| `channels.toml` | which channels are recorded (`true`/`false` per channel, each line commented with a description — editable with any text editor) |
| `vp2ledger_settings.json` | the control panel's stored settings |

## Notes on the WeatherLink Live interface

- **Polling pace** — according to the documentation the local HTTP interface tolerates
  continuous polling down to 10 seconds, which is why that is the lower limit. Faster
  data (every 2.5 s) would require the device's UDP broadcast, which is not needed
  here.
- **Units** — the local API always answers in US units (°F, mph, inHg, rain as
  bucket-tip counts), even when the console or app is set to metric; that setting only
  affects the display there.
- **Cost** — the local API runs on your own device inside your own network, without
  accounts, API keys or fees. Only Davis' extended cloud access (WeatherLink
  subscriptions, e.g. for historical data through the v2 cloud API) costs money, and
  VP2Ledger does not use it.

## Troubleshooting

**"error: no answer from …"** — the station cannot be reached over the network. Check
whether the VPN or LAN connection is up and the address is correct. A quick browser
test: `http://<station address>/v1/current_conditions` must show JSON data.

**Changing site name or station address** — pass `--site` and `--host` on the command
line, or type them into the fields of the control panel, which remembers them.

**Excluding individual channels** — set the channel to `false` in `channels.toml`, or
untick it in the panel. Changed columns take effect with the *next* daily file; a file
that already exists today keeps its columns, so every file stays internally
consistent.

**Several instances at once** — supported. The daily file is locked per row, so
parallel instances append cleanly to the same file; each reading then appears once per
instance.

## Development

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -e .[dev]
```

```bash
pytest
```

**Layout:**

```text
src/vp2ledger/
├── __main__.py     command line options and constants (site, address)
├── transport.py    HTTP access to the station + JSON decoding
├── channels.py     channel table: keys, captions, units, conversions
├── choice.py       persisted channel on/off switches (channels.toml)
├── ledger.py       daily CSV files, lock-protected appends
├── logbook.py      one capture cycle + the unattended loop
└── panel.py        graphical control panel (tkinter)
```

## License

Copyright © Christopher Manzi 2026. All rights reserved.
