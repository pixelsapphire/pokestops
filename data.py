import csv
import json
import os
import re
from abc import ABC
from typing import Any, Callable, Generic, Literal, Iterable, Self, TypeVar, Union

import ref
from util import geopoint, RichComparisonT, SupportsDunderGT

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
                    print(f'Error while processing row {row}: {e}')
        print('Done!')
        return collection


class JsonSerializable(ABC):
    def __json_entry__(self, db: Union['Database', None] = None) -> str:
        pass

    @staticmethod
    def json_entry(obj: 'JsonSerializable', db: Union['Database', None] = None) -> str:
        return obj.__json_entry__(db)


class Discovery(Generic[RichComparisonT]):
    def __init__(self, item: RichComparisonT, date: str = ''):
        self.item: RichComparisonT = item
        self.date: str = date

    def date_known(self) -> bool:
        return self.date != ''

    def __hash__(self):
        return hash(self.item) + hash(self.date)

    def __lt__(self, other: Self):
        if not isinstance(other, type(self)):
            return False
        if self.date != other.date:
            return (self.date if self.date else '0') < (other.date if other.date else '0')
        else:
            return self.item > other.item if isinstance(self.item, SupportsDunderGT) else not self.item < other.item


class Stop(JsonSerializable):

    def __init__(self, short_name: str, full_name: str, latitude: str, longitude: str, zone: str, routes: str):
        self.short_name: str = short_name
        self.full_name: str = full_name
        self.location: geopoint = geopoint(float(latitude), float(longitude))
        self.zone: str = zone
        self.visits: set[Discovery] = set()
        self.regions: list[Region] = []
        self.lines: list[tuple[str, str]] = list(map(lambda e: (e[:e.index(':')], e[e.index(':') + 1:]),
                                                     routes.split('&'))) if routes else []
        self.terminals_progress: list[tuple[Literal['arrival', 'departure'], Player, Terminal]] = []

    def __hash__(self):
        return hash(self.short_name)

    def __eq__(self, other: Self):
        return self.short_name == other.short_name if isinstance(other, type(self)) else False

    def in_any_of(self, towns: set[str]) -> bool:
        return '/' in self.full_name and self.full_name[:self.full_name.index('/')] in towns

    def is_visited(self, include_ev: bool = True) -> bool:
        return any(visit.date or include_ev for visit in self.visits)

    def is_visited_by(self, player: Union[str, 'Player'], include_ev: bool = True) -> bool:
        name: str = player.nickname if isinstance(player, Player) else player
        return any(name == visit.item.nickname and (visit.date_known() or include_ev) for visit in self.visits)

    def date_visited_by(self, player: Union[str, 'Player'], include_ev: bool = True) -> str:
        name: str = player.nickname if isinstance(player, Player) else player
        return next((visit.date for visit in self.visits if name == visit.item.nickname and (visit.date_known() or include_ev)))

    def add_visit(self, visit: Discovery['Player']):
        if self.is_visited_by(visit.item):
            print(f'{visit.item.nickname} already visited {self.short_name}, '
                  f'remove the entry from {visit.date if visit.date else 'her EV file'}')
        self.visits.add(visit)

    def mark_closest_arrival(self, player: 'Player', terminal: 'Terminal'):
        self.terminals_progress.append(('arrival', player, terminal))

    def mark_closest_departure(self, player: 'Player', terminal: 'Terminal'):
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
    def read_stops(source: str, db: 'Database') -> tuple[dict[str, 'Stop'], dict[str, set[str]]]:
        print(f'  Reading stops data from {source}... ', end='')
        stops: dict[str, Stop] = {}
        stop_groups: dict[str, set[str]] = {}
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
                    stop_groups[stop.full_name] = set()
                stop_groups[stop.full_name].add(stop.short_name)
        print('Done!')
        return stops, stop_groups

    def __json_entry__(self, _=None) -> str:
        return (f'"{self.short_name}":{{'
                f'n:"{self.full_name}",'
                f'lt:{self.location.latitude},'
                f'ln:{self.location.longitude},'
                f'l:[{','.join(f'["{line}","{destination}"]' for line, destination in self.lines)}],'
                f'{f'v:[{','.join(f'["{visit.item.nickname}","{visit.date}"]'
                                  for visit in sorted(self.visits))}],' if self.visits else ''}'
                f'}},')


