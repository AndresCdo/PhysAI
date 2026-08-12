"""Physical constants and reserved keywords for PhysAI."""

from typing import Dict, Set
from physai.core.types import UnitDimension

RESERVED_CONSTANTS: Set[str] = {
    "g",
    "c",
    "pi",
    "e",
    "h",
    "hbar",
    "k",
    "kb",
    "epsilon0",
    "mu0",
    "Na",
    "R",
    "G",
    "sigma",
    "me",
    "mp",
    "mn",
    "qe",
}

MATHEMATICAL_FUNCTIONS: Set[str] = {
    "Sin",
    "Cos",
    "Tan",
    "ArcSin",
    "ArcCos",
    "ArcTan",
    "Sinh",
    "Cosh",
    "Tanh",
    "Log",
    "Log10",
    "Log2",
    "Exp",
    "Sqrt",
    "Power",
    "Abs",
    "Sign",
    "Floor",
    "Ceiling",
    "Round",
    "Min",
    "Max",
    "Sum",
    "Product",
}

PHYSICAL_UNITS: Dict[str, UnitDimension] = {
    "Meters": UnitDimension(length=1),
    "m": UnitDimension(length=1),
    "Kilograms": UnitDimension(mass=1),
    "kg": UnitDimension(mass=1),
    "Seconds": UnitDimension(time=1),
    "s": UnitDimension(time=1),
    "Amperes": UnitDimension(current=1),
    "A": UnitDimension(current=1),
    "Kelvins": UnitDimension(temperature=1),
    "K": UnitDimension(temperature=1),
    "Moles": UnitDimension(amount=1),
    "mol": UnitDimension(amount=1),
    "Candelas": UnitDimension(luminosity=1),
    "cd": UnitDimension(luminosity=1),
    "Newtons": UnitDimension(mass=1, length=1, time=-2),
    "N": UnitDimension(mass=1, length=1, time=-2),
    "Joules": UnitDimension(mass=1, length=2, time=-2),
    "J": UnitDimension(mass=1, length=2, time=-2),
    "Watts": UnitDimension(mass=1, length=2, time=-3),
    "W": UnitDimension(mass=1, length=2, time=-3),
    "Pascals": UnitDimension(mass=1, length=-1, time=-2),
    "Pa": UnitDimension(mass=1, length=-1, time=-2),
    "Volts": UnitDimension(mass=1, length=2, time=-3, current=-1),
    "V": UnitDimension(mass=1, length=2, time=-3, current=-1),
    "Ohms": UnitDimension(mass=1, length=2, time=-3, current=-2),
    "Hertz": UnitDimension(time=-1),
    "Hz": UnitDimension(time=-1),
    "MetersPerSecond": UnitDimension(length=1, time=-1),
    "m/s": UnitDimension(length=1, time=-1),
    "MetersPerSecondSquared": UnitDimension(length=1, time=-2),
    "m/s^2": UnitDimension(length=1, time=-2),
    "Radians": UnitDimension(),
    "rad": UnitDimension(),
    "Degrees": UnitDimension(),
    "deg": UnitDimension(),
}

SI_BASE_UNITS = [
    "Meters",
    "Kilograms",
    "Seconds",
    "Amperes",
    "Kelvins",
    "Moles",
    "Candelas",
]

UNIT_ALIASES: Dict[str, str] = {
    "meter": "Meters",
    "metre": "Meters",
    "kilogram": "Kilograms",
    "second": "Seconds",
    "ampere": "Amperes",
    "kelvin": "Kelvins",
    "mole": "Moles",
    "candela": "Candelas",
    "newton": "Newtons",
    "joule": "Joules",
    "watt": "Watts",
    "pascal": "Pascals",
    "volt": "Volts",
    "ohm": "Ohms",
    "hertz": "Hertz",
}


def normalize_unit(unit: str) -> str:
    """Normalize a unit string to standard form."""
    unit_lower = unit.lower().strip()
    if unit_lower in UNIT_ALIASES:
        return UNIT_ALIASES[unit_lower]
    if unit in PHYSICAL_UNITS:
        return unit
    return unit


def get_unit_dimension(unit: str) -> UnitDimension:
    """Get the dimension of a unit string."""
    normalized = normalize_unit(unit)
    if normalized in PHYSICAL_UNITS:
        return PHYSICAL_UNITS[normalized]
    raise ValueError(f"Unknown unit: {unit}")
