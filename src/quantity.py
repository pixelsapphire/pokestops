from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from util import strif


class Multiplier:
    def __init__(self, value: float | int | str | Decimal, symbol: str):
        self.value: Decimal = Decimal(value)
        self.symbol: str = symbol

    def __repr__(self):
        return f'Multiplier x{self.value} [{self.symbol}]'


yocto: Multiplier = Multiplier(Decimal('0.000000000000000000000001'), 'y')
zepto: Multiplier = Multiplier(Decimal('0.000000000000000000001'), 'z')
atto: Multiplier = Multiplier(Decimal('0.000000000000000001'), 'a')
femto: Multiplier = Multiplier(Decimal('0.000000000000001'), 'f')
pico: Multiplier = Multiplier(Decimal('0.000000000001'), 'p')
nano: Multiplier = Multiplier(Decimal('0.000000001'), 'n')
micro: Multiplier = Multiplier(Decimal('0.000001'), 'µ')
milli: Multiplier = Multiplier(Decimal('0.001'), 'm')
centi: Multiplier = Multiplier(Decimal('0.01'), 'c')
deci: Multiplier = Multiplier(Decimal('0.1'), 'd')
one: Multiplier = Multiplier(Decimal('1'), '')
deca: Multiplier = Multiplier(Decimal('10'), 'da')
hecto: Multiplier = Multiplier(Decimal('100'), 'h')
kilo: Multiplier = Multiplier(Decimal('1000'), 'k')
mega: Multiplier = Multiplier(Decimal('1000000'), 'M')
giga: Multiplier = Multiplier(Decimal('1000000000'), 'G')
tera: Multiplier = Multiplier(Decimal('1000000000000'), 'T')
peta: Multiplier = Multiplier(Decimal('1000000000000000'), 'P')
exa: Multiplier = Multiplier(Decimal('1000000000000000000'), 'E')
zetta: Multiplier = Multiplier(Decimal('1000000000000000000000'), 'Z')
yotta: Multiplier = Multiplier(Decimal('1000000000000000000000000'), 'Y')
kibi: Multiplier = Multiplier('1024', 'Ki')
mebi: Multiplier = Multiplier('1048576', 'Mi')
gibi: Multiplier = Multiplier('1073741824', 'Gi')
tebi: Multiplier = Multiplier('1099511627776', 'Ti')
pebi: Multiplier = Multiplier('1125899906842624', 'Pi')
exbi: Multiplier = Multiplier('1152921504606846976', 'Ei')
zebi: Multiplier = Multiplier('1180591620717411303424', 'Zi')
yobi: Multiplier = Multiplier('1208925819614629174706176', 'Yi')


class Unit:
    def __init__(self, symbol: str | None = '', multiplier: Multiplier = one):
        self.symbol: str = strif(symbol, symbol)
        self.multiplier: Multiplier = multiplier

    def __str__(self) -> str:
        return f'{self.multiplier.symbol}{self.symbol}'

    def __repr__(self):
        return f'Unit({self.symbol}, {self.multiplier})'

    def __eq__(self, other):
        return self.symbol == other.symbol and self.multiplier.value == other.multiplier.value

    def __hash__(self):
        return hash((self.symbol, self.multiplier.value))

    def __lt__(self, other):
        return self.multiplier.value < other.multiplier.value

    def __le__(self, other):
        return self.multiplier.value <= other.multiplier.value

    def __gt__(self, other):
        return self.multiplier.value > other.multiplier.value

    def __ge__(self, other):
        return self.multiplier.value >= other.multiplier.value

    def compatible_with(self, other: Unit) -> bool:
        return self.symbol == other.symbol