class AchievementProgress:
    def __init__(self, name: str, visited: int, total: int, completed: str | None = None):
        self.name: str = name
        self.description: str = 'Collect all of the following: '
        self.visited: int = visited
        self.total: int = total
        self.completion_date: str | None = completed

    def percentage(self) -> int:
        return int(round(self.visited / self.total * 100))

    def is_completed(self) -> bool:
        return self.visited == self.total

    def completion_date_known(self) -> bool:
        return self.completion_date is not None and self.completion_date != ''


class Achievements:
    def __init__(self):
        self.stop_groups: dict[str, set[Stop]] = {}

    def add_stop(self, s: Stop) -> None:
        if s.full_name not in self.stop_groups:
            self.stop_groups[s.full_name] = set()
        self.stop_groups[s.full_name].add(s)


class TerminalProgress:
    def __init__(self, terminal: 'Terminal', player: 'Player', closest_arrival: Stop, closest_departure: Stop):
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

    def reached_by(self, player: 'Player') -> bool:
        return any(p.reached() for p in self.progress if p.player == player)

    def anybody_reached(self) -> bool:
        return any(p.reached() for p in self.progress)

    def completed_by(self, player: 'Player') -> bool:
        progress: TerminalProgress = next((p for p in self.progress if p.player == player), None)
        return progress and progress.completed()

    def add_player_progress(self, player: 'Player', closest_arrival: Stop, closest_departure: Stop) -> None:
        progress: TerminalProgress = TerminalProgress(self, player, closest_arrival, closest_departure)
        self.progress.append(progress)
        if not progress.arrived():
            closest_arrival.mark_closest_arrival(player, self)
        if not progress.departed():
            closest_departure.mark_closest_departure(player, self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id if isinstance(other, type(self)) else False

    @staticmethod
    def read_list(source: str, stops: dict[str, Stop]) -> list['Terminal']:
        print(f'  Reading terminals data from {source}... ', end='')
        constructor = lambda *row: Terminal(row[0], row[1], row[2], row[3], stops.get(row[4]), stops.get(row[5]))
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], constructor, list.append)

    def __json_entry__(self, _=None) -> str:
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
    def read_dict(source: str) -> dict[str, 'Carrier']:
        print(f'  Reading carriers data from {source}... ', end='')
        return __read_collection__(source, {}, Carrier, lambda c, v: c.update({v.symbol: v}))

    def __json_entry__(self, _=None) -> str:
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

    def __json_entry__(self, _=None) -> str:
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
        self.discoveries: set[Discovery] = set()

    def __hash__(self):
        return hash(self.vehicle_id)

    def __eq__(self, other):
        return self.vehicle_id == other.vehicle_id if isinstance(other, type(self)) else False

    def __cmp_key__(self):
        return int(self.vehicle_id) if self.vehicle_id.isdigit() else int(self.vehicle_id[:self.vehicle_id.index('+')])

    def __lt__(self, other):
        return self.__cmp_key__() < other.__cmp_key__() if isinstance(other, type(self)) else False

    def discovered_by(self, player: Union[str, 'Player']) -> str | None:
        name = player.nickname if isinstance(player, Player) else player
        return next((visit.date for visit in self.discoveries if name == visit.item), None)

    def add_discovery(self, visit: Discovery):
        if self.discovered_by(visit.item):
            print(f'{visit.item} already discovered {self.vehicle_id}, remove the entry from {visit.date}')
        self.discoveries.add(visit)

    @staticmethod
    def read_dict(source: str, carriers: dict[str, Carrier], models: dict[str, VehicleModel]) -> dict[str, 'Vehicle']:
        print(f'  Reading vehicles data from {source}... ', end='')
        constructor = lambda *row: Vehicle(row[0], row[1], carriers.get(row[2]), models.get(row[3]), row[4], row[5])
        return __read_collection__(source, {}, constructor, lambda c, v: c.update({v.vehicle_id: v}))

    def __json_entry__(self, _=None) -> str:
        return (f'"{self.vehicle_id}":{{'
                f'{f'p:"{self.license_plate}", ' if self.license_plate else ''}'
                f'{f'm:"{self.model.model_id}", ' if self.model else ''}'
                f'c:"{self.carrier.symbol}",'
                f'{f'i:{f'"{self.image_url}"'},' if self.image_url else ''}'
                f'l:"{self.lore}",'
                f'{f'd:[{','.join(f'["{visit.item.nickname}","{visit.date}"]'
                                  for visit in sorted(self.discoveries))}],' if self.discoveries else ''}'
                f'}},')


