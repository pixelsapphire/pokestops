from __future__ import annotations
import csv
import os
import platform
import subprocess
import sys
import zipfile
from htmlBuilder.attributes import HtmlTagAttribute
from math import atan2, pi
from typing import Any, Protocol, TypeVar, runtime_checkable

TContra = TypeVar("TContra", contravariant=True)


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
                comment_rows.append(row) if row[0].startswith('#') else data_rows.append(row)
            return data_rows, comment_rows
        except StopIteration:
            error(f'File {os.path.abspath(file)} is empty')


def create_lexicographic_mapping(mapping_data: str) -> dict[str, float]:
    mapping: dict[str, float] = {}
    character_sets = mapping_data.split()
    for base_character, *derived_characters in character_sets:
        if not derived_characters:
            continue
        for i, derived_character in enumerate(derived_characters):
            mapping[derived_character] = ord(base_character) + (1 + i) / (1 + len(derived_characters))
    return mapping


def lexicographic_sequence(s: str, mapping: dict[str, float]) -> list[float]:
    return [mapping[c] if c in mapping else float(ord(c)) for c in s]


class zip_file(zipfile.ZipFile):
    def extract_as(self, member: str | zipfile.ZipInfo, output: str | os.PathLike[str],
                   path: str | os.PathLike[str] | None = None, pwd: bytes | None = None):
        self.extract(member, path, pwd)
        member_name = member.filename if isinstance(member, zipfile.ZipInfo) else member
        os.rename(member_name, output)


class geopoint:
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude

    def __str__(self):
        return f'({self.latitude}, {self.longitude})'

    def __repr__(self):
        return f'geopoint({self.latitude}, {self.longitude})'

    def __eq__(self, other: geopoint):
        return self.latitude == other.latitude and self.longitude == other.longitude if isinstance(other, geopoint) else False

    def __hash__(self):
        return hash((self.latitude, self.longitude))

    def __iter__(self):
        return iter((self.latitude, self.longitude))

    def __len__(self):
        return 2

    def __getitem__(self, index: int):
        return self.latitude if index == 0 else self.longitude if index == 1 else None


class vector2f:
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

    def __eq__(self, other: vector2f | FloatVectorLike):
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


class CustomHtmlTagAttribute(HtmlTagAttribute):
    def __init__(self, name: str, value: str | bool | None):
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        super().__init__(value)
        self._name = name
