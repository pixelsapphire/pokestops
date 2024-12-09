import csv
import json
import os
import re
from abc import ABC
from typing import Any, Callable, Literal, Iterable, Self, TypeVar, Union
from util import geopoint

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
        return collection


class JsonSerializable(ABC):
    def __json_entry__(self, db: Union['Database', None] = None) -> str:
        pass

    @staticmethod
    def json_entry(obj: 'JsonSerializable', db: Union['Database', None] = None) -> str:
        return obj.__json_entry__(db)


class Discovery:
    def __init__(self, name: str, date: str):
        self.name: str = name
        self.date: str = date

    def __hash__(self):
        return hash(self.name) + hash(self.date)

    def __lt__(self, other: Self):
        return False if not isinstance(other, type(self)) else (
            self.date < other.date if self.date != other.date else self.name > other.name)


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

    def visited_by(self, player: Union[str, 'Player'], include_ev: bool = True) -> str | None:
        name = player.nickname if isinstance(player, Player) else player
        return next((visit.date for visit in self.visits
                     if name == visit.name and (visit.date != '2000-01-01' or include_ev)), None)

    def visited(self, include_ev: bool = True) -> bool:
        return any(visit.date != '2000-01-01' or include_ev for visit in self.visits)

    def add_visit(self, visit: Discovery):
        if self.visited_by(visit.name):
            print(f'{visit.name} already visited {self.short_name}, '
                  f'remove the entry from {visit.date if visit.date != '2000-01-01' else 'her EV file'}')
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
        return stops, stop_groups

    def __json_entry__(self, _=None) -> str:
        return (f'"{self.short_name}":{{'
                f'n:"{self.full_name}",'
                f'lt:{self.location.latitude},'
                f'ln:{self.location.longitude},'
                f'l:[{','.join(f'["{line}","{destination}"]' for line, destination in self.lines)}],'
                f'{f'v:[{','.join(f'["{visit.name}","{visit.date if visit.date != '2000-01-01' else ''}"]'
                                  for visit in sorted(self.visits))}],' if self.visits else ''}'
                f'}},')


class AchievementProgress:
    def __init__(self, name: str, visited: int, total: int, completed: str | None = None):
        self.name: str = name
        self.description: str = 'Collect all of the following: '
        self.visited: int = visited
        self.total: int = total
        self.completed: str | None = completed

    def percentage(self) -> int:
        return int(round(self.visited / self.total * 100))


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
        return next((visit.date for visit in self.discoveries if name == visit.name), None)

    def add_discovery(self, visit: Discovery):
        if self.discovered_by(visit.name):
            print(f'{visit.name} already discovered {self.vehicle_id}, remove the entry from {visit.date}')
        self.discoveries.add(visit)

    @staticmethod
    def read_dict(source: str, carriers: dict[str, Carrier], models: dict[str, VehicleModel]) -> dict[str, 'Vehicle']:
        constructor = lambda *row: Vehicle(row[0], row[1], carriers.get(row[2]), models.get(row[3]), row[4], row[5])
        return __read_collection__(source, {}, constructor, lambda c, v: c.update({v.vehicle_id: v}))

    def __json_entry__(self, _=None) -> str:
        return (f'"{self.vehicle_id}":{{'
                f'{f'p:"{self.license_plate}", ' if self.license_plate else ''}'
                f'{f'm:"{self.model.model_id}", ' if self.model else ''}'
                f'c:"{self.carrier.symbol}",'
                f'{f'i:{f'"{self.image_url}"'},' if self.image_url else ''}'
                f'l:"{self.lore}",'
                f'{f'd:[{','.join(f'["{visit.name}","{visit.date}"]'
                                  for visit in sorted(self.discoveries))}],' if self.discoveries else ''}'
                f'}},')


class Route(JsonSerializable):
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
    def read_dict(source: str) -> dict[str, 'Route']:
        constructor = lambda *row: Route(row[2], row[3].split('|')[0], row[4].split('|')[0].split('^')[0], row[6], row[7],
                                         list(map(lambda seq: seq.split('&'), row[8].split('|'))))
        return __read_collection__(source, {}, constructor, lambda c, v: c.update({v.number: v}))

    def __cmp_key__(self):
        return int(self.number) if self.number.isdigit() else int(re.sub(r'\D', '', self.number)) - 1000

    def __lt__(self, other):
        return self.__cmp_key__() < other.__cmp_key__() if isinstance(other, type(self)) else False

    def __json_entry__(self, _=None) -> str:
        return (f'"{self.number}":{{'
                f'b:"{self.background_color}",'
                f't:"{self.text_color}",'
                f'r:"{self.description}",'
                f'k:"{self.kind()}",'
                f'd:"{self.terminals}",'
                f'}},')