class Line(JsonSerializable):
    def __init__(self, number: str, terminals: str, description: str,
                 background_color: str, text_color: str, stops: list[list[str]]):
        self.number: str = number
        self.terminals: str = terminals
        self.description: str = description
        self.background_color: str = background_color
        self.text_color: str = text_color
        self.stops: list[list[str]] = stops

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
    def read_dict(source: str) -> dict[str, 'Line']:
        print(f'  Reading routes data from {source}... ', end='')
        constructor = lambda *row: Line(row[2], row[3].split('|')[0], row[4].split('|')[0].split('^')[0], row[6], row[7],
                                        list(map(lambda seq: seq.split('&'), row[8].split('|'))))
        return __read_collection__(source, {}, constructor, lambda c, v: c.update({v.number: v}))

    def __cmp_key__(self):
        return int(self.number) if self.number.isdigit() else int(re.sub(r'\D', '', self.number)) - 1000

    def __lt__(self, other):
        return self.__cmp_key__() < other.__cmp_key__() if isinstance(other, type(self)) else False

    def __json_entry__(self, _=None) -> str:
        return (f'"{self.number}":{{'
                f'bc:"{self.background_color}",'
                f'tc:"{self.text_color}",'
                f'k:"{self.kind()}",'
                f't:"{self.terminals}",'
                f'rd:"{self.description}",'
                f'r:[{','.join(f'[{",".join(f"\"{stop}\"" for stop in seq)}]' for seq in self.stops)}]'
                f'}},')


class Player(JsonSerializable):
    def __init__(self, nickname: str, primary_color: str, tint_color: str):
        nickname_lowercase: str = nickname.lower()
        self.nickname: str = nickname
        self.primary_color: str = primary_color
        self.tint_color: str = tint_color
        self.stops_file: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_stops}'
        self.ev_file: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_ev_stops}'
        self.terminals_file: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_terminals}'
        self.lines_file: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_lines}'
        self.vehicles_file: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_vehicles}'
        self.__achievements__: Achievements = Achievements()
        self.__lines__: list[Discovery[Line]] = []
        self.__vehicles__: list[Discovery[Vehicle]] = []

    def add_stop(self, stop: Stop) -> None:
        self.__achievements__.add_stop(stop)

    def add_line(self, line: Line, date: str) -> None:
        self.__lines__.append(Discovery(line, date))

    def add_vehicle(self, vehicle: Vehicle, date: str) -> None:
        self.__vehicles__.append(Discovery(vehicle, date))

    def get_achievements(self, stops: dict[str, Stop], stop_groups: dict[str, set[str]]) -> list[AchievementProgress]:
        prog = []
        for group in self.__achievements__.stop_groups:
            visited = len(self.__achievements__.stop_groups[group])
            total = len(stop_groups[group])
            if visited == total:
                date = max(s.date_visited_by(self) for s in self.__achievements__.stop_groups[group])
                prog.append(AchievementProgress(group, visited, total, date))
            else:
                prog.append(AchievementProgress(group, visited, total))
            prog[-1].description += ', '.join(
                sorted(s.short_name for s in stops.values() if s.full_name == group))
        return sorted(prog, key=lambda p: (p.percentage(), p.completion_date), reverse=True)

    def get_n_achievements(self, stops: dict[str, Stop], stop_groups: dict[str, set[str]]) -> int:
        return len(list(filter(lambda ap: ap.visited == ap.total, self.get_achievements(stops, stop_groups))))

    def get_lines(self) -> Iterable[Discovery[Line]]:
        return reversed(self.__lines__)

    def get_vehicles(self) -> Iterable[Discovery[Vehicle]]:
        return reversed(self.__vehicles__)

    def get_n_vehicles(self) -> int:
        return len(self.__vehicles__)

    @staticmethod
    def init_file(path: str, initial_content: str = '') -> None:
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'x') as new_file:
                new_file.write(initial_content)

    def init_files(self) -> None:
        self.init_file(self.stops_file, 'stop_id,date_visited\n')
        self.init_file(self.ev_file)
        self.init_file(self.terminals_file, 'terminal_id,closest_arrival,closest_departure\n')
        self.init_file(self.lines_file, 'line_number,date_discovered\n')
        self.init_file(self.vehicles_file, 'vehicle_id,date_discovered\n')

    @staticmethod
    def read_list(source: str) -> list['Player']:
        print(f'  Reading players data from {source}... ', end='')
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], Player, list.append)

    def __json_entry__(self, db: 'Database' = None) -> str:
        stops: dict[str, Stop] = db.stops if db else {}
        return (f'"{self.nickname}":{{\n'
                f'v:[{','.join(sorted(f'"{v.item.vehicle_id}"' for v in self.get_vehicles()))}],\n'
                f's:[{','.join(sorted(f'"{s.short_name}"' for s in stops.values() if s.is_visited_by(self)))}],\n'
                f'}},')

    def __lt__(self, other):
        return self.nickname < other.nickname if isinstance(other, type(self)) else False