class Quantity:
    def __init__(self, magnitude: float | int | str | Decimal | Quantity, unit: str | Unit = ''):
        if isinstance(magnitude, Quantity):
            self.magnitude: Decimal = magnitude.magnitude
            self.unit: Unit = magnitude.unit
        else:
            self.magnitude: Decimal = Decimal(magnitude)
            self.unit: Unit = Unit(unit) if isinstance(unit, str) else unit

    def __str__(self) -> str:
        return f'{self.magnitude}{self.unit}'

    def __repr__(self) -> str:
        return f'Quantity({self.magnitude}, {self.unit})'

    def __eq__(self, other: Quantity) -> bool:
        return self.base_magnitude == other.base_magnitude and self.unit.compatible_with(other.unit)

    def __hash__(self) -> int:
        return hash((self.base_magnitude, self.unit.symbol))

    def __lt__(self, other):
        if not self.unit.compatible_with(other.unit):
            raise ValueError('Cannot compare quantities with different units')
        return self.base_magnitude < other.base_magnitude

    def __le__(self, other):
        if not self.unit.compatible_with(other.unit):
            raise ValueError('Cannot compare quantities with different units')
        return self.base_magnitude <= other.base_magnitude

    def __gt__(self, other):
        if not self.unit.compatible_with(other.unit):
            raise ValueError('Cannot compare quantities with different units')
        return self.base_magnitude > other.base_magnitude

    def __ge__(self, other):
        if not self.unit.compatible_with(other.unit):
            raise ValueError('Cannot compare quantities with different units')
        return self.base_magnitude >= other.base_magnitude

    def __ne__(self, other):
        return not self == other

    def __add__(self, other: Quantity) -> Quantity:
        if not self.unit.compatible_with(other.unit):
            raise ValueError('Cannot add quantities with different units')
        return Quantity(self.magnitude + other.magnitude, self.unit) \
            if self.unit == other.unit else Quantity(self.base_magnitude + other.base_magnitude, self.unit.symbol)

    def __sub__(self, other: Quantity) -> Quantity:
        if self.unit != other.unit:
            raise ValueError('Cannot subtract quantities with different units')
        return Quantity(self.magnitude - other.magnitude, self.unit) \
            if self.unit == other.unit else Quantity(self.base_magnitude - other.base_magnitude, self.unit.symbol)

    def __mul__(self, scalar: float | int | str | Decimal) -> Quantity:
        return Quantity(self.magnitude * scalar, self.unit)

    def __truediv__(self, scalar: float | int | str | Decimal) -> Quantity:
        return Quantity(self.magnitude / scalar, self.unit)

    def __floordiv__(self, scalar: float | int | str | Decimal) -> Quantity:
        return Quantity(self.magnitude // scalar, self.unit)

    def __abs__(self) -> Quantity:
        return Quantity(abs(self.magnitude), self.unit)

    def __neg__(self) -> Quantity:
        return Quantity(-self.magnitude, self.unit)

    @property
    def base_magnitude(self) -> Decimal:
        return self.magnitude * self.unit.multiplier.value

    def convert(self, *, multiplier: Multiplier | None = None) -> Quantity:
        if multiplier is not None:
            return Quantity(self.magnitude / multiplier.value, Unit(self.unit.symbol, multiplier))
        return self

    def format(self, *, multiplier: Multiplier | None = None, precision: int | None = None) -> str:
        magnitude: Decimal = self.magnitude if multiplier is None else self.magnitude * multiplier.value
        return f'{round(magnitude, precision)}{self.unit}' if precision is not None else f'{magnitude}{self.unit}'


class Duration(Quantity):
    def __init__(self, duration: float | int | str | Decimal | Quantity, multiplier: Multiplier = one):
        super().__init__(duration, Unit('s', multiplier))

    @staticmethod
    def from_hms(*, hours: int = 0, minutes: int = 0, seconds: float = 0) -> Duration:
        return Duration(hours * 3600 + minutes * 60 + seconds)

    @staticmethod
    def as_difference(start: datetime, end: datetime) -> Duration:
        return Duration((end - start).total_seconds())

    def format_as_hms(self, display_zero: bool = False) -> str:
        hours, remainder = divmod(abs(self.base_magnitude), 3600)
        minutes, seconds = divmod(remainder, 60)
        h, m, s = f'{int(hours)}h', f'{int(minutes)}m', f'{int(seconds)}s'
        return f'{h} {m} {s}' if display_zero else (f'{strif(h, hours > 0)} {strif(m, minutes > 0)} '
                                                    f'{strif(s, seconds > 0 or (hours == 0 and minutes == 0))}').strip()

    def __add__(self, other: Duration) -> Duration:
        return Duration(self.base_magnitude + other.base_magnitude)

    def __sub__(self, other: Duration) -> Duration:
        return Duration(self.base_magnitude - other.base_magnitude)

    def __mul__(self, scalar: float | int | str | Decimal) -> Duration:
        return Duration(self.base_magnitude * scalar)

    def __truediv__(self, scalar: float | int | str | Decimal) -> Duration:
        return Duration(self.base_magnitude / scalar)

    def __floordiv__(self, scalar: float | int | str | Decimal) -> Duration:
        return Duration(self.base_magnitude // scalar)

    def __abs__(self) -> Duration:
        return Duration(abs(self.base_magnitude))

    def __neg__(self) -> Duration:
        return Duration(-self.base_magnitude)
