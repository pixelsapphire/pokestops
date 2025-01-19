from __future__ import annotations
import json
import re
import ref
import traceback
from abc import ABC
from collections import defaultdict
from date import DateAndOrder
from datetime import datetime
from geo import geopoint
from log import log
from quantity import Duration
from typing import Final, get_args, Literal, Self, TYPE_CHECKING
from util import *

if TYPE_CHECKING:
    from announcements import Announcement
    from player import Player

T = TypeVar('T')
C = TypeVar('C')


def __read_collection__(source: str, identity: C, mapper: Callable[..., T], combiner: Callable[[C, T], None]) -> C:
    with open(source, 'r') as file:
        reader = csv.reader(file)
        next(reader)
        collection: C = identity
        for row in reader:
            if row and not row[0].lstrip().startswith('#'):
                try:
                    combiner(collection, mapper(*row))
                except (IndexError, TypeError) as e:
                    error(f'Error while processing row {row}: {e}')
                    error(traceback.format_exc())
        log('Done!')
        return collection


class JsonSerializable(ABC):
    def __json_entry__(self) -> str: ...

    @staticmethod
    def json_entry(obj: JsonSerializable) -> str:
        return obj.__json_entry__()


class Discovery[RichComparisonT]:
    def __init__(self, item: RichComparisonT, date: DateAndOrder = DateAndOrder.distant_past):
        self.item: RichComparisonT = item
        self.date: DateAndOrder = date

    def __hash__(self):
        return hash(self.item) + hash(self.date)

    def __lt__(self, other: Self):
        if not isinstance(other, type(self)):
            return False
        elif self.date != other.date:
            return self.date < other.date
        else:
            return self.item > other.item if isinstance(self.item, SupportsDunderGT) else not self.item < other.item


