from __future__ import annotations
import util
from data import __read_collection__
from data import *
from typing import Iterable


class AchievementProgress:
    def __init__(self, name: str, stops_list: list[str], visited: int, total: int,
                 completed: DateAndOrder = DateAndOrder.never):
        self.name: str = name
        self.stops_list: list[str] = stops_list
        self.visited: int = visited
        self.total: int = total
        self.completion_date: DateAndOrder = completed

    def percentage(self) -> int:
        return int(round(self.visited / self.total * 100))

    def is_completed(self) -> bool:
        return self.visited == self.total


class Logbook:
    __lexmap__: dict[str, float] = util.create_lexicographic_mapping(util.file_to_string(ref.lexmap_polish))

    def __init__(self, player: Player):
        self.player: Player = player
        self.stops: list[Discovery[Stop]] = []
        self.lines: list[Discovery[Line]] = []
        self.vehicles: list[Discovery[Vehicle]] = []

    def add_stop(self, stop: Stop, date: DateAndOrder = DateAndOrder.distant_past) -> None:
        self.stops.append(Discovery(stop, date))

    def add_line(self, line: Line, date: DateAndOrder) -> None:
        self.lines.append(Discovery(line, date))

    def add_vehicle(self, vehicle: Vehicle, date: DateAndOrder) -> None:
        self.vehicles.append(Discovery(vehicle, date))

    @staticmethod
    def __cmp_achievements__(a: AchievementProgress, b: AchievementProgress) -> RichComparisonT:
        if a.percentage() != b.percentage():
            return 1 if a.percentage() < b.percentage() else -1
        if a.completion_date != b.completion_date:
            return 1 if a.completion_date < b.completion_date else -1
        if a.name != b.name:
            return util.lexicographic_compare(a.name, b.name, Logbook.__lexmap__)
        return 0

    def get_achievements(self, db: Database) -> list[AchievementProgress]:
        prog: list[AchievementProgress] = []
        for name, stops in db.stop_groups.items():
            visited: int = count(s for s in stops if s.is_visited_by(self.player))
            if visited == 0:
                continue
            total: int = len(stops)
            stops_list: list[str] = list(s.short_name for s in stops)
            if visited == total:
                date: DateAndOrder = max(s.date_visited_by(self.player) for s in stops if s.is_visited_by(self.player))
                prog.append(AchievementProgress(name, stops_list, visited, total, date))
            elif visited > 0:
                prog.append(AchievementProgress(name, stops_list, visited, total))
        return Comparator(Logbook.__cmp_achievements__).sorted(prog)

    def get_n_achievements(self, db: Database) -> int:
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return len(list(filter(AchievementProgress.is_completed, self.get_achievements(db))))

    def get_stops(self) -> Iterable[Discovery[Stop]]:
        return sorted(self.stops, reverse=True)

    def get_lines(self) -> Iterable[Discovery[Line]]:
        return sorted(self.lines, reverse=True)

    def get_vehicles(self) -> Iterable[Discovery[Vehicle]]:
        return sorted(self.vehicles, reverse=True)

    def get_n_vehicles(self) -> int:
        return len(self.vehicles)


class ChronoLoader:
    def __init__(self, error_generator: Callable[[list[str]], str]):
        self.current_day: DateAndOrder = DateAndOrder.distant_past
        self.current_day_count: int = 0
        self.error_generator: Callable[[list[str]], str] = error_generator

    def next(self, row: list[str]) -> DateAndOrder:
        if DateAndOrder(date_string=row[1]) > self.current_day:
            self.current_day = DateAndOrder(date_string=row[1])
            self.current_day_count = 1
        elif DateAndOrder(date_string=row[1]) == self.current_day:
            self.current_day_count += 1
        else:
            error(self.error_generator(row))
        return DateAndOrder(date_string=row[1], number_in_day=self.current_day_count)