class Player(JsonSerializable):
    def __init__(self, nickname: str, primary_color: str, tint_color: str,
                 stops_file: str, ev_file: str, terminals_file: str, vehicles_file: str):
        self.nickname: str = nickname
        self.primary_color: str = primary_color
        self.tint_color: str = tint_color
        self.stops_file: str = stops_file
        self.ev_file: str = ev_file
        self.terminals_file: str = terminals_file
        self.vehicles_file: str = vehicles_file
        self.__achievements__: Achievements = Achievements()
        self.__vehicles__: list[tuple[Vehicle, str]] = []

    def add_stop(self, s: Stop) -> None:
        self.__achievements__.add_stop(s)

    def add_vehicle(self, v: Vehicle, date: str) -> None:
        self.__vehicles__.append((v, date))

    def get_achievements(self, stops: dict[str, Stop], stop_groups: dict[str, set[str]]) -> list[AchievementProgress]:
        prog = []
        for group in self.__achievements__.stop_groups:
            visited = len(self.__achievements__.stop_groups[group])
            total = len(stop_groups[group])
            if visited == total:
                date = max(s.visited_by(self) for s in self.__achievements__.stop_groups[group])
                prog.append(AchievementProgress(group, visited, total, date))
            else:
                prog.append(AchievementProgress(group, visited, total))
            prog[-1].description += ', '.join(
                sorted(s.short_name for s in stops.values() if s.full_name == group))
        return sorted(prog, key=lambda p: (p.percentage(), p.completed), reverse=True)

    def get_n_achievements(self, stops: dict[str, Stop], stop_groups: dict[str, set[str]]) -> int:
        return len(list(filter(lambda s: s.visited == s.total, self.get_achievements(stops, stop_groups))))

    def get_vehicles(self) -> Iterable[tuple[Vehicle, str]]:
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
        self.init_file(self.vehicles_file, 'vehicle_id,date_discovered\n')

    @staticmethod
    def read_list(source: str) -> list['Player']:
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], Player, list.append)

    def __json_entry__(self, db: 'Database' = None) -> str:
        stops: dict[str, Stop] = db.stops if db else {}
        return (f'"{self.nickname}":{{\n'
                f'v:[{','.join(sorted(f'"{v[0].vehicle_id}"' for v in self.get_vehicles()))}],\n'
                f's:[{','.join(sorted(f'"{s.short_name}"' for s in stops.values() if s.visited_by(self)))}],\n'
                f'}},')


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
        with (open(source, 'r') as file):
            index = json.load(file)
            regions = [Region(region['number'], region['short_name'], region['full_name'],
                              Region.__resolve_predicate__(region['predicate']))
                       for region in index['regions']]
            district: Region = next(filter(lambda r: r.short_name == index['district'], regions))
            return district, {
                district.short_name: district,
                **{region.short_name: region for region in regions if region != district},
            }


class Database:
    type CollectionName = Literal[
        'players', 'progress', 'stops', 'stop_groups', 'terminals', 'carriers', 'regions', 'vehicles', 'models']
    __stars__: dict[tuple[int, int], int] = {(1, 1): 1, (2, 2): 2, (3, 4): 3, (5, 7): 4, (8, 100): 5}

    def __init__(self, players: list[Player], progress: dict[str, dict[str, float]],
                 stops: dict[str, Stop], stop_groups: dict[str, set[str]], terminals: list[Terminal],
                 carriers: dict[str, Carrier], regions: dict[str, Region], district: Region,
                 vehicles: dict[str, Vehicle], models: dict[str, VehicleModel], routes: dict[str, Route]):
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
        self.routes: dict[str, Route] = routes

    @staticmethod
    def partial(players: list[Player] | None = None, progress: dict[str, dict[str, float]] | None = None,
                stops: dict[str, Stop] | None = None, stop_groups: dict[str, set[str]] | None = None,
                terminals: list[Terminal] | None = None, carriers: dict[str, Carrier] | None = None,
                regions: dict[str, Region] | None = None, district: Region | None = None,
                vehicles: dict[str, Vehicle] | None = None, models: dict[str, VehicleModel] | None = None,
                routes: dict[str, Route] | None = None) -> 'Database':
        return Database(players or [], progress or {}, stops or {}, stop_groups or {}, terminals or [],
                        carriers or {}, regions or {}, district or Region(0, '', '', lambda _: False),
                        vehicles or {}, models or {}, routes or {})

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