class Stop(JsonSerializable):

    def __init__(self, short_name: str, full_name: str, latitude: str, longitude: str, zone: str, routes: str):
        self.short_name: str = short_name
        self.full_name: str = full_name
        self.location: geopoint = geopoint(float(latitude), float(longitude))
        self.zone: str = zone
        self.visits: list[Discovery] = []
        self.regions: list[Region] = []
        self.lines: list[tuple[str, str]] = list(map(lambda e: (e[:e.index(':')], e[e.index(':') + 1:]),
                                                     routes.split('&'))) if routes else []
        self.terminals_progress: list[tuple[Literal['arrival', 'departure'], Player, Terminal]] = []

    def __hash__(self):
        return hash(self.short_name)

    def __eq__(self, other):
        return self.short_name == other.short_name if isinstance(other, type(self)) else False

    def __lt__(self, other):
        return self.short_name < other.short_name if isinstance(other, type(self)) else False

    def in_any_of(self, towns: set[str]) -> bool:
        return '/' in self.full_name and self.full_name[:self.full_name.index('/')] in towns

    def is_visited(self, include_ev: bool = True) -> bool:
        return any(visit.date.is_known() or include_ev for visit in self.visits)

    def is_visited_by(self, player: str | Player, include_ev: bool = True) -> bool:
        from player import Player
        name: str = player.nickname if isinstance(player, Player) else player
        return any(name == visit.item.nickname and (visit.date.is_known() or include_ev) for visit in self.visits)

    def date_visited_by(self, player: Player, include_ev: bool = True) -> DateAndOrder:
        return next((visit.date for visit in self.visits
                     if player.nickname == visit.item.nickname and (visit.date.is_known() or include_ev)))

    def add_visit(self, player: Player, date: DateAndOrder = DateAndOrder.distant_past):
        if self.is_visited_by(player):
            error(f'{player.nickname} has already visited stop {self.short_name}, '
                  f'remove the {f'{date.to_string(number=False)} ' if date else ''}'
                  f'entry from her {'' if date else 'EV '}stops file')
        self.visits.append(Discovery(player, date))

    def mark_closest_arrival(self, player: Player, terminal: Terminal):
        self.terminals_progress.append(('arrival', player, terminal))

    def mark_closest_departure(self, player: Player, terminal: Terminal):
        self.terminals_progress.append(('departure', player, terminal))

    def marker(self) -> str:
        number = int(self.short_name[-2:])
        if 0 < number < 20:
            return 'B'
        elif 20 < number < 40:
            return 'T'
        elif 40 < number < 70:
            return 'R'
        elif 70 < number < 90:
            return 'H'
        else:
            return 'E'

    @staticmethod
    def dummy(short_name: str, full_name: str) -> Stop:
        return Stop(short_name, full_name, '0', '0', '', '')

    @staticmethod
    def read_stops(source: str, db: Database) -> tuple[dict[str, Stop], dict[str, SortedSet[Stop]]]:
        log(f'  Reading stops data from {source}... ', end='')
        stops: dict[str, Stop] = {}
        stop_groups: dict[str, SortedSet[Stop]] = {}
        with open(source, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                stop = Stop(row[1], row[2], row[3], row[4], row[5], row[6] if len(row) > 6 else '')
                region = next((r for r in db.regions_without_district() if stop in r), None)
                if not region:
                    raise ValueError(f'Stop {stop.full_name} [{stop.short_name}] not in any region')
                region.add_stop(stop)
                db.district.add_stop(stop)
                stops[row[1]] = stop
                if stop.full_name not in stop_groups:
                    stop_groups[stop.full_name] = SortedSet()
                stop_groups[stop.full_name].add(stop)
        log('Done!')
        return stops, stop_groups

    def __json_entry__(self) -> str:
        return (f'"{self.short_name}":{{'
                f'n:"{self.full_name}",'
                f'lt:{self.location.latitude},'
                f'ln:{self.location.longitude},'
                f'l:[{','.join(f'["{line}","{destination}"]' for line, destination in self.lines)}],'
                f'{f'v:[{','.join(f'["{visit.item.nickname}","{visit.date:y-m-d|}"]'
                                  for visit in sorted(self.visits))}],' if self.visits else ''}'
                f'}},')


class TerminalProgress:
    def __init__(self, terminal: Terminal, player: Player, closest_arrival: Stop, closest_departure: Stop):
        self.terminal: Terminal = terminal
        self.player: Player = player
        self.closest_arrival: Stop = closest_arrival
        self.closest_departure: Stop = closest_departure

    def arrived(self) -> bool:
        return self.closest_arrival == self.terminal.arrival_stop

    def departed(self) -> bool:
        return self.closest_departure == self.terminal.departure_stop

    def reached(self) -> bool:
        return self.arrived() or self.departed()

    def completed(self):
        return self.arrived() and self.departed()


class Terminal(JsonSerializable):
    def __init__(self, terminal_id: str, name: str, latitude: str, longitude: str, arrival_stop: Stop, departure_stop: Stop):
        self.id: str = terminal_id
        self.name: str = name
        self.latitude: float = float(latitude)
        self.longitude: float = float(longitude)
        self.arrival_stop: Stop = arrival_stop
        self.departure_stop: Stop = departure_stop
        self.progress: list[TerminalProgress] = []

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id if isinstance(other, type(self)) else False

    def reached_by(self, player: Player) -> bool:
        return any(p.reached() for p in self.progress if p.player == player)

    def anybody_reached(self) -> bool:
        return any(p.reached() for p in self.progress)

    def completed_by(self, player: Player) -> bool:
        progress: TerminalProgress | None = next((p for p in self.progress if p.player == player), None)
        return progress and progress.completed()

    def add_player_progress(self, player: Player, closest_arrival: Stop, closest_departure: Stop) -> None:
        progress: TerminalProgress = TerminalProgress(self, player, closest_arrival, closest_departure)
        self.progress.append(progress)
        if not progress.arrived():
            closest_arrival.mark_closest_arrival(player, self)
        if not progress.departed():
            closest_departure.mark_closest_departure(player, self)

    @staticmethod
    def read_list(source: str, stops: dict[str, Stop]) -> list[Terminal]:
        log(f'  Reading terminals data from {source}... ', end='')
        constructor = lambda *row: Terminal(row[0], row[1], row[2], row[3], stops.get(row[4]), stops.get(row[5]))
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], constructor, list.append)

    def __json_entry__(self) -> str:
        return (f'"{self.id}":{{'
                f'n:"{self.name}",'
                f'lt:{self.latitude},'
                f'ln:{self.longitude}'
                f'}},')


class StopChange:
    def __init__(self, date: DateAndOrder, old_stop: Stop = None, new_stop: Stop | None = None):
        self.date: DateAndOrder = date
        self.old_stop: Stop | None = old_stop
        self.new_stop: Stop | None = new_stop
        if old_stop is None and new_stop is None:
            raise ValueError('Empty change')

    def affects(self, stop: Stop) -> bool:
        return stop == self.old_stop or stop == self.new_stop

    def is_effective(self) -> bool:
        return DateAndOrder.today() >= self.date

    def is_additional(self) -> bool:
        return self.old_stop is None

    def is_removal(self) -> bool:
        return self.new_stop is None

    def is_modification(self) -> bool:
        return self.old_stop is not None and self.new_stop is not None

    def is_id_change(self) -> bool:
        return self.is_modification() and self.old_stop.short_name != self.new_stop.short_name

    def is_name_change(self) -> bool:
        return self.is_modification() and self.old_stop.full_name != self.new_stop.full_name

    @staticmethod
    def read_list(source: str) -> list[StopChange]:
        log(f'  Reading scheduled stop changes data from {source}... ', end='')
        constructor = lambda *row: StopChange(DateAndOrder(date_string=row[0]),
                                              Stop.dummy(row[1], row[2]) if row[1] and row[2] else None,
                                              Stop.dummy(row[3], row[4]) if row[3] and row[4] else None)
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], constructor, list.append)


