import os
from typing import Callable, Iterable, Self


class Visit:
    def __init__(self, name: str, date: str):
        self.name: str = name
        self.date: str = date

    def __hash__(self):
        return hash(self.name) + hash(self.date)

    def __lt__(self, other: Self):
        return (self.date < other.date if self.date != other.date else self.name > other.name) if isinstance(
            other, type(self)) else False


class Stop:
    def __init__(self, short_name: str, full_name: str, latitude: str, longitude: str, zone: str, routes: str):
        self.short_name: str = short_name
        self.full_name: str = full_name
        self.latitude: float = float(latitude)
        self.longitude: float = float(longitude)
        self.zone: str = zone
        self.visits: set[Visit] = set()
        self.regions: list[Region] = []
        self.lines: list[tuple[int, str]] = list(map(lambda e: (int(e[:e.index(':')]), e[e.index(':') + 1:]),
                                                     routes.split('&')))

    def __hash__(self):
        return hash(self.short_name)

    def __eq__(self, other: Self):
        return self.short_name == other.short_name if isinstance(other, type(self)) else False

    def in_one_of(self, towns: set[str]) -> bool:
        return '/' in self.full_name and self.full_name[:self.full_name.index('/')] in towns

    def visited_by(self, name: str, include_ev: bool = True) -> str | None:
        return next((visit.date for visit in self.visits
                     if name == visit.name and (visit.date != '2000-01-01' or include_ev)), None)

    def add_visit(self, visit: Visit):
        if self.visited_by(visit.name):
            print(f'{visit.name} already visited {self.short_name}, '
                  f'remove the entry from {visit.date if visit.date != '2000-01-01' else 'her EV file'}')
        self.visits.add(visit)

    def marker(self) -> tuple[str, str, float, str | None]:
        number = int(self.short_name[-2:])
        if 0 < number < 20:
            return 'circle', '●', 1.1, None
        elif 20 < number < 40:
            return 'star', '★', 1, None
        elif 40 < number < 70:
            return 'diamond', '■', 0.9, 'transform: rotate(45deg);'
        elif 70 < number < 90:
            return 'square', '■', 0.9, None
        else:
            return 'triangle', '▲', 0.8, None


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


class Carrier:
    def __init__(self, symbol: str, short_name: str, full_name: str):
        self.symbol: str = symbol
        self.short_name: str = short_name
        self.full_name: str = full_name

    def __hash__(self):
        return hash(self.symbol)

    def __eq__(self, other):
        return self.symbol == other.symbol if isinstance(other, type(self)) else False


class VehicleModel:
    def __init__(self, model_id: str, kind: str, kind_detailed: str, brand: str, model: str, seats: str, lore: str):
        self.model_id: str = model_id
        self.kind: str = kind
        self.kind_detailed: str = kind_detailed
        self.brand: str = brand
        self.model: str = model
        self.seats: int | None = int(seats) if seats.isdigit() else None
        self.lore: str = lore

    def __hash__(self):
        return hash(self.model_id)

    def __eq__(self, other):
        return self.model_id == other.model_id if isinstance(other, type(self)) else False


class Vehicle:
    def __init__(self, vehicle_id: str, carrier: Carrier, model: VehicleModel, image_url: str, lore: str):
        self.vehicle_id: str = vehicle_id
        self.carrier: Carrier = carrier
        self.model: VehicleModel = model
        self.image_url: str | None = image_url if image_url else None
        self.lore: str = lore

    def __hash__(self):
        return hash(self.vehicle_id)

    def __eq__(self, other):
        return self.vehicle_id == other.vehicle_id if isinstance(other, type(self)) else False

    def __cmp_key__(self):
        return int(self.vehicle_id) if self.vehicle_id.isdigit() else int(self.vehicle_id[:self.vehicle_id.index('+')])

    def __lt__(self, other):
        return self.__cmp_key__() < other.__cmp_key__() if isinstance(other, type(self)) else False


class Player:
    def __init__(self, nickname: str, primary_color: str, tint_color: str, stops_file: str, ev_file: str, vehicles_file: str):
        self.nickname: str = nickname
        self.primary_color: str = primary_color
        self.tint_color: str = tint_color
        self.stops_file: str = stops_file
        self.ev_file: str = ev_file
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
                date = max(s.visited_by(self.nickname) for s in self.__achievements__.stop_groups[group])
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
            with open(path, 'x') as new_file:
                new_file.write(initial_content)

    def init_files(self) -> None:
        self.init_file(self.stops_file, 'stop_id,date_visited\n')
        self.init_file(self.ev_file)
        self.init_file(self.vehicles_file, 'vehicle_id,date_discovered\n')


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

    def __contains__(self, item):
        return self.predicate(item)

    def __lt__(self, other):
        return self.number < other.number
