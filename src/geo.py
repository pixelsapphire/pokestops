from __future__ import annotations
from math import atan2, pi
from pyproj import Geod
from quantity import *
from typing import Any, Generic, Protocol, Sequence, TypeVar
from util import prepare_path, sign, to_css

TFloatSeq = TypeVar("TFloatSeq", bound=Sequence[float])
__geod__ = Geod(ellps='WGS84')


class FloatVectorLike(Protocol):
    def __getitem__(self, index: int) -> float: ...


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

    @staticmethod
    def parse(string: str) -> geopoint:
        return geopoint(*map(float, string.split(',')))

    @staticmethod
    def distance(a: geopoint, b: geopoint) -> Quantity:
        return Quantity(__geod__.inv(a.longitude, a.latitude, b.longitude, b.latitude)[2], 'm')


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


class LineSegment(Generic[TFloatSeq], Sequence[TFloatSeq]):
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


class MapMetrics:
    def __init__(self, points: list[geopoint]):
        self.lat_min: float = min(p.latitude for p in points)
        self.lat_max: float = max(p.latitude for p in points)
        self.lon_min: float = min(p.longitude for p in points)
        self.lon_max: float = max(p.longitude for p in points)
        self.lat_range: float = self.lat_max - self.lat_min
        self.lon_range: float = self.lon_max - self.lon_min
        self.coord_range: float = max(self.lat_range, self.lon_range)
        self.scale_factor: float = 1000 / self.coord_range

    def transform_point(self, point: geopoint) -> vector2f:
        return vector2f(12 + (point.longitude - self.lon_min) * self.scale_factor,
                        12 + (self.lat_max - point.latitude) * self.scale_factor)


def next_midpoint(previous_dir: vector2f, current_point: vector2f, next_point: vector2f,
                  alternative_direction: bool) -> tuple[vector2f, vector2f, vector2f]:
    delta: vector2f = next_point - current_point
    distance: vector2f = vector2f(abs(delta.x), abs(delta.y))
    current_dir_1: vector2f = vector2f(sign(delta.x), sign(delta.y))
    current_dir_2: vector2f = vector2f(sign(delta.x), 0) if distance.x > distance.y \
        else vector2f(0, sign(delta.y)) if distance.y > distance.x else current_dir_1
    midpoint_offset_1: float = min(distance.x, distance.y)
    midpoint_offset_2: float = max(distance.x, distance.y) - midpoint_offset_1
    if not previous_dir:
        if midpoint_offset_1 > midpoint_offset_2:
            dir_before_midpoint: vector2f = current_dir_1 if not alternative_direction else current_dir_2
        else:
            dir_before_midpoint: vector2f = current_dir_2 if not alternative_direction else current_dir_1
    else:
        if previous_dir == current_dir_1 or previous_dir == current_dir_2:
            dir_before_midpoint: vector2f = previous_dir
        elif vector2f.angle_offset(previous_dir, current_dir_1) < vector2f.angle_offset(previous_dir, current_dir_2):
            dir_before_midpoint: vector2f = current_dir_1 if not alternative_direction else current_dir_2
        else:
            dir_before_midpoint: vector2f = current_dir_2 if not alternative_direction else current_dir_1
    if dir_before_midpoint == current_dir_1:
        midpoint_offset: float = midpoint_offset_1
        dir_after_midpoint: vector2f = current_dir_2
    else:
        midpoint_offset: float = midpoint_offset_2
        dir_after_midpoint: vector2f = current_dir_1
    midpoint: vector2f = current_point + dir_before_midpoint * midpoint_offset
    return dir_before_midpoint, midpoint, dir_after_midpoint


def midpoints(sequence: list[vector2f]) -> list[vector2f]:
    if not sequence:
        return []
    new_sequence: list[vector2f] = []
    previous_dir: vector2f = vector2f(0, 0)
    current_point: vector2f = sequence[0]
    new_sequence.append(current_point)

    for i in range(1, len(sequence)):
        next_point: vector2f = sequence[i]
        dir_before_midpoint1, midpoint1, dir_after_midpoint1 = next_midpoint(previous_dir, current_point, next_point, False)
        dir_before_midpoint2, midpoint2, dir_after_midpoint2 = next_midpoint(previous_dir, current_point, next_point, True)
        diff1: float = vector2f.angle_offset(previous_dir, dir_before_midpoint1)
        diff2: float = vector2f.angle_offset(previous_dir, dir_before_midpoint2)
        midpoint, dir_after_midpoint = (midpoint1, dir_after_midpoint1) if diff1 >= diff2 else (midpoint2, dir_after_midpoint2)
        new_sequence.append(midpoint)
        new_sequence.append(next_point)
        previous_dir = dir_after_midpoint
        current_point = next_point
    return new_sequence


def create_route_diagram(points: list[geopoint], color: str, output_path: str) -> None:
    metrics: MapMetrics = MapMetrics(points)
    points: list[vector2f] = list(map(metrics.transform_point, points))
    with open(prepare_path(output_path), 'w') as file:
        file.write(f'<svg'
                   f' width="{24 + 1000 * metrics.lon_range / metrics.coord_range:.1f}"'
                   f' height="{24 + 1000 * metrics.lat_range / metrics.coord_range:.1f}"'
                   f' xmlns="http://www.w3.org/2000/svg">\n')
        sequence: list[vector2f] = midpoints(points)
        file.write(f'<path d="M{sequence[0].x:.1f} {sequence[0].y:.1f} ')
        for p in sequence[1:]:
            file.write(f'L{p.x:.1f} {p.y:.1f} ')
        file.write(f'" />\n')
        for p in sequence[::2]:
            file.write(f'<circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="8" />\n')
        file.write(f'<style>\n{to_css({
            'circle': {
                'fill': 'white',
                'stroke': f'#{color}' if color.lower() != 'ffffff' else 'black',
                'stroke-width': '4'
            },
            'path': {
                'fill': 'none',
                'stroke': f'#{color}',
                'stroke-width': '8'
            }
        })}</style>\n')
        file.write('</svg>')


def create_multi_route_map(routes: list[list[geopoint]], color: str, output_path: str) -> None:
    flat_points: list[geopoint] = [point for route in routes for point in route if route]
    metrics: MapMetrics = MapMetrics(flat_points)
    with open(prepare_path(output_path), 'w') as file:
        file.write(f'<svg'
                   f' width="{24 + 1000 * metrics.lon_range / metrics.coord_range:.1f}"'
                   f' height="{24 + 1000 * metrics.lat_range / metrics.coord_range:.1f}"'
                   f' xmlns="http://www.w3.org/2000/svg">\n')
        foreground: list[str] = []
        for route in routes:
            sequence: list[vector2f] = list(map(metrics.transform_point, route))
            file.write(f'<path d="M{sequence[0].x:.1f} {sequence[0].y:.1f} ')
            for p in sequence[1:]:
                file.write(f'L{p.x:.1f} {p.y:.1f} ')
            file.write(f'" />\n')
            for p in (sequence[0], sequence[-1]):
                foreground.append(f'<circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="8" />\n')
        file.write(''.join(foreground))
        file.write(f'<style>\n{to_css({
            'circle': {
                'fill': 'white',
                'stroke': f'#{color}' if color.lower() != 'ffffff' else 'black',
                'stroke-width': '4'
            },
            'path': {
                'fill': 'none',
                'stroke': f'#{color}',
                'stroke-width': '8'
            }
        })}</style>\n')
        file.write('</svg>')