class Carrier(JsonSerializable):
    def __init__(self, symbol: str, short_name: str, full_name: str):
        self.symbol: str = symbol
        self.short_name: str = short_name
        self.full_name: str = full_name

    def __hash__(self):
        return hash(self.symbol)

    def __eq__(self, other):
        return self.symbol == other.symbol if isinstance(other, type(self)) else False

    @staticmethod
    def read_dict(source: str) -> dict[str, Carrier]:
        log(f'  Reading carriers data from {source}... ', end='')
        return __read_collection__(source, {}, Carrier, lambda c, v: c.update({v.symbol: v}))

    def __json_entry__(self) -> str:
        return (f'"{self.symbol}":{{'
                f'n:"{self.full_name}",'
                f'}},')


class VehicleModel(JsonSerializable):
    def __init__(self, model_id: str, kind: str, kind_detailed: str, brand: str, model: str, seats: str | int, lore: str):
        self.model_id: str = model_id
        self.kind: str = kind
        self.kind_detailed: str = kind_detailed
        self.brand: str = brand
        self.model: str = model
        self.seats: int | None = int(seats) if (isinstance(seats, str) and seats.isdigit()) or isinstance(seats, int) else None
        self.lore: str = lore

    def __hash__(self):
        return hash(self.model_id)

    def __eq__(self, other):
        return self.model_id == other.model_id if isinstance(other, type(self)) else False

    @staticmethod
    def read_dict(source: str) -> dict[str, 'VehicleModel']:
        log(f'  Reading vehicle models data from {source}... ', end='')
        return __read_collection__(source, {}, VehicleModel, lambda c, v: c.update({v.model_id: v}))

    def __json_entry__(self) -> str:
        return (f'"{self.model_id}":{{'
                f'k:"{self.kind_detailed}",'
                f'b:"{self.brand}",'
                f'm:"{self.model}",'
                f'{f's:{self.seats},' if self.seats else ''}'
                f'l:"{self.lore}",'
                f'}},')


class Vehicle(JsonSerializable):
    def __init__(self, vehicle_id: str, license_plate: str, carrier: Carrier, model: VehicleModel, image_url: str, lore: str):
        self.vehicle_id: str = vehicle_id
        self.license_plate: str = license_plate
        self.carrier: Carrier = carrier
        self.model: VehicleModel = model
        self.image_url: str | None = image_url if image_url else None
        self.lore: str = lore
        self.discoveries: list[Discovery] = []

    def __hash__(self):
        return hash(self.vehicle_id)

    def __eq__(self, other):
        return self.vehicle_id == other.vehicle_id if isinstance(other, type(self)) else False

    def __lt__(self, other):
        return self.__cmp_key__() < other.__cmp_key__() if isinstance(other, type(self)) else False

    def __cmp_key__(self) -> RichComparisonT:
        if self.vehicle_id.isdigit():
            return int(self.vehicle_id), ''
        elif '+' in self.vehicle_id:
            return int(self.vehicle_id[:self.vehicle_id.index('+')]), ''
        elif re.search(r'\d', self.vehicle_id):
            return int(re.sub(r'\D', '', self.vehicle_id)), re.sub(r'\d', '_', self.vehicle_id)
        else:
            return 0, self.vehicle_id

    def is_discovered(self) -> bool:
        return len(self.discoveries) > 0

    def discovered_by(self, player: str | Player) -> str | None:
        from player import Player
        name = player.nickname if isinstance(player, Player) else player
        return next((visit.date for visit in self.discoveries if name == visit.item.nickname), None)

    def add_discovery(self, player: Player, date: DateAndOrder):
        if self.discovered_by(player):
            error(f'{player.nickname} has already discovered vehicle #{self.vehicle_id}, '
                  f'remove the {date.to_string(number=False)} entry from her vehicles file')
        self.discoveries.append(Discovery(player, date))

    @staticmethod
    def read_dict(source: str, carriers: dict[str, Carrier], models: dict[str, VehicleModel]) -> dict[str, Vehicle]:
        log(f'  Reading vehicles data from {source}... ', end='')
        constructor = lambda *row: Vehicle(row[0], row[1], carriers.get(row[2]), models.get(row[3]), row[4], row[5])
        return __read_collection__(source, {}, constructor, lambda c, v: c.update({v.vehicle_id: v}))

    def __json_entry__(self) -> str:
        return (f'"{self.vehicle_id}":{{'
                f'{f'p:"{self.license_plate}", ' if self.license_plate else ''}'
                f'{f'm:"{self.model.model_id}", ' if self.model else ''}'
                f'c:"{self.carrier.symbol}",'
                f'{f'i:{f'"{self.image_url}"'},' if self.image_url else ''}'
                f'l:"{self.lore}",'
                f'{f'd:[{','.join(f'["{visit.item.nickname}","{visit.date:y-m-d}"]'
                                  for visit in sorted(self.discoveries))}],' if self.discoveries else ''}'
                f'}},')


