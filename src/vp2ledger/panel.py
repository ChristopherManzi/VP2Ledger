"""Graphical control panel (tkinter).

Launch with ``python -m vp2ledger --panel``. All settings live in
``vp2ledger_settings.json`` next to the working directory and are loaded
again on the next start. The channel choice is shared with the command
line through ``channels.toml``, so both frontends always agree on what is
recorded.
"""

from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .channels import LAYOUT
from .choice import ChannelChoice
from .ledger import Ledger
from .logbook import PACE_CEILING, PACE_FLOOR, Logbook
from .transport import ProbeError, Station

SETTINGS_FILE = "vp2ledger_settings.json"


def read_settings(location: str | Path = SETTINGS_FILE) -> dict:
    """Stored settings, or an empty dict when there are none (yet)."""
    try:
        return json.loads(Path(location).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_settings(settings: dict, location: str | Path = SETTINGS_FILE) -> None:
    Path(location).write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


class ControlPanel:
    """Main window with settings, channel checkboxes and start/stop."""

    def __init__(self, site: str, host: str):
        stored = read_settings()
        self.choice = ChannelChoice("channels.toml")
        self.worker: threading.Thread | None = None
        self.halt = threading.Event()
        self.headline = "Ready."

        self.window = tk.Tk()
        self.window.title("VP2Ledger")
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        body = ttk.Frame(self.window, padding=12)
        body.grid(sticky="nsew")
        body.columnconfigure(1, weight=1)

        # -- settings entries, prefilled from the stored settings ----------
        self.site = tk.StringVar(value=stored.get("site", site))
        self.host = tk.StringVar(value=stored.get("host", host))
        self.pace = tk.StringVar(value=str(stored.get("pace", 60)))
        self.folder = tk.StringVar(value=stored.get("folder", "."))
        self.metric = tk.BooleanVar(value=stored.get("metric", True))
        self.column_mark = tk.StringVar(value=stored.get("column_mark", ";"))
        self.decimal_mark = tk.StringVar(value=stored.get("decimal_mark", ","))

        def labelled(row: int, caption: str) -> None:
            ttk.Label(body, text=caption).grid(row=row, column=0, sticky="w", pady=2)

        labelled(0, "Site name:")
        ttk.Entry(body, textvariable=self.site).grid(row=0, column=1, columnspan=2, sticky="ew")
        labelled(1, "Station address (IP):")
        ttk.Entry(body, textvariable=self.host).grid(row=1, column=1, columnspan=2, sticky="ew")
        labelled(2, "Pace (seconds):")
        ttk.Entry(body, textvariable=self.pace, width=8).grid(row=2, column=1, sticky="w")
        labelled(3, "Output folder:")
        ttk.Entry(body, textvariable=self.folder).grid(row=3, column=1, sticky="ew")
        ttk.Button(body, text="Browse", command=self.pick_folder).grid(row=3, column=2, padx=(4, 0))

        labelled(4, "Units:")
        ttk.Checkbutton(
            body,
            text="convert to metric (°C, km/h, hPa, mm) - untick for raw US units",
            variable=self.metric,
        ).grid(row=4, column=1, columnspan=2, sticky="w")

        labelled(5, "CSV column / decimal mark:")
        marks = ttk.Frame(body)
        marks.grid(row=5, column=1, columnspan=2, sticky="w")
        ttk.Entry(marks, textvariable=self.column_mark, width=3).pack(side="left")
        ttk.Entry(marks, textvariable=self.decimal_mark, width=3).pack(side="left", padx=(8, 0))

        # -- channel checkboxes in a scrollable area -----------------------
        ttk.Label(body, text="Channels to record:").grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(8, 2)
        )
        holder = ttk.Frame(body, borderwidth=1, relief="sunken")
        holder.grid(row=7, column=0, columnspan=3, sticky="nsew")
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)
        body.rowconfigure(7, weight=1)

        canvas = tk.Canvas(holder, height=260, highlightthickness=0)
        slider = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=slider.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        slider.grid(row=0, column=1, sticky="ns")

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind_all(
            "<MouseWheel>",
            lambda event: canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"),
        )

        self.ticks: dict[str, tk.BooleanVar] = {}
        for channel in LAYOUT:
            var = tk.BooleanVar(value=self.choice.is_active(channel.key))
            self.ticks[channel.key] = var
            ttk.Checkbutton(
                inner, text=f"{channel.key} - {channel.caption}", variable=var
            ).pack(anchor="w")

        # -- buttons and status line ---------------------------------------
        buttons = ttk.Frame(body)
        buttons.grid(row=8, column=0, columnspan=3, pady=(10, 4))
        self.go = ttk.Button(buttons, text="Start logging", command=self.start)
        self.go.pack(side="left", padx=4)
        self.stop = ttk.Button(buttons, text="Stop", command=self.request_stop, state="disabled")
        self.stop.pack(side="left", padx=4)
        self.probe = ttk.Button(buttons, text="Test reading", command=self.test_reading)
        self.probe.pack(side="left", padx=4)

        self.footer = ttk.Label(body, text=self.headline, relief="groove", anchor="w")
        self.footer.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(4, 0))

        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._refresh()

    # -- helpers -----------------------------------------------------------

    def pick_folder(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.folder.get() or ".")
        if chosen:
            self.folder.set(chosen)

    def _complain(self, message: str) -> None:
        messagebox.showerror("Check your input", message)

    def _assemble(self) -> tuple[Logbook, float] | None:
        """Validate the inputs, persist them, build a ready-to-run Logbook."""
        try:
            pace = float(self.pace.get().replace(",", "."))
        except ValueError:
            self._complain("The pace must be a number of seconds.")
            return None
        if not PACE_FLOOR <= pace <= PACE_CEILING:
            self._complain(f"The pace must lie between {PACE_FLOOR} and {PACE_CEILING} seconds.")
            return None
        host = self.host.get().strip()
        if not host:
            self._complain("Please enter the address of the WeatherLink Live.")
            return None
        column_mark = self.column_mark.get()
        decimal_mark = self.decimal_mark.get()
        if len(column_mark) != 1 or len(decimal_mark) != 1:
            self._complain("Column and decimal mark must be exactly one character each.")
            return None
        if column_mark == decimal_mark:
            self._complain("Column and decimal mark must differ.")
            return None

        for key, var in self.ticks.items():
            self.choice.switches[key] = var.get()
        self.choice.store()

        write_settings({
            "site": self.site.get(),
            "host": host,
            "pace": pace,
            "folder": self.folder.get() or ".",
            "metric": self.metric.get(),
            "column_mark": column_mark,
            "decimal_mark": decimal_mark,
        })

        book = Logbook(
            station=Station(host),
            choice=self.choice,
            ledger=Ledger(
                self.folder.get() or ".",
                metric=self.metric.get(),
                column_mark=column_mark,
                decimal_mark=decimal_mark,
            ),
            site=self.site.get(),
            metric=self.metric.get(),
        )
        return book, pace

    # -- actions -----------------------------------------------------------

    def start(self) -> None:
        assembled = self._assemble()
        if assembled is None:
            return
        book, pace = assembled
        self.halt.clear()
        self.worker = threading.Thread(target=self._grind, args=(book, pace), daemon=True)
        self.worker.start()
        self.headline = "Logging ..."

    def request_stop(self) -> None:
        self.halt.set()
        self.headline = "Stopping ..."

    def test_reading(self) -> None:
        assembled = self._assemble()
        if assembled is None:
            return
        book, _ = assembled
        try:
            row = book.capture()
        except ProbeError as trouble:
            messagebox.showerror("Test reading", str(trouble))
            return
        filled = sum(1 for value in row.values() if value != "")
        messagebox.showinfo("Test reading", f"Success - {filled} values written.")

    def _grind(self, book: Logbook, pace: float) -> None:
        """Worker thread: capture at the configured pace until halted."""
        while not self.halt.is_set():
            began = time.monotonic()
            try:
                book.capture()
                self.headline = "Last reading at " + time.strftime("%H:%M:%S")
            except ProbeError:
                self.headline = "Station unreachable (" + time.strftime("%H:%M:%S") + ")"
            except OSError as trouble:
                self.headline = f"Write failed: {trouble}"
            remaining = pace - (time.monotonic() - began)
            if remaining > 0:
                self.halt.wait(remaining)
        self.headline = "Stopped."

    def _refresh(self) -> None:
        """Periodic UI update: status line and button states."""
        self.footer.config(text=self.headline)
        busy = self.worker is not None and self.worker.is_alive()
        for button in (self.go, self.probe):
            button.config(state="disabled" if busy else "normal")
        self.stop.config(state="normal" if busy else "disabled")
        self._timer = self.window.after(400, self._refresh)

    def close(self) -> None:
        self.halt.set()
        self.window.after_cancel(self._timer)
        self.window.destroy()

    def run(self) -> None:
        self.window.mainloop()


def open_panel(site: str, host: str) -> None:
    ControlPanel(site, host).run()
