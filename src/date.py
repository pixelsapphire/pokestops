from __future__ import annotations
import datetime
import re
from util import coalesce, RichComparisonT
from typing import Final, Self


class DateAndOrder:
    never: Final[Self] = None
    distant_past: Final[Self] = None
    distant_future: Final[Self] = None

    __months__: Final[list[str]] = ['January', 'February', 'March', 'April', 'May', 'June',
                                    'July', 'August', 'September', 'October', 'November', 'December']

    def __init__(self, *, year: int | None = None, month: int | None = None, day: int | None = None,
                 date_string: str | None = '', string_format: str | None = None, number_in_day: int | None = None):
        if date_string:
            if string_format:
                format_parts: list[str] = string_format.split('|')
                if len(string_format) == 0 or len(format_parts) not in (1, 2, 4):
                    raise ValueError(f'Invalid format specifier \'{string_format}\' for object of type \'{type(self)}\'')
                if len(format_parts) > 1 and date_string == format_parts[1]:  # never
                    self._year: int = -1
                    self._month: int = -1
                    self._day: int = -1
                    self._number_in_day: int = 0
                elif len(format_parts) == 4 and date_string in [format_parts[2], format_parts[3]]:  # distant past/future
                    self._year: int = -1
                    self._month: int = -1
                    self._day: int = -1
                    self._number_in_day: int = -1 if date_string == format_parts[2] else 1
                else:
                    regex: str = (format_parts[0].replace('d', r'(\d{2})').replace('m', r'(\d{2})')
                                  .replace('y', r'(\d{4})').replace('n', r'(\d+)'))
                    match = re.match(regex, date_string)
                    placeholders_order: list[str] = re.findall(r'[ymdn]', format_parts[0])
                    if match:
                        groups: tuple[str, ...] = match.groups()
                        self._year: int = int(groups[placeholders_order.index('y')]) if 'y' in placeholders_order else 0
                        self._month: int = int(groups[placeholders_order.index('m')]) if 'm' in placeholders_order else 0
                        self._day: int = int(groups[placeholders_order.index('d')]) if 'd' in placeholders_order else 0
                        if 'n' in placeholders_order and number_in_day is not None:
                            raise ValueError(
                                'Cannot pass argument number_in_day if the number is already present in date_string')
                        elif 'n' in placeholders_order:
                            self._number_in_day: int = int(groups[placeholders_order.index('n')])
                        elif number_in_day is not None:
                            self._number_in_day: int = number_in_day
                        else:
                            self._number_in_day: int = 0
                    else:
                        raise ValueError(f'Invalid date string \'{date_string}\' with format \'{string_format}\'')
            else:
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
            self._year: int = year
            self._month: int = month
            self._day: int = day
            self._number_in_day: int = coalesce(number_in_day, 0)
        else:
            raise ValueError('Must pass either (date_string, [number_in_day]), (year, month, day, [number_in_day]), '
                             'or use DateAndOrder.long_time_ago or DateAndOrder.unknown')

    def __eq__(self, other):
        return self.__cmp_key__() == other.__cmp_key__() if isinstance(other, DateAndOrder) else False

    def __le__(self, other):
        if DateAndOrder.never in (self, other):
            return self == DateAndOrder.never
        if DateAndOrder.distant_past in (self, other):
            return self == DateAndOrder.distant_past
        if DateAndOrder.distant_future in (self, other):
            return other == DateAndOrder.distant_future
        return self.__cmp_key__() < other.__cmp_key__() if isinstance(other, DateAndOrder) else bool(self) < bool(other)

    def __lt__(self, other):
        return self <= other and self != other

    def __ge__(self, other):
        if DateAndOrder.never in (self, other):
            return other == DateAndOrder.never
        if DateAndOrder.distant_past in (self, other):
            return other == DateAndOrder.distant_past
        if DateAndOrder.distant_future in (self, other):
            return self == DateAndOrder.distant_future
        return self.__cmp_key__() > other.__cmp_key__() if isinstance(other, DateAndOrder) else bool(self) > bool(other)

    def __gt__(self, other):
        return self >= other and self != other

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
        if len(format_spec) == 0 or len(format_parts) not in (1, 2, 4):
            raise ValueError(f'Invalid format specifier \'{format_spec}\' for object of type \'{type(self)}\'')
        if not self.is_known():
            if len(format_parts) == 2 or self == DateAndOrder.never:
                return format_parts[1]
            return format_parts[2] if self == DateAndOrder.distant_past else format_parts[3]
        else:
            formatted_string: str = format_parts[0]
            if 'y' in format_spec:
                formatted_string = formatted_string.replace('y', f'{self._year:04}')
            if 'm' in format_spec:
                formatted_string = formatted_string.replace('m', f'{self._month:02}')
            if 'M' in format_spec:
                formatted_string = formatted_string.replace('M', f'{self.__months__[self._month - 1]}')
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
        return self != DateAndOrder.never and self != DateAndOrder.distant_past and self != DateAndOrder.distant_future

    def format(self, format_spec: str) -> str:
        return self.__format__(format_spec)

    def to_string(self, number: bool = True) -> str:
        return self.__str__() if number else self.__str__().split(':')[0]

    @staticmethod
    def today() -> DateAndOrder:
        today_date: datetime.date = datetime.date.today()
        return DateAndOrder(year=today_date.year, month=today_date.month, day=today_date.day)


DateAndOrder.never = DateAndOrder(year=-1, month=-1, day=-1, number_in_day=0)  # type: ignore
DateAndOrder.distant_past = DateAndOrder(year=-1, month=-1, day=-1, number_in_day=-1)  # type: ignore
DateAndOrder.distant_future = DateAndOrder(year=-1, month=-1, day=-1, number_in_day=1)  # type: ignore