class Route:
    def __init__(self, route_id, points: list[geopoint]):
        self.route_id: str = route_id
        self.points: list[geopoint] = points

    @staticmethod
    def read_dict(source: str) -> dict[str, Route]:
        log(f'  Reading routes data from {source}... ', end='')
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        points: dict[str, list[tuple[geopoint, int]]] = __read_collection__(
            source, defaultdict(list),
            lambda r_id, lat, lon, seq: (r_id, (geopoint(lat, lon), int(seq))), lambda c, v: c[v[0]].append(v[1])
        )
        return {route_id: Route(route_id, [point for point, _ in sorted(points, key=lambda p: p[1])])
                for route_id, points in points.items()}


class Line(JsonSerializable):
    def __init__(self, number: str, terminals: str, description: str,
                 background_color: str, text_color: str, routes: list[str], variants: list[list[str]]):
        self.number: str = number
        self.terminals: str = terminals
        self.description: str = description
        self.background_color: str = background_color
        self.text_color: str = text_color
        self.routes: list[str] = routes
        self.variants: list[list[str]] = variants
        self.discoveries: list[Discovery] = []
        if self.background_color == self.text_color:
            self.text_color = invert_hex_color(self.text_color)

    def __eq__(self, other):
        return self.number == other.number if isinstance(other, type(self)) else False

    def __hash__(self):
        return hash(self.number)

    def __repr__(self):
        return f'Line {self.number}'

    def __lt__(self, other):
        return self.__cmp_key__() < other.__cmp_key__() if isinstance(other, type(self)) else False

    def __cmp_key__(self) -> RichComparisonT:
        if self.number.isdigit():
            return int(self.number), ''
        else:
            return int(re.sub(r'\D', '', self.number)) - 1000, re.sub(r'\d', '_', self.number)

    def is_discovered(self) -> bool:
        return len(self.discoveries) > 0

    def discovered_by(self, player: str | Player) -> str | None:
        from player import Player
        name = player.nickname if isinstance(player, Player) else player
        return next((visit.date for visit in self.discoveries if name == visit.item.nickname), None)

    def add_discovery(self, player: Player, date: DateAndOrder):
        if self.discovered_by(player):
            error(f'{player.nickname} already discovered line {self.number}, '
                  f'remove the {date.to_string(number=False)} entry from her lines file')
        self.discoveries.append(Discovery(player, date))

    def kind(self) -> str:
        if self.number.startswith('T'):
            return 'substitute'
        if not self.number.isdigit():
            return 'special'
        number: int = int(self.number)
        if number == 0 or number == 100:
            return 'tourist'
        if number == 24:
            return 'Christmas tram'
        if 1 <= number <= 89:
            return 'tram'
        if 90 <= number <= 99:
            return 'temporary tram'
        if 101 <= number <= 140:
            return 'minibus'
        if 141 <= number <= 199:
            return 'bus'
        if 200 <= number <= 209:
            return 'night tram'
        if 210 <= number <= 299:
            return 'night bus'
        return 'suburban bus'

    @staticmethod
    def dummy(number: str) -> Line:
        return Line(number, '', '', '525252', 'ffffff', [], [])

    @staticmethod
    def read_dict(source: str) -> dict[str, Line]:  # TODO attach actual routes and stops instead of ids
        log(f'  Reading routes data from {source}... ', end='')
        constructor = lambda *row: Line(row[2], row[3].split('|')[0], row[4].split('|')[0].split('^')[0], row[6], row[7],
                                        row[8].split('&'), list(map(lambda seq: seq.split('&'), row[9].split('|'))))
        return __read_collection__(source, {}, constructor, lambda c, v: c.update({v.number: v}))

    def __json_entry__(self) -> str:
        return (f'"{self.number}":{{'
                f'bc:"{self.background_color}",'
                f'tc:"{self.text_color}",'
                f'k:"{self.kind()}",'
                f't:"{self.terminals}",'
                f'rd:"{self.description}",'
                f'r:[{','.join(f'[{",".join(f"\"{stop}\"" for stop in seq)}]' for seq in self.variants)}],'
                f'{f'd:[{','.join(f'["{visit.item.nickname}","{visit.date:y-m-d}"]'
                                  for visit in sorted(self.discoveries))}],' if self.discoveries else ''}'
                f'}},')