class Player(JsonSerializable):
    def __init__(self, nickname: str, primary_color: str, tint_color: str):
        nickname_lowercase = nickname.lower()
        self.nickname: str = nickname
        self.primary_color: str = primary_color
        self.tint_color: str = tint_color
        self.logbook: Logbook = Logbook(self)
        self.__stops_file__: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_stops}'
        self.__ev_file__: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_ev_stops}'
        self.__terminals_file__: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_terminals}'
        self.__lines_file__: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_lines}'
        self.__vehicles_file__: str = f'{ref.playerdata_path}/{nickname_lowercase}/{ref.playerdata_file_vehicles}'

    def __eq__(self, other):
        return self.nickname == other.nickname if isinstance(other, type(self)) else False

    def __hash__(self):
        return hash(self.nickname)

    def __lt__(self, other):
        return self.nickname < other.nickname if isinstance(other, type(self)) else False

    def __repr__(self):
        return f'Player {self.nickname}'

    def __init_files__(self) -> None:
        prepare_file(self.__stops_file__, 'stop_id,date_visited\n')
        prepare_file(self.__ev_file__, 'stop_id\n')
        prepare_file(self.__terminals_file__, 'terminal_id,closest_arrival,closest_departure\n')
        prepare_file(self.__lines_file__, 'line_number,date_discovered\n')
        prepare_file(self.__vehicles_file__, 'vehicle_id,date_discovered\n')

    def __load_stops__(self, db: Database) -> None:
        loader: ChronoLoader = ChronoLoader(lambda r: f'{self.nickname}\'s stop visits are not in chronological order, '
                                                      f'change position of the ({r[0]},{r[1]}) entry in her stops file')
        stop_rows, stop_comments = get_csv_rows(self.__stops_file__)
        for row in stop_rows:
            stop: Stop | None = db.stops.get(row[0])
            date: DateAndOrder = loader.next(row)
            if stop:
                stop.add_visit(self, date)
                self.logbook.add_stop(stop, date)
            else:
                change: StopChange | None = find_first(lambda c: row[0] == c.old_stop.short_name, db.get_effective_changes())
                if change:
                    error(f'{self.nickname} has visited stop {row[0]}, which is now {change.new_stop.short_name}, '
                          f'change the {row[1]} entry in her stops file')
                else:
                    error(f'{self.nickname} has visited stop {row[0]}, which is currently not in the database, '
                          f'comment or remove the {row[1]} entry from her stops file')
        for row in stop_comments:
            if db.stops.get(row[0]):
                error(f'{self.nickname} has visited stop {row[0]}, which is now in the database, '
                      f'restore the {row[1]} entry in her stops file')

    def __load_ev_stops__(self, db: Database) -> None:
        ev_stop_rows, ev_stop_comments = get_csv_rows(self.__ev_file__)
        for row in ev_stop_rows:
            stop = db.stops.get(row[0])
            if stop:
                stop.add_visit(self)
                self.logbook.add_stop(stop)
            else:
                change = find_first(lambda c: row[0] == c.old_stop.short_name, db.get_effective_changes())
                if change:
                    error(f'{self.nickname} has visited stop {row[0]}, which is now {change.new_stop.short_name}, '
                          f'change the entry in her EV stops file')
                else:
                    error(f'{self.nickname} has visited stop {row[0]}, which is currently not in the database, '
                          f'comment or remove the entry from her EV stops file')
        for row in ev_stop_comments:
            if db.stops.get(row[0]):
                error(f'{self.nickname} has visited stop {row[0]}, which is now in the database, '
                      f'restore the entry in her EV stops file')

    def __load_terminals__(self, db: Database) -> None:
        terminal_rows, terminal_comments = get_csv_rows(self.__terminals_file__)
        for row in terminal_rows:
            terminal: Terminal | None = next((t for t in db.terminals if t.id == row[0]), None)
            closest_arrival: Stop | None = db.stops.get(row[1])
            closest_departure: Stop | None = db.stops.get(row[2])
            if not terminal:
                error(f'{self.nickname} has visited terminal {row[0]}, which is currently not in the database, '
                      f'comment or remove the entry from her terminals file')
            elif not closest_arrival or not closest_departure:
                error(f'{self.nickname}\'s progress for terminal {row[0]} mentions stop '
                      f'{row[1] if not closest_arrival else row[2]}, which is currently not in the database, '
                      f'fix the entry in her terminals file')
            else:
                terminal.add_player_progress(self, closest_arrival, closest_departure)
        for row in terminal_comments:
            if next((t for t in db.terminals if t.id == row[0]), None):
                error(f'{self.nickname} has visited terminal {row[0]}, which is now in the database, '
                      f'restore the entry in her terminals file')

    def __load_lines__(self, db: Database) -> None:
        loader: ChronoLoader = ChronoLoader(lambda r: f'{self.nickname}\'s line discoveries are not in chronological order, '
                                                      f'change position of the ({r[0]},{r[1]}) entry in her lines file')
        line_rows, line_comments = get_csv_rows(self.__lines_file__)
        for row in line_rows:
            line = db.lines.get(row[0])
            date: DateAndOrder = loader.next(row)
            if line:
                line.add_discovery(self, date)
                self.logbook.add_line(line, date)
            else:
                error(f'{self.nickname} has discovered line {row[0]}, which is currently not in the database, '
                      f'comment or remove the {row[1]} entry from her lines file')
        for row in line_comments:
            if db.lines.get(row[0]):
                error(f'{self.nickname} has discovered line {row[0]}, which is now in the database, '
                      f'restore the {row[1]} entry in her lines file')

    def __load_vehicles__(self, db: Database) -> None:
        loader: ChronoLoader = ChronoLoader(lambda r: f'{self.nickname}\'s vehicle discoveries are not in chronological order, '
                                                      f'change position of the ({r[0]},{r[1]}) entry in her vehicles file')
        vehicle_rows, vehicle_comments = get_csv_rows(self.__vehicles_file__)
        for row in vehicle_rows:
            vehicle = db.vehicles.get(row[0])
            date: DateAndOrder = loader.next(row)
            if vehicle:
                vehicle.add_discovery(self, date)
                self.logbook.add_vehicle(vehicle, date)
            else:
                combined: str | None = next((v for v in db.vehicles.keys() if
                                             v.startswith(f'{row[0]}+') or v.endswith(f'+{row[0]}') or
                                             v == f'{"+".join(row[0].split("+")[::-1])}'), None)
                if combined:
                    error(f'{self.nickname} has discovered vehicle #{row[0]}, which is part of a combined vehicle #{combined}, '
                          f'change the {row[1]} entry in her vehicles file')
                else:
                    error(f'{self.nickname} has discovered vehicle #{row[0]}, which is currently not in the database, '
                          f'comment or remove the {row[1]} entry from her vehicles file')
        for row in vehicle_comments:
            if db.vehicles.get(row[0]):
                error(f'{self.nickname} has discovered vehicle #{row[0]}, which is now in the database, '
                      f'restore the {row[1]} entry in her vehicles file')

    def load_data(self, db: Database) -> None:
        self.__init_files__()
        self.__load_stops__(db)
        self.__load_ev_stops__(db)
        self.__load_terminals__(db)
        self.__load_lines__(db)
        self.__load_vehicles__(db)

    @staticmethod
    def read_list(source: str) -> list[Player]:
        log(f'  Reading players index from {source}... ', end='')
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], Player, list.append)

    def __json_entry__(self) -> str:
        return (f'"{self.nickname}":{{\n'
                f's:[{','.join(sorted(f'"{d.item.short_name}"' for d in self.logbook.get_stops()))}],\n'
                f'l:[{','.join(sorted(f'"{d.item.number}"' for d in self.logbook.get_lines()))}],\n'
                f'v:[{','.join(sorted(f'"{d.item.vehicle_id}"' for d in self.logbook.get_vehicles()))}],\n'
                f'pc:"{self.primary_color}",\n'
                f'tc:"{self.tint_color}",\n'
                f'}},')
