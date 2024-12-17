from __future__ import annotations
import csv
import os
import platform
import subprocess
import sys
import zipfile
from htmlBuilder.attributes import HtmlTagAttribute
from math import atan2, pi
from sortedcontainers import SortedSet
from typing import Any, Callable, Final, Iterable, Protocol, Self, Sequence, TypeVar, runtime_checkable

T = TypeVar("T")
TContra = TypeVar("TContra", contravariant=True)
TFloatSeq = TypeVar("TFloatSeq", bound=Sequence[float])


class FloatVectorLike(Protocol):
    def __getitem__(self, index: int) -> float: ...


@runtime_checkable
class SupportsDunderLT(Protocol[TContra]):
    def __lt__(self, other: TContra, /) -> bool: ...


@runtime_checkable
class SupportsDunderGT(Protocol[TContra]):
    def __gt__(self, other: TContra, /) -> bool: ...


RichComparisonT = TypeVar("RichComparisonT", bound=SupportsDunderLT[Any] | SupportsDunderGT[Any])

__roman_num__: dict[int, str] = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X'}


def roman_numeral(n: int) -> str:
    return __roman_num__[n] if 1 <= n <= 10 else f'{n}'


def sign(n: int | float) -> int:
    return 1 if n > 0 else -1 if n < 0 else 0


def count(iterable: Iterable[Any]) -> int:
    return sum(1 for _ in iterable)


def to_css(stylesheet: dict[str, dict[str, str]]) -> str:
    return '\n'.join(
        f'{selector} {{\n{";\n".join(f"{prop}: {value}" for prop, value in properties.items())};\n}}'
        for selector, properties in stylesheet.items()
    )


__error_log__: list[str] = []


def error(*args: Any) -> None:
    __error_log__.append(' '.join(map(str, args)))


def print_errors() -> None:
    for message in __error_log__:
        print(message, file=sys.stderr)


def prepare_path(file_path: str | os.PathLike[str]) -> str | os.PathLike[str]:
    directory_path = os.path.dirname(os.path.abspath(file_path))
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    return file_path


def system_open(file_path: str | os.PathLike[str]) -> None:
    if platform.system() == 'Darwin':  # macOS
        subprocess.call(('open', file_path))
    elif platform.system() == 'Windows':  # windows
        os.startfile(file_path)
    else:  # linux
        subprocess.call(('xdg-open', file_path))


def file_to_string(file_path: str | os.PathLike[str]) -> str:
    with open(file_path, 'r') as file:
        return file.read()


def get_csv_rows(file: str | os.PathLike[str]) -> tuple[list[list[str]], list[list[str]]]:
    with open(file, 'r') as f:
        try:
            reader = csv.reader(f)
            next(reader)
            rows: list[list[str]] = [row for row in reader if len(row) > 0]
            data_rows: list[list[str]] = []
            comment_rows: list[list[str]] = []
            for row in rows:
                if not row[0].lstrip().startswith('#'):
                    data_rows.append(row)
                elif not row[0].lstrip().startswith('##'):
                    row[0] = row[0].lstrip().lstrip('#').lstrip()
                    comment_rows.append(row)
            return data_rows, comment_rows
        except StopIteration:
            error(f'File {os.path.abspath(file)} is empty')
            return [], []


def create_lexicographic_mapping(mapping_data: str) -> dict[str, float]:
    mapping: dict[str, float] = {}
    character_sets = mapping_data.split()
    for character_set in character_sets:
        base_character: str = character_set[0]
        derived_characters: str = character_set[1:]
        if not derived_characters:
            continue
        for i, derived_character in enumerate(derived_characters):
            mapping[derived_character] = ord(base_character) + (1 + i) / (1 + len(derived_characters))
    return mapping


def lexicographic_sequence(s: str, mapping: dict[str, float]) -> list[float]:
    return [mapping[c] if c in mapping else float(ord(c)) for c in s]


def lexicographic_compare(a: str, b: str, mapping: dict[str, float]) -> int:
    seq_a: list[float] = lexicographic_sequence(a, mapping)
    seq_b: list[float] = lexicographic_sequence(b, mapping)
    for x, y in zip(seq_a, seq_b):
        if x != y:
            return sign(x - y)
    return -1 if len(seq_a) < len(seq_b) else 1 if len(seq_a) > len(seq_b) else 0