class Region:
    def __init__(self, number: int, short_name: str, full_name: str, predicate: Callable[[Stop], bool]):
        self.number: int = number
        self.short_name: str = short_name
        self.full_name: str = full_name
        self.predicate: Callable[[Stop], bool] = predicate
        self.stops: set[Stop] = set()

    def __contains__(self, stop: Stop) -> bool:
        return self.predicate(stop)

    def __lt__(self, other) -> bool:
        return self.number < other.number if isinstance(other, type(self)) else False

    def __hash__(self):
        return hash(self.short_name)

    def __eq__(self, other):
        return self.short_name == other.short_name if isinstance(other, type(self)) else False

    def add_stop(self, s: Stop) -> None:
        self.stops.add(s)
        s.regions.append(self)

    @staticmethod
    def __resolve_predicate__(predicate_object: dict[str, Any]) -> Callable[[Stop], bool]:
        predicate_type = predicate_object['type']
        if predicate_type == 'true':
            return lambda _: True
        elif predicate_type == 'or':
            return lambda s: any(Region.__resolve_predicate__(operand)(s) for operand in predicate_object['operands'])
        elif predicate_type == 'equals':
            return lambda s: getattr(s, predicate_object['field']) == predicate_object['value']
        elif predicate_type == 'does_not_contain':
            return lambda s: predicate_object['value'] not in getattr(s, predicate_object['field'])
        elif predicate_type == 'in_any_of':
            return lambda s: s.in_any_of(predicate_object['towns'])
        else:
            raise ValueError(f'Unknown predicate type: {predicate_type}')

    @staticmethod
    def read_regions(source: str) -> tuple[Region, dict[str, Region]]:
        log(f'  Reading regions data from {source}... ', end='')
        with (open(source, 'r') as file):
            index = json.load(file)
            regions = [Region(region['number'], region['short_name'], region['full_name'],
                              Region.__resolve_predicate__(region['predicate']))
                       for region in index['regions']]
            district: Region = find_first(lambda r: r.short_name == index['district'], regions)
            log('Done!')
            return district, {
                district.short_name: district,
                **{region.short_name: region for region in regions if region != district},
            }


class RaidElement(ABC):
    def __init__(self, departure: datetime | None, arrival: datetime | None, comment: str | None = None):
        self.departure: datetime | None = departure
        self.arrival: datetime | None = arrival
        self.comment: str | None = comment

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RaidElement:
        clas: Any = globals().get(f'{data['type'][0].upper()}{data['type'][1:]}RaidElement')
        if clas is None or not issubclass(clas, RaidElement) or clas.from_dict == RaidElement.from_dict:
            raise ValueError(f'Unknown raid element type: {data['type']}')
        return clas.from_dict(data)


class PointRaidElement(RaidElement):
    def __init__(self, phase: str, location: geopoint, stop: str, icon: str | None = None, comment: str | None = None,
                 departure: datetime | None = None, arrival: datetime | None = None):
        super().__init__(departure, arrival, comment)
        self.phase: str = phase
        self.location: geopoint = location
        self.stop: str = stop
        self.icon: str | None = icon

    @property
    def time(self) -> datetime | None:
        return self.departure or self.arrival

    def marker(self) -> str:
        if self.icon is not None:
            return self.icon
        elif self.phase == 'start' or self.phase == 'finish':
            return 'F'
        elif self.phase == 'departure':
            return 'D'
        elif self.phase == 'arrival':
            return 'A'
        elif self.phase == 'transfer':
            return 'M'
        elif self.phase == 'break':
            return 'b'
        else:
            return 'B'

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PointRaidElement:
        return PointRaidElement(data['phase'], geopoint.parse(data['location']), data['stop'],
                                data.get('icon'), data.get('comment'))


class RepeatedPointRaidElement(RaidElement):
    def __init__(self, points: list[PointRaidElement]):
        super().__init__(None, None)
        if len(points) == 0:
            raise ValueError('RepeatedPointRaidElement must contain at least one point')
        if any(p.location != points[0].location or p.stop != points[0].stop for p in points):
            raise ValueError('All points in RepeatedPointRaidElement must have the same location and stop name')
        self.points: list[PointRaidElement] = points
        self.location: geopoint = points[0].location
        self.stop = points[0].stop

    def marker(self) -> str:
        return ''.join(point.marker() for point in self.points)

    def add(self, point: PointRaidElement):
        self.points.append(point)


class RouteRaidElement(RaidElement):
    def __init__(self, departure: datetime | None, arrival: datetime | None,
                 transport_method: str, shape: list[geopoint], line_number: str | None = None, comment: str | None = None):
        super().__init__(departure, arrival, comment)
        self.transport_method: str = transport_method
        self.shape: list[geopoint] = shape
        self.line_number: str | None = line_number

    @property
    @memoized
    def total_length(self) -> Quantity:
        return sum((geopoint.distance(self.shape[i], self.shape[i + 1]) for i in range(len(self.shape) - 1)), Quantity(0, 'm'))

    @property
    @memoized
    def total_time(self) -> Duration:
        return Duration.as_difference(self.departure, self.arrival) \
            if self.departure is not None and self.arrival is not None else Duration(0)

    def shape_defined(self):
        return len(self.shape) > 0

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RouteRaidElement:
        return RouteRaidElement(datetime.fromisoformat(data['departure']) if 'departure' in data else None,
                                datetime.fromisoformat(data['arrival']) if 'arrival' in data else None,
                                data['transport_method'], [geopoint.parse(point) for point in data['shape'].split('&')],
                                data.get('line'), data.get('comment'))