class Region:
    def __init__(self, number: int, short_name: str, full_name: str, predicate: Callable[[Stop], bool]):
        self.number: int = number
        self.short_name: str = short_name
        self.full_name: str = full_name
        self.predicate: Callable[[Stop], bool] = predicate
        self.stops: set[Stop] = set()

    def add_stop(self, s: Stop) -> None:
        self.stops.add(s)
        s.regions.append(self)

    def __contains__(self, stop: Stop) -> bool:
        return self.predicate(stop)

    def __lt__(self, other) -> bool:
        return self.number < other.number if isinstance(other, type(self)) else False

    def __hash__(self):
        return hash(self.short_name)

    def __eq__(self, other):
        return self.short_name == other.short_name if isinstance(other, type(self)) else False

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
    def read_regions(source: str) -> tuple['Region', dict[str, 'Region']]:
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
        'players', 'progress', 'stops', 'stop_groups', 'terminals', 'carriers', 'regions', 'vehicles', 'models', 'lines']
    __stars__: dict[tuple[int, int], int] = {(1, 1): 1, (2, 2): 2, (3, 4): 3, (5, 7): 4, (8, 100): 5}

    def __init__(self, players: list[Player], progress: dict[str, dict[str, float]],
                 stops: dict[str, Stop], stop_groups: dict[str, set[str]], terminals: list[Terminal],
                 carriers: dict[str, Carrier], regions: dict[str, Region], district: Region,
                 vehicles: dict[str, Vehicle], models: dict[str, VehicleModel], lines: dict[str, Line]):
        self.players: list[Player] = players
        self.progress: dict[str, dict[str, float]] = progress
        self.stops: dict[str, Stop] = stops
        self.stop_groups: dict[str, set[str]] = stop_groups
        self.terminals: list[Terminal] = terminals
        self.carriers: dict[str, Carrier] = carriers
        self.regions: dict[str, Region] = regions
        self.district: Region = district
        self.vehicles: dict[str, Vehicle] = vehicles
        self.models: dict[str, VehicleModel] = models
        self.lines: dict[str, Line] = lines

    @staticmethod
    def partial(players: list[Player] | None = None, progress: dict[str, dict[str, float]] | None = None,
                stops: dict[str, Stop] | None = None, stop_groups: dict[str, set[str]] | None = None,
                terminals: list[Terminal] | None = None, carriers: dict[str, Carrier] | None = None,
                regions: dict[str, Region] | None = None, district: Region | None = None,
                vehicles: dict[str, Vehicle] | None = None, models: dict[str, VehicleModel] | None = None,
                routes: dict[str, Line] | None = None) -> 'Database':
        return Database(players or [], progress or {}, stops or {}, stop_groups or {}, terminals or [],
                        carriers or {}, regions or {}, district or Region(0, '', '', lambda _: False),
                        vehicles or {}, models or {}, routes or {})

    def has_collection(self, name: CollectionName) -> bool:
        return bool(getattr(self, name))

    def add_collection(self, name: CollectionName, collection: Any):
        setattr(self, name, collection)

    @staticmethod
    def get_stars_for_group(size: int):
        return next((stars for ((min_size, max_size), stars) in Database.__stars__.items() if min_size <= size <= max_size), 0)

    def regions_without_district(self) -> list[Region]:
        return [region for region in self.regions.values() if region != self.district]

    def region_of(self, stop: Stop) -> Region:
        return next((region for region in stop.regions if stop and region != self.district), self.district)

    def group_location(self, stop: Stop) -> geopoint:
        stops = list(map(lambda stop_id: self.stops[stop_id], self.stop_groups[stop.full_name]))
        return geopoint(sum(s.location.latitude for s in stops) / len(stops),
                        sum(s.location.longitude for s in stops) / len(stops))