class zip_file(zipfile.ZipFile):
    def extract_as(self, member: str | zipfile.ZipInfo, output: str | os.PathLike[str],
                   path: str | os.PathLike[str] | None = None, pwd: bytes | None = None):
        self.extract(member, path, pwd)
        member_name = member.filename if isinstance(member, zipfile.ZipInfo) else member
        os.rename(member_name, output)


class geopoint(Sequence[float]):
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude

    def __str__(self):
        return f'({self.latitude}, {self.longitude})'

    def __repr__(self):
        return f'geopoint({self.latitude}, {self.longitude})'

    def __eq__(self, other):
        return self.latitude == other.latitude and self.longitude == other.longitude if isinstance(other, geopoint) else False

    def __hash__(self):
        return hash((self.latitude, self.longitude))

    def __iter__(self):
        return iter((self.latitude, self.longitude))

    def __len__(self):
        return 2

    def __getitem__(self, index: int):
        return self.latitude if index == 0 else self.longitude if index == 1 else None


class vector2f(Sequence[float]):
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def unit(self):
        return self / abs(self)

    def angle(self):
        return atan2(self.y, self.x) % (2 * pi)

    @staticmethod
    def angle_offset(a: vector2f, b: vector2f) -> float:
        return abs(atan2(a.y, a.x) - atan2(b.y, b.x)) % pi

    def __str__(self):
        return f'({self.x}, {self.y})'

    def __repr__(self):
        return f'point({self.x}, {self.y})'

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y \
            if isinstance(other, vector2f) else self.x == other[0] and self.y == other[1]

    def __hash__(self):
        return hash((self.x, self.y))

    def __neg__(self):
        return vector2f(-self.x, -self.y)

    def __add__(self, other: vector2f | FloatVectorLike):
        return vector2f(self.x + other.x, self.y + other.y) \
            if isinstance(other, vector2f) else vector2f(self.x + other[0], self.y + other[1])

    def __sub__(self, other: vector2f | FloatVectorLike):
        return vector2f(self.x - other.x, self.y - other.y) \
            if isinstance(other, vector2f) else vector2f(self.x - other[0], self.y - other[1])

    def __mul__(self, other: Any):
        return vector2f(self.x * other.x, self.y * other.y) \
            if isinstance(other, vector2f) else vector2f(self.x * other[0], self.y * other[1]) \
            if isinstance(other, vector2f) else vector2f(self.x * other, self.y * other)

    def __truediv__(self, other: Any):
        return vector2f(self.x / other.x, self.y / other.y) \
            if isinstance(other, vector2f) else vector2f(self.x / other[0], self.y / other[1]) \
            if isinstance(other, vector2f) else vector2f(self.x / other, self.y / other)

    def __abs__(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def __bool__(self):
        return self.x != 0 or self.y != 0

    def __iter__(self):
        return iter((self.x, self.y))

    def __len__(self):
        return 2

    def __getitem__(self, index: int):
        return self.x if index == 0 else self.y if index == 1 else None


class LineSegment[TFloatSeq](Sequence[TFloatSeq]):
    def __init__(self, a: TFloatSeq, b: TFloatSeq):
        self._a: TFloatSeq = a
        self._b: TFloatSeq = b
        if a[0] > b[0] or a[0] == b[0] and a[1] > b[1]:
            self._a, self._b = self._b, self._a

    def __eq__(self, other):
        return (self._a, self._b) == (other._a, other._b) if isinstance(other, LineSegment) else False

    def __hash__(self):
        return hash((self._a, self._b))

    def __getitem__(self, index):
        return self._a if index == 0 else self._b if index == 1 else None

    def __iter__(self):
        return iter((self._a, self._b))

    def __len__(self):
        return 2

    def __repr__(self):
        return f'LineSegment({self._a}, {self._b})'

    @property
    def a(self) -> TFloatSeq:
        return self._a

    @property
    def b(self) -> TFloatSeq:
        return self._b


class DateAndOrder:
    long_time_ago: Final[Self] = None
    never: Final[Self] = None

    def __init__(self, *, year: int | None = None, month: int | None = None, day: int | None = None,
                 date_string: str | None = '', number_in_day: int | None = None):
        if date_string:
            date_and_number: list[str] = date_string.split(':')
            date_parts: list[int] = list(map(int, date_and_number[0].split('-')))
            self._year: int = date_parts[0]
            self._month: int = date_parts[1]
            self._day: int = date_parts[2]
            if len(date_and_number) > 1 and number_in_day is not None:
                raise ValueError('Cannot pass argument number_in_day if the number is already present in date_string')
            elif len(date_and_number) > 1:
                self._number_in_day: int = int(date_and_number[1])
            elif number_in_day is not None:
                self._number_in_day: int = number_in_day
            else:
                self._number_in_day: int = 0
        elif year is not None and month is not None and day is not None:
            self._year = year
            self._month = month
            self._day = day
            self._number_in_day = number_in_day if number_in_day is not None else 0
        else:
            raise ValueError('Must pass either (date_string, [number_in_day]), (year, month, day, [number_in_day]), '
                             'or use DateAndOrder.long_time_ago or DateAndOrder.unknown')

    def __eq__(self, other):
        return self.__cmp_key__() == other.__cmp_key__() if isinstance(other, DateAndOrder) else False

    def __lt__(self, other):
        return self.__cmp_key__() < other.__cmp_key__() if isinstance(other, DateAndOrder) else False

    def __gt__(self, other):
        return self.__cmp_key__() > other.__cmp_key__() if isinstance(other, DateAndOrder) else False

    def __hash__(self):
        return hash((self._year, self._month, self._day, self._number_in_day))

    def __bool__(self):
        return self.is_known()

    def __str__(self):
        return f'{self._year:04}-{self._month:02}-{self._day:02}:{self._number_in_day}'

    def __repr__(self):
        return f'DateAndOrder({self._year}, {self._month}, {self._day}, {self._number_in_day})'

    def __format__(self, format_spec: str):
        if not format_spec:
            return self.__str__()
        format_parts: list[str] = format_spec.split('|')
        if len(format_parts) > 3:
            raise ValueError(f'Invalid format specifier \'{format_spec}\' for object of type \'{type(self)}\'')
        if self == DateAndOrder.long_time_ago and len(format_parts) > 1:
            return format_parts[1]
        elif self == DateAndOrder.never and len(format_parts) > 1:
            return format_parts[2 if len(format_parts) == 2 else 1]
        else:
            formatted_string: str = format_parts[0]
            if 'y' in format_spec:
                formatted_string = formatted_string.replace('y', f'{self._year:04}')
            if 'm' in format_spec:
                formatted_string = formatted_string.replace('m', f'{self._month:02}')
            if 'd' in format_spec:
                formatted_string = formatted_string.replace('d', f'{self._day:02}')
            if 'n' in format_spec:
                formatted_string = formatted_string.replace('n', f'{self._number_in_day}')
            return formatted_string

    def __cmp_key__(self) -> RichComparisonT:
        return self._year, self._month, self._day, self._number_in_day

    @property
    def year(self) -> int:
        return self._year

    @property
    def month(self) -> int:
        return self._month

    @property
    def day(self) -> int:
        return self._day

    @property
    def number_in_day(self) -> int:
        return self._number_in_day

    def is_known(self) -> bool:
        return self != DateAndOrder.never and self != DateAndOrder.long_time_ago

    def to_string(self, number: bool = True) -> str:
        return self.__str__() if number else self.__str__().split(':')[0]


DateAndOrder.long_time_ago = DateAndOrder(year=0, month=0, day=0, number_in_day=0)  # type: ignore
DateAndOrder.never = DateAndOrder(year=-1, month=-1, day=-1, number_in_day=-1)  # type: ignore


class CustomHtmlTagAttribute(HtmlTagAttribute):
    def __init__(self, name: str, value: str | bool | None):
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        super().__init__(value)
        self._name = name


class Comparator[T]:
    def __init__(self, cmp: Callable[[T, T], int]):
        self._cmp: Callable[[T, T], int] = cmp

    def __sort__(self, items: list[T]) -> list[T]:
        if len(items) <= 1:
            return items
        pivot = items[len(items) // 2]
        less = [item for item in items if self._cmp(item, pivot) < 0]
        equal = [item for item in items if self._cmp(item, pivot) == 0]
        greater = [item for item in items if self._cmp(item, pivot) > 0]
        return self.__sort__(less) + equal + self.__sort__(greater)

    def sorted(self, items: Iterable[T]) -> list[T]:
        return self.__sort__(list(items))


class HashableSet[T](SortedSet[T]):
    def __init__(self, iterable: Iterable[T] = ()):
        super().__init__(iterable)

    def __hash__(self):
        return hash(tuple(self))

    def __repr__(self):
        return f'HashableSet({super().__repr__()})'