class TransferRaidElement(RouteRaidElement):
    def __init__(self):
        super().__init__(None, None, 'foot', [])


class Raid:
    def __init__(self, raid_id: str, icon: str, date: DateAndOrder, participants: list[Player], elements: list[RaidElement]):
        self.raid_id: Final[str] = raid_id
        self.icon: Final[str] = icon
        self.date: Final[DateAndOrder] = date
        self._participants: list[Player] = participants
        self._elements: list[RaidElement] = elements

    @property
    def participants(self) -> list[Player]:
        return self._participants

    @property
    def elements(self) -> list[RaidElement]:
        return self._elements

    @property
    @memoized
    def map_elements(self) -> list[RaidElement]:

        elements_with_transfers: list[RaidElement] = []
        i: int = 0
        while i < len(self.elements) - 2:
            e0, e1, e2 = self.elements[i], self.elements[i + 1], self.elements[i + 2]
            if (isinstance(e0, PointRaidElement) and isinstance(e1, RouteRaidElement) and isinstance(e2, PointRaidElement) and
                    e0.stop == e2.stop and e0.phase == 'arrival' and e1.transport_method == 'foot' and e2.phase == 'departure'):
                elements_with_transfers.append(PointRaidElement('transfer', e0.location, e0.stop, None, None, e2.time, e0.time))
                elements_with_transfers.append(e1)
                i += 2
            else:
                elements_with_transfers.append(e0)
            i += 1
        while i < len(self.elements):
            elements_with_transfers.append(self.elements[i])
            i += 1

        marked_stops: dict[str, RepeatedPointRaidElement] = {}
        raid_map_elements: list[RaidElement] = []
        for element in elements_with_transfers:
            if not isinstance(element, PointRaidElement):
                raid_map_elements.append(element)
            else:
                if element.stop not in marked_stops:
                    marked_stops[element.stop] = (repeated_stop := RepeatedPointRaidElement([element]))
                    raid_map_elements.append(repeated_stop)
                else:
                    marked_stops[element.stop].add(element)

        return raid_map_elements

    @property
    @memoized
    def stops(self) -> list[PointRaidElement]:
        return [element for element in self._elements if isinstance(element, PointRaidElement)]

    @property
    @memoized
    def routes(self) -> list[RouteRaidElement]:
        return [element for element in self._elements if isinstance(element, RouteRaidElement)]

    @property
    @memoized
    def start_time(self) -> datetime:
        return min(route.departure for route in self.routes if route.departure is not None)

    @property
    @memoized
    def finish_time(self) -> datetime:
        return max(route.arrival for route in self.routes if route.arrival is not None)

    @property
    @memoized
    def total_ride_time(self) -> Duration:
        return sum((route.total_time for route in self.routes if route.transport_method != 'foot'), Duration(0))

    @property
    @memoized
    def total_time(self) -> Duration:
        return Duration.as_difference(self.start_time, self.finish_time)

    @property
    @memoized
    def total_length(self) -> Quantity:
        return sum((route.total_length for route in self.routes), Quantity(0, 'm')).convert(multiplier=kilo)

    @property
    @memoized
    def taken_rides(self) -> int:
        return count(r for r in self.routes if r.transport_method != 'foot')

    @property
    @memoized
    def walking_distance(self) -> Quantity:
        return (sum((route.total_length for route in self.routes if route.transport_method == 'foot'), Quantity(0, 'm'))
                .convert(multiplier=kilo))

    @property
    @memoized
    def visited_stops(self) -> int:
        unique_stops: set[str] = set()
        for stop in self.stops:
            unique_stops.add(re.sub(r'\[.+?]', '[]', stop.stop))
        return len(unique_stops)

    @staticmethod
    def load(raid_id: str, players: list[Player]):
        with open(f'{ref.raiddata_path}/{raid_id}.json', 'r') as file:
            raid_data = json.load(file)
            raid: Raid = Raid(raid_id, raid_data['icon'], DateAndOrder(date_string=raid_data['date']),
                              [find_first(lambda p: p.nickname == nickname, players) for nickname in raid_data['participants']],
                              [RaidElement.from_dict(element) for element in raid_data['elements']])
            for i in range(1, len(raid._elements) - 1):
                if isinstance(raid._elements[i], RouteRaidElement):
                    raid._elements[i - 1].departure = raid._elements[i].departure
                    raid._elements[i + 1].arrival = raid._elements[i].arrival
            i: int = 0
            while i < len(raid._elements) - 1:
                if isinstance(raid._elements[i], PointRaidElement) and isinstance(raid._elements[i + 1], PointRaidElement):
                    raid._elements.insert(i + 1, TransferRaidElement())
                    i += 1
                i += 1
            return raid

    @staticmethod
    def read_list(source: str, players: list[Player]) -> list[Raid]:
        log(f'  Reading raids index from {source} and data from their respective files... ', end='')
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], lambda i: Raid.load(i, players), list.append)


