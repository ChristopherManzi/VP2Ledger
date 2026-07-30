"""Channel table of everything a WeatherLink Live reports.

The local HTTP interface always answers in US units, no matter what the
console or the phone app is set to - that setting only changes the display
there. Rainfall arrives as bucket tips instead of a length; how much a
single tip is worth is announced by the ``rain_size`` channel.

Rather than attaching a converter to every single channel, each channel
only declares *which physical quantity* its raw number carries. The
conversion into SI units is then looked up once per quantity, which keeps
the table below purely descriptive.

The tuple order below is the column order of the exported CSV and the unit
strings are the ones the output format asks for, so neither may be
reshuffled or translated.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Iterable, Mapping, NamedTuple


class Quantity(Enum):
    """What kind of number a raw channel value is."""

    PLAIN = "plain"                    # already usable, no conversion
    FAHRENHEIT = "fahrenheit"          # -> degrees Celsius
    MILES_PER_HOUR = "miles_per_hour"  # -> kilometres per hour
    INCHES_MERCURY = "inches_mercury"  # -> hectopascal
    TIP_COUNT = "tip_count"            # bucket tips -> millimetres
    TIP_CODE = "tip_code"              # gauge code -> millimetres per tip


#: Gauge resolution code announced by the station -> millimetres per tip.
TIP_MILLIMETRES = {1: 0.254, 2: 0.2, 3: 0.1, 4: 0.0254}

#: Channel that carries the gauge resolution code.
RESOLUTION_CHANNEL = "rain_size"


class Channel(NamedTuple):
    """One recordable value."""

    key: str            # name used by the station's API and as CSV column
    caption: str        # human readable description
    quantity: Quantity  # how to convert the raw number
    native_unit: str    # unit as delivered by the station
    metric_unit: str    # unit after conversion


LAYOUT: tuple[Channel, ...] = (
    Channel("temp", "Air temperature", Quantity.FAHRENHEIT, "°F", "°C"),
    Channel("hum", "Relative humidity", Quantity.PLAIN, "% RH", "% RH"),
    Channel("bar_absolute", "Absolute barometric pressure", Quantity.INCHES_MERCURY, "inHg", "hPa"),
    Channel("solar_rad", "Solar irradiance (global radiation)", Quantity.PLAIN, "W/m²", "W/m²"),
    Channel("wind_speed_last", "Wind speed", Quantity.MILES_PER_HOUR, "mph", "km/h"),
    Channel("wind_dir_last", "Wind direction", Quantity.PLAIN, "°", "°"),
    Channel("rain_rate_last", "Current rainfall intensity", Quantity.TIP_COUNT, "Counts/h", "mm/h"),
    Channel("dew_point", "Dew point", Quantity.FAHRENHEIT, "°F", "°C"),
    Channel("wet_bulb", "Wet bulb temperature", Quantity.FAHRENHEIT, "°F", "°C"),
    Channel("heat_index", "Apparent temperature in heat", Quantity.FAHRENHEIT, "°F", "°C"),
    Channel("wind_chill", "Apparent temperature in wind", Quantity.FAHRENHEIT, "°F", "°C"),
    # The two indices below are derived from °F and are converted along with
    # the temperatures, but the output format labels them "Index".
    Channel("thw_index", "Temperature humidity wind index", Quantity.FAHRENHEIT, "Index", "Index"),
    Channel("thsw_index", "Temperature humidity sun wind index", Quantity.FAHRENHEIT, "Index", "Index"),
    Channel("uv_index", "UV index", Quantity.PLAIN, "Index", "Index"),
    Channel("bar_sea_level", "Pressure reduced to sea level", Quantity.INCHES_MERCURY, "inHg", "hPa"),
    Channel("bar_trend", "Pressure trend", Quantity.INCHES_MERCURY, "inHg", "hPa/3 h"),
    Channel("wind_speed_avg_last_1_min", "Mean wind speed over the last minute", Quantity.MILES_PER_HOUR, "mph", "km/h"),
    Channel("wind_dir_scalar_avg_last_1_min", "Scalar mean wind direction over the last minute", Quantity.PLAIN, "°", "°"),
    Channel("wind_speed_avg_last_2_min", "Mean wind speed over the last 2 minutes", Quantity.MILES_PER_HOUR, "mph", "km/h"),
    Channel("wind_dir_scalar_avg_last_2_min", "Scalar mean wind direction over the last 2 minutes", Quantity.PLAIN, "°", "°"),
    Channel("wind_speed_hi_last_2_min", "Peak wind speed over the last 2 minutes", Quantity.MILES_PER_HOUR, "mph", "km/h"),
    Channel("wind_dir_at_hi_speed_last_2_min", "Wind direction at the peak speed (2 min)", Quantity.PLAIN, "°", "°"),
    Channel("wind_speed_avg_last_10_min", "Mean wind speed over the last 10 minutes", Quantity.MILES_PER_HOUR, "mph", "km/h"),
    Channel("wind_dir_scalar_avg_last_10_min", "Scalar mean wind direction over the last 10 minutes", Quantity.PLAIN, "°", "°"),
    Channel("wind_speed_hi_last_10_min", "Peak wind speed over the last 10 minutes", Quantity.MILES_PER_HOUR, "mph", "km/h"),
    Channel("wind_dir_at_hi_speed_last_10_min", "Wind direction at the peak speed (10 min)", Quantity.PLAIN, "°", "°"),
    Channel("rain_rate_hi", "Peak rainfall intensity since midnight", Quantity.TIP_COUNT, "Counts/h", "mm/h"),
    Channel("rainfall_last_15_min", "Rainfall over the last 15 minutes", Quantity.TIP_COUNT, "Counts", "mm"),
    Channel("rain_rate_hi_last_15_min", "Peak rainfall intensity within the last 15 minutes", Quantity.TIP_COUNT, "Counts/h", "mm/h"),
    Channel("rainfall_last_60_min", "Rainfall over the last hour", Quantity.TIP_COUNT, "Counts", "mm"),
    Channel("rainfall_last_24_hr", "Rainfall over the last 24 hours", Quantity.TIP_COUNT, "Counts", "mm"),
    Channel("rain_storm", "Rainfall of the ongoing rain event", Quantity.TIP_COUNT, "Counts", "mm"),
    Channel("rain_storm_start_at", "Start of the ongoing rain event", Quantity.PLAIN, "Unix time", "Unix time"),
    Channel("rainfall_daily", "Rainfall since midnight", Quantity.TIP_COUNT, "Counts", "mm"),
    Channel("rainfall_monthly", "Rainfall since the first of the month", Quantity.TIP_COUNT, "Counts", "mm"),
    Channel("rainfall_year", "Rainfall since new year", Quantity.TIP_COUNT, "Counts", "mm"),
    Channel("rain_storm_last", "Rainfall of the previous rain event", Quantity.TIP_COUNT, "Counts", "mm"),
    Channel("rain_storm_last_start_at", "Start of the previous rain event", Quantity.PLAIN, "Unix time", "Unix time"),
    Channel("rain_storm_last_end_at", "End of the previous rain event", Quantity.PLAIN, "Unix time", "Unix time"),
    Channel("rx_state", "Reception state of the sensor", Quantity.PLAIN, "", ""),
    Channel("trans_battery_flag", "Transmitter battery flag (0 = fine, 1 = low)", Quantity.PLAIN, "", ""),
    Channel("rain_size", "Resolution of the rain gauge", Quantity.TIP_CODE, "Code", "mm/tip"),
)

#: Channel lookup by API key.
BY_KEY: dict[str, Channel] = {channel.key: channel for channel in LAYOUT}


def _celsius(value: float, _resolution: Any) -> float:
    return round((value - 32.0) * 5.0 / 9.0, 1)


def _kilometres_per_hour(value: float, _resolution: Any) -> float:
    return round(value * 1.609344, 1)


def _hectopascal(value: float, _resolution: Any) -> float:
    return round(value * 33.86389, 1)


def _millimetres(value: float, resolution: Any) -> float:
    """Bucket tips scaled by the gauge resolution the station announced."""
    step = TIP_MILLIMETRES.get(resolution)
    return round(value * step, 2) if step else value


def _millimetres_per_tip(value: float, _resolution: Any) -> float:
    return TIP_MILLIMETRES.get(value, value)


_CONVERSIONS = {
    Quantity.FAHRENHEIT: _celsius,
    Quantity.MILES_PER_HOUR: _kilometres_per_hour,
    Quantity.INCHES_MERCURY: _hectopascal,
    Quantity.TIP_COUNT: _millimetres,
    Quantity.TIP_CODE: _millimetres_per_tip,
}


def keys() -> tuple[str, ...]:
    """All channel keys in column order."""
    return tuple(channel.key for channel in LAYOUT)


def unit_of(key: str, metric: bool = True) -> str:
    """Unit of a channel in the requested unit system, "" if unknown."""
    channel = BY_KEY.get(key)
    if channel is None:
        return ""
    return channel.metric_unit if metric else channel.native_unit


def to_metric(channel: Channel, value: Any, resolution: Any = None) -> Any:
    """Convert a single raw value; non numbers are handed back untouched."""
    conversion = _CONVERSIONS.get(channel.quantity)
    if conversion is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    return conversion(value, resolution)


def project(
    values: Mapping[str, Any],
    wanted: Iterable[str],
    metric: bool = True,
) -> dict[str, Any]:
    """Pick the wanted channels out of a raw reading and convert them.

    The result keeps the column order of :data:`LAYOUT`. Channels the
    station did not deliver (or delivered as ``null``) end up as an empty
    string so their CSV cell stays blank.
    """
    requested = set(wanted)
    resolution = values.get(RESOLUTION_CHANNEL)
    row: dict[str, Any] = {}
    for channel in LAYOUT:
        if channel.key not in requested:
            continue
        value = values.get(channel.key)
        if value is None:
            row[channel.key] = ""
        elif metric:
            row[channel.key] = to_metric(channel, value, resolution)
        else:
            row[channel.key] = value
    return row
