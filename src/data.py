from __future__ import annotations
import json
import ref
import re
from abc import ABC
from collections import defaultdict
from typing import Literal, TYPE_CHECKING
from util import *

if TYPE_CHECKING:
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
        print('Done!')
        return collection


class JsonSerializable(ABC):
    def __json_entry__(self) -> str: ...

    @staticmethod
    def json_entry(obj: JsonSerializable) -> str:
        return obj.__json_entry__()


class Discovery[RichComparisonT]:
    def __init__(self, item: RichComparisonT, date: DateAndOrder = DateAndOrder.long_time_ago):
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

    def add_visit(self, player: Player, date: DateAndOrder = DateAndOrder.long_time_ago):
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
    def read_stops(source: str, db: Database) -> tuple[dict[str, Stop], dict[str, SortedSet[Stop]]]:
        print(f'  Reading stops data from {source}... ', end='')
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
        print('Done!')
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
        print(f'  Reading terminals data from {source}... ', end='')
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
        print(f'  Reading carriers data from {source}... ', end='')
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
        print(f'  Reading vehicle models data from {source}... ', end='')
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

    def __cmp_key__(self):
        return int(self.vehicle_id) if self.vehicle_id.isdigit() else int(self.vehicle_id[:self.vehicle_id.index('+')])

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
        print(f'  Reading vehicles data from {source}... ', end='')
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
        print(f'  Reading routes data from {source}... ', end='')
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
                 background_color: str, text_color: str, routes: list[str], stops: list[list[str]]):
        self.number: str = number
        self.terminals: str = terminals
        self.description: str = description
        self.background_color: str = background_color
        self.text_color: str = text_color
        self.routes: list[str] = routes
        self.stops: list[list[str]] = stops
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

    def __cmp_key__(self):
        return int(self.number) if self.number.isdigit() else int(re.sub(r'\D', '', self.number)) - 1000

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
    def read_dict(source: str) -> dict[str, Line]:  # TODO attach actual routes and stops instead of ids
        print(f'  Reading routes data from {source}... ', end='')
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
                f'r:[{','.join(f'[{",".join(f"\"{stop}\"" for stop in seq)}]' for seq in self.stops)}],'
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
        print(f'  Reading regions data from {source}... ', end='')
        with (open(source, 'r') as file):
            index = json.load(file)
            regions = [Region(region['number'], region['short_name'], region['full_name'],
                              Region.__resolve_predicate__(region['predicate']))
                       for region in index['regions']]
            district: Region = next(filter(lambda r: r.short_name == index['district'], regions))
            print('Done!')
            return district, {
                district.short_name: district,
                **{region.short_name: region for region in regions if region != district},
            }


class Database:
    type CollectionName = Literal[
        'players', 'progress', 'stops', 'stop_groups', 'terminals',
        'carriers', 'regions', 'vehicles', 'models', 'lines', 'routes']
    __stars__: dict[tuple[int, int], int] = {(1, 1): 1, (2, 2): 2, (3, 4): 3, (5, 7): 4, (8, 100): 5}

    def __init__(self, players: list[Player], progress: dict[str, dict[str, float]],
                 stops: dict[str, Stop], stop_groups: dict[str, SortedSet[Stop]], terminals: list[Terminal],
                 carriers: dict[str, Carrier], regions: dict[str, Region], district: Region,
                 vehicles: dict[str, Vehicle], models: dict[str, VehicleModel],
                 lines: dict[str, Line], routes: dict[str, Route]):
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

    def __contains__(self, name: CollectionName) -> bool:
        return bool(getattr(self, name))

    @staticmethod
    def partial(players: list[Player] | None = None, progress: dict[str, dict[str, float]] | None = None,
                stops: dict[str, Stop] | None = None, stop_groups: dict[str, SortedSet[Stop]] | None = None,
                terminals: list[Terminal] | None = None, carriers: dict[str, Carrier] | None = None,
                regions: dict[str, Region] | None = None, district: Region | None = None,
                vehicles: dict[str, Vehicle] | None = None, models: dict[str, VehicleModel] | None = None,
                lines: dict[str, Line] | None = None, routes: dict[str, Route] | None = None) -> Database:
        return Database(players or [], progress or {}, stops or {}, stop_groups or {}, terminals or [],
                        carriers or {}, regions or {}, district or Region(0, '', '', lambda _: False),
                        vehicles or {}, models or {}, lines or {}, routes or {})

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

    @staticmethod
    def make_update_report(old_data: Database, new_data: Database) -> None:
        added_stops: set[Stop] = {s for s in new_data.stops.values() if s not in old_data.stops.values()}
        removed_stops: set[Stop] = {s for s in old_data.stops.values() if s not in new_data.stops.values()}
        added_lines: set[str] = {r for r in new_data.lines.keys() if r not in old_data.lines.keys()}
        removed_lines: set[str] = {r for r in old_data.lines.keys() if r not in new_data.lines.keys()}
        changed_lines: set[str] = {r for r in new_data.lines.keys()
                                   if r in old_data.lines.keys() and new_data.lines[r].stops != old_data.lines[r].stops}
        if not added_stops and not removed_stops and not added_lines and not removed_lines and not changed_lines:
            print(' No changes, no report created.')
        else:
            print(' Data has changed, creating report... ', end='')
            lines: int = max(len(added_lines), len(removed_lines), len(changed_lines))
            lexmap: dict[str, float] = create_lexicographic_mapping(file_to_string(ref.lexmap_polish))
            line_key = lambda line: int(line) if line.isdigit() else int(re.sub(r'\D', '', line)) - lines
            stop_key = lambda stop: lexicographic_sequence(f'{stop.full_name}{stop.short_name}', lexmap)
            with open(prepare_path(ref.report_gtfs), 'w') as file:
                file.write('GTFS database updated.\n')
                if added_stops:
                    file.write(f'Added stops:\n- {'\n- '.join(f'{s.full_name} [{s.short_name}]'
                                                              for s in sorted(added_stops, key=stop_key))}\n')
                if removed_stops:
                    file.write(f'Removed stops:\n- {'\n- '.join(f'{s.full_name} [{s.short_name}]'
                                                                for s in sorted(removed_stops, key=stop_key))}\n')
                if added_lines:
                    file.write(f'Added lines:\n- {"\n- ".join(sorted(added_lines, key=line_key))}\n')
                if removed_lines:
                    file.write(f'Removed lines:\n- {"\n- ".join(sorted(removed_lines, key=line_key))}\n')
                if changed_lines:
                    file.write(f'Changed lines:\n- {"\n- ".join(sorted(changed_lines, key=line_key))}\n')
            print(f'Report stored in {ref.report_gtfs}!')
            system_open(ref.report_gtfs)