class Database:
    CollectionName = Literal[
        'players', 'progress', 'stops', 'stop_groups', 'terminals', 'carriers', 'regions',
        'vehicles', 'models', 'lines', 'routes', 'raids', 'scheduled_changes', 'announcements']
    __stars__: dict[tuple[int, int], int] = {(1, 1): 1, (2, 2): 2, (3, 4): 3, (5, 7): 4, (8, 100): 5}

    def __init__(self, players: list[Player], progress: dict[str, dict[str, float]],
                 stops: dict[str, Stop], stop_groups: dict[str, SortedSet[Stop]], terminals: list[Terminal],
                 carriers: dict[str, Carrier], regions: dict[str, Region], district: Region,
                 vehicles: dict[str, Vehicle], models: dict[str, VehicleModel],
                 routes: dict[str, Route], lines: dict[str, Line], raids: list[Raid],
                 scheduled_changes: list[StopChange], announcements: list[Announcement],

                 *, is_old_data: bool = False):
        self.__old_data__: Database | None = Database.partial(is_old_data=True) if is_old_data else None
        self.__reported_collections__: set[Database.CollectionName] = set()
        self.players: list[Player] = players
        self.progress: dict[str, dict[str, float]] = progress
        self.stops: dict[str, Stop] = stops
        self.stop_groups: dict[str, SortedSet[Stop]] = stop_groups
        self.terminals: list[Terminal] = terminals
        self.carriers: dict[str, Carrier] = carriers
        self.regions: dict[str, Region] = regions
        self.district: Region = district
        self.vehicles: dict[str, Vehicle] = vehicles
        self.models: dict[str, VehicleModel] = models
        self.routes: dict[str, Route] = routes
        self.lines: dict[str, Line] = lines
        self.raids: list[Raid] = raids
        self.scheduled_changes: list[StopChange] = scheduled_changes
        self.announcements: list[Announcement] = announcements

    def __contains__(self, name: CollectionName) -> bool:
        return bool(getattr(self, name))

    @staticmethod
    def partial(players: list[Player] | None = None, progress: dict[str, dict[str, float]] | None = None,
                stops: dict[str, Stop] | None = None, stop_groups: dict[str, SortedSet[Stop]] | None = None,
                terminals: list[Terminal] | None = None, carriers: dict[str, Carrier] | None = None,
                regions: dict[str, Region] | None = None, district: Region | None = None,
                vehicles: dict[str, Vehicle] | None = None, models: dict[str, VehicleModel] | None = None,
                routes: dict[str, Route] | None = None, lines: dict[str, Line] | None = None, raids: list[Raid] | None = None,
                scheduled_changes: list[StopChange] | None = None, announcements: list[Announcement] | None = None,
                *, is_old_data: bool = False) -> Database:
        return Database(players or [], progress or {}, stops or {}, stop_groups or {}, terminals or [],
                        carriers or {}, regions or {}, district or Region(0, '', '', lambda _: False),
                        vehicles or {}, models or {}, routes or {}, lines or {}, raids or [],
                        scheduled_changes or [], announcements or [],
                        is_old_data=is_old_data)

    @staticmethod
    def merge(db1: Database, db2: Database) -> Database:
        if db1 and db2 is None:
            return Database.partial()
        elif (db1 is None) != (db2 is None):
            return coalesce(db1, db2)
        return Database(
            db1.players + db2.players,
            {**db1.progress, **db2.progress},
            {**db1.stops, **db2.stops},
            {**db1.stop_groups, **db2.stop_groups},
            db1.terminals + db2.terminals,
            {**db1.carriers, **db2.carriers},
            {**db1.regions, **db2.regions},
            db1.district,
            {**db1.vehicles, **db2.vehicles},
            {**db1.models, **db2.models},
            {**db1.routes, **db2.routes},
            {**db1.lines, **db2.lines},
            db1.raids + db2.raids,
            db1.scheduled_changes + db2.scheduled_changes,
            db1.announcements + db2.announcements
        )

    @staticmethod
    def get_stars_for_group(size: int):
        return next((stars for ((min_size, max_size), stars) in Database.__stars__.items() if min_size <= size <= max_size), 0)

    def regions_without_district(self) -> list[Region]:
        return [region for region in self.regions.values() if region != self.district]

    def region_of(self, stop: Stop) -> Region:
        return next((region for region in stop.regions if stop and region != self.district), self.district)

    def group_location(self, stop: Stop) -> geopoint:
        stops: SortedSet[Stop] = self.stop_groups[stop.full_name]
        return geopoint(sum(s.location.latitude for s in stops) / len(stops),
                        sum(s.location.longitude for s in stops) / len(stops))

    def get_effective_changes(self):
        return [change for change in self.scheduled_changes if change.is_effective()]

    def report_old_data(self, old_data: Database) -> None:
        self.__old_data__ = Database.merge(self.__old_data__, old_data)
        for collection in get_args(Database.CollectionName):
            if len(getattr(old_data, collection)) > 0:
                self.__reported_collections__.add(collection)

    def make_update_report(self) -> None:
        added_stops: set[Stop] = {s for s in self.stops.values() if s not in self.__old_data__.stops.values()}
        removed_stops: set[Stop] = {s for s in self.__old_data__.stops.values() if s not in self.stops.values()}
        changed_stops: set[tuple[Stop, Stop]] = set()
        added_lines: set[str] = {r for r in self.lines.keys() if r not in self.__old_data__.lines.keys()}
        removed_lines: set[str] = {r for r in self.__old_data__.lines.keys() if r not in self.lines.keys()}
        changed_lines: set[str] = {r for r in self.lines.keys() if r in self.__old_data__.lines.keys() and
                                   self.lines[r].variants != self.__old_data__.lines[r].variants}
        added_announcements: set[Announcement] = {a for a in self.announcements if a not in self.__old_data__.announcements}
        removed_announcements: set[Announcement] = {a for a in self.__old_data__.announcements if a not in self.announcements}
        effective_modifications: list[StopChange] = [c for c in self.get_effective_changes() if c.is_modification()]
        if effective_modifications:
            for change in effective_modifications:
                removed_stops.discard(change.old_stop)
                added_stops.discard(change.new_stop)
                changed_stops.add((change.old_stop, change.new_stop))
        if (added_stops or removed_stops or changed_stops or
                added_lines or removed_lines or changed_lines or added_announcements):
            log('Data has changed, creating report... ', end='')
            lines: int = max(len(added_lines), len(removed_lines), len(changed_lines))
            lexmap: dict[str, float] = create_lexicographic_mapping(file_to_string(ref.lexmap_polish))
            line_key = lambda line: int(line) if line.isdigit() else int(re.sub(r'\D', '', line)) - lines
            stop_key = lambda stop: lexicographic_sequence(f'{stop.full_name}{stop.short_name}', lexmap)
            with (open(prepare_path(ref.report_gtfs), 'w') as file):
                if (('stops' in self.__reported_collections__ and (added_stops or removed_stops or changed_stops)) or
                        ('lines' in self.__reported_collections__ and (added_lines or removed_lines or changed_lines))):
                    file.write('GTFS database updated.\n')
                if 'stops' in self.__reported_collections__:
                    if added_stops:
                        file.write(f'Added stops:\n- {'\n- '.join(f'{s.full_name} [{s.short_name}]'
                                                                  for s in sorted(added_stops, key=stop_key))}\n')
                    if removed_stops:
                        file.write(f'Removed stops:\n- {'\n- '.join(f'{s.full_name} [{s.short_name}]'
                                                                    for s in sorted(removed_stops, key=stop_key))}\n')
                    if changed_stops:
                        file.write(f'Changed stops:\n- {'\n- '
                                   .join(f'{old.full_name} [{old.short_name}] -> {new.full_name} [{new.short_name}]'
                                         for old, new in sorted(changed_stops, key=lambda p: stop_key(p[0])))}\n')
                if 'lines' in self.__reported_collections__:
                    if added_lines:
                        file.write(f'Added lines:\n- {"\n- ".join(sorted(added_lines, key=line_key))}\n')
                    if removed_lines:
                        file.write(f'Removed lines:\n- {"\n- ".join(sorted(removed_lines, key=line_key))}\n')
                    if changed_lines:
                        file.write(f'Changed lines:\n- {"\n- ".join(sorted(changed_lines, key=line_key))}\n')
                if 'announcements' in self.__reported_collections__ and (added_announcements or removed_announcements):
                    file.write('Announcements updated.\n')
                    if added_announcements:
                        file.write(f'New announcements:\n- {"\n- ".join(a.title for a in added_announcements)}\n')
                    if removed_announcements:
                        file.write(f'Expired announcements:\n- {"\n- ".join(a.title for a in removed_announcements)}\n')
            log(f'Report stored in {ref.report_gtfs}!')
            system_open(ref.report_gtfs)
        else:
            log('No changes, no report created.')

    @staticmethod
    def get_game_modes() -> list[str]:
        return ['Pokestops', 'Pokelines', 'Stellar Voyage', 'City Raiders']
