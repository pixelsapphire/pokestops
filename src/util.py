import csv
import os
import platform
import subprocess
import zipfile
from datetime import datetime
from functools import partial
from log import error
from quantity import kilo, Quantity
from sortedcontainers import SortedSet
from typing import Any, Callable, Generic, Hashable, Iterable, Protocol, TypeVar, runtime_checkable

T: TypeVar = TypeVar("T")
TContra: TypeVar = TypeVar("TContra", contravariant=True)


@runtime_checkable
class SupportsDunderLT(Protocol[TContra]):
    def __lt__(self, other: TContra, /) -> bool: ...


@runtime_checkable
class SupportsDunderGT(Protocol[TContra]):
    def __gt__(self, other: TContra, /) -> bool: ...


RichComparisonT: TypeVar = TypeVar("RichComparisonT", bound=SupportsDunderLT[Any] | SupportsDunderGT[Any])


class memoized:
    def __init__(self, func):
        self.func = func
        self.cache: dict[tuple[Any, ...], Any] = {}

    def __call__(self, *args):
        hashed_args: tuple[Any, ...] = tuple(arg if isinstance(arg, Hashable) else (type(arg), id(arg)) for arg in args)
        if hashed_args in self.cache:
            return self.cache[hashed_args]
        else:
            value = self.func(*args)
            self.cache[hashed_args] = value
            return value

    def __repr__(self):
        return self.func.__doc__

    def __get__(self, obj, objtype):
        return partial(self.__call__, obj)


__roman_num__: dict[int, str] = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X'}


def roman_numeral(n: int) -> str:
    return __roman_num__[n] if 1 <= n <= 10 else f'{n}'


def sign(n: int | float) -> int:
    return 1 if n > 0 else -1 if n < 0 else 0


def count(iterable: Iterable[Any]) -> int:
    return sum(1 for _ in iterable)


def find_first[T](predicate: Callable[[T], bool], iterable: Iterable[T], /, default: T | None = None) -> T | None:
    return next(filter(predicate, iterable), default)


def coalesce(*args: Any) -> Any:
    for x in args:
        if x is not None:
            return x
    return None


def strif(s: str, condition: Any) -> str:
    return s if condition else ''


def maybe(self: Any, method: str | Callable, *args: Any, **kwargs: Any) -> Any:
    if self is None:
        return None
    return method(self, *args, **kwargs) if callable(method) else getattr(self, method)(*args, **kwargs)


def to_css(stylesheet: dict[str, dict[str, str]]) -> str:
    return '\n'.join(
        f'{selector} {{\n{";\n".join(f"{prop}: {value}" for prop, value in properties.items())};\n}}'
        for selector, properties in stylesheet.items()
    )


def invert_hex_color(color: str) -> str:
    hashtag: bool = color.startswith('#')
    color: str = color.lstrip('#')
    inverted_color = ''.join(f'{255 - int(color[i:i + 2], 16):02x}' for i in range(0, 6, 2))
    return f'{strif('#', hashtag)}{inverted_color}{strif(color[-2:], len(color) > 6)}'


def format_distance(distance: Quantity) -> str:
    return distance.convert(multiplier=kilo).format(precision=1) \
        if distance >= Quantity(1000, 'm') else distance.format(precision=0)


def absolute_path(path: str | os.PathLike[str]) -> str:
    return os.path.abspath(path)


def prepare_path(path: str | os.PathLike[str], path_is_directory: bool = False) -> str | os.PathLike[str]:
    directory_path = path if path_is_directory else os.path.dirname(absolute_path(path))
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
    return path


def prepare_file(path: str | os.PathLike[str], initial_content: str = '', override: bool = False) -> str | os.PathLike[str]:
    if not os.path.exists(path) or override:
        with open(prepare_path(path), 'w' if override else 'x') as file:
            file.write(f'{initial_content}')
    return path


def clear_directory(directory: str | os.PathLike[str]) -> None:
    for file in os.listdir(directory):
        file_path: str = os.path.join(directory, file)
        if os.path.isfile(file_path):
            os.remove(file_path)


def system_open(file_path: str | os.PathLike[str]) -> None:
    if platform.system() == 'Darwin':  # macOS
        subprocess.call(('open', file_path))
    elif platform.system() == 'Windows':  # windows
        os.startfile(file_path)
    else:  # linux
        subprocess.call(('xdg-open', file_path))


def file_last_modified(file_path: str | os.PathLike[str]) -> datetime | None:
    return datetime.fromtimestamp(os.path.getmtime(file_path)) if os.path.exists(file_path) else None


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
            error(f'File {absolute_path(file)} is empty')
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


class HashableSet(Generic[T], SortedSet[T]):
    def __init__(self, iterable: Iterable[T] = ()):
        super().__init__(iterable)

    def __hash__(self):
        return hash(tuple(self))

    def __repr__(self):
        return f'HashableSet({super().__repr__()})'
