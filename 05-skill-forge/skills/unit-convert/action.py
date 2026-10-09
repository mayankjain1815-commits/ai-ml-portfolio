"""Unit conversion table + math — the executable half of unit-convert.

Factors convert to a *base unit* per family (meters, grams, bytes, seconds,
m/s). Temperature is handled separately because it's affine, not linear —
a classic source of wrong answers when a model just multiplies.
"""

from __future__ import annotations

# family -> {unit alias: factor to base}
FAMILIES: dict[str, dict[str, float]] = {
    "length": {
        "m": 1, "meter": 1, "meters": 1, "metre": 1, "metres": 1,
        "km": 1000, "kilometer": 1000, "kilometers": 1000,
        "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
        "mm": 0.001, "mi": 1609.344, "mile": 1609.344, "miles": 1609.344,
        "ft": 0.3048, "foot": 0.3048, "feet": 0.3048,
        "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
        "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
    },
    "mass": {
        "g": 1, "gram": 1, "grams": 1,
        "kg": 1000, "kilogram": 1000, "kilograms": 1000,
        "mg": 0.001, "lb": 453.59237, "lbs": 453.59237,
        "pound": 453.59237, "pounds": 453.59237,
        "oz": 28.349523125, "ounce": 28.349523125, "ounces": 28.349523125,
        "t": 1_000_000, "tonne": 1_000_000, "tonnes": 1_000_000,
    },
    "data": {
        "b": 1, "byte": 1, "bytes": 1,
        "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4,
        "kib": 1024, "mib": 1024**2, "gib": 1024**3, "tib": 1024**4,
        "kilobyte": 1000, "megabyte": 1000**2, "gigabyte": 1000**3,
    },
    "time": {
        "s": 1, "sec": 1, "second": 1, "seconds": 1,
        "ms": 0.001, "min": 60, "minute": 60, "minutes": 60,
        "h": 3600, "hr": 3600, "hour": 3600, "hours": 3600,
        "day": 86400, "days": 86400, "week": 604800, "weeks": 604800,
        "year": 31_557_600, "years": 31_557_600,  # 365.25 days
    },
    "speed": {
        "m/s": 1, "mps": 1,
        "km/h": 1 / 3.6, "kph": 1 / 3.6, "kmh": 1 / 3.6,
        "mph": 0.44704, "mi/h": 0.44704,
        "kn": 0.514444, "knot": 0.514444, "knots": 0.514444,
    },
}

TEMP_UNITS = {"c", "celsius", "°c", "f", "fahrenheit", "°f", "k", "kelvin"}

ALIASES: dict[str, tuple[str, float]] = {
    alias: (family, factor)
    for family, table in FAMILIES.items()
    for alias, factor in table.items()
}


class UnknownUnit(ValueError):
    pass


def lookup(unit: str) -> tuple[str, float]:
    key = unit.strip().lower()
    if key in ALIASES:
        return ALIASES[key]
    raise UnknownUnit(f"unknown unit {unit!r}")


def _to_celsius(value: float, unit: str) -> float:
    u = unit.lower()
    if u in {"c", "celsius", "°c"}:
        return value
    if u in {"f", "fahrenheit", "°f"}:
        return (value - 32) * 5 / 9
    return value - 273.15  # kelvin


def _from_celsius(c: float, unit: str) -> float:
    u = unit.lower()
    if u in {"c", "celsius", "°c"}:
        return c
    if u in {"f", "fahrenheit", "°f"}:
        return c * 9 / 5 + 32
    return c + 273.15


def convert(value: float, src: str, dst: str) -> tuple[float, str]:
    """Return (converted_value, one-line_worked_formula)."""
    s, d = src.strip().lower(), dst.strip().lower()

    if s in TEMP_UNITS and d in TEMP_UNITS:
        c = _to_celsius(value, s)
        out = _from_celsius(c, d)
        pivot = "" if s == "c" or d == "c" else " via °C"
        return out, f"{value:g}°{s.upper()} -> {out:g}°{d.upper()}{pivot}"

    src_family, src_factor = lookup(src)
    dst_family, dst_factor = lookup(dst)
    if src_family != dst_family:
        raise UnknownUnit(
            f"can't convert {src_family} ({src!r}) to {dst_family} ({dst!r})"
        )
    out = value * src_factor / dst_factor
    return out, f"{value:g} × {src_factor:g} ÷ {dst_factor:g}"


def sig4(x: float) -> str:
    """4 significant digits, trailing zeros stripped (3.28 not 3.2800)."""
    if x == 0:
        return "0"
    from math import log10, floor

    digits = 4 - int(floor(log10(abs(x)))) - 1
    rounded = round(x, max(0, digits))
    return f"{rounded:g}"


def run(inputs: dict[str, str]) -> str:
    missing = [k for k in ("value", "from_unit", "to_unit") if k not in inputs]
    if missing:
        raise ValueError(
            f"missing {', '.join(missing)} — e.g. "
            "--input value=12.5 --input from_unit=km --input to_unit=miles"
        )
    try:
        value = float(inputs["value"])
    except ValueError as exc:
        raise ValueError(f"value must be a number, got {inputs['value']!r}") from exc

    try:
        result, work = convert(value, inputs["from_unit"], inputs["to_unit"])
    except UnknownUnit as exc:
        families = ", ".join(FAMILIES)
        return f"{exc}\nSupported families: {families}, plus temperature (C, F, K)."

    return f"{sig4(value)} {inputs['from_unit']} = {sig4(result)} {inputs['to_unit']}\nhow: {work}"
