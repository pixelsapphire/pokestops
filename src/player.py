from __future__ import annotations
from data import __read_collection__
from data import *
from typing import Iterable


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


class Logbook:
    def __init__(self, player: Player):
        self.player: Player = player
        self.stop_groups: dict[str, set[Stop]] = {}
        self.lines: list[Discovery[Line]] = []
        self.vehicles: list[Discovery[Vehicle]] = []

    def add_stop(self, s: Stop) -> None:
        if s.full_name not in self.stop_groups:
            self.stop_groups[s.full_name] = set()
        self.stop_groups[s.full_name].add(s)

    def add_line(self, line: Line, date: str) -> None:
        self.lines.append(Discovery(line, date))

    def add_vehicle(self, vehicle: Vehicle, date: str) -> None:
        self.vehicles.append(Discovery(vehicle, date))

    def get_achievements(self, stops: dict[str, Stop], stop_groups: dict[str, set[str]]) -> list[AchievementProgress]:
        prog = []
        for group in self.stop_groups:
            visited = len(self.stop_groups[group])
            total = len(stop_groups[group])
            if visited == total:
                date = max(s.date_visited_by(self.player) for s in self.stop_groups[group])
                prog.append(AchievementProgress(group, visited, total, date))
            else:
                prog.append(AchievementProgress(group, visited, total))
            prog[-1].description += ', '.join(
                sorted(s.short_name for s in stops.values() if s.full_name == group))
        return sorted(prog, key=lambda p: (p.percentage(), p.completion_date), reverse=True)

    def get_n_achievements(self, stops: dict[str, Stop], stop_groups: dict[str, set[str]]) -> int:
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return len(list(filter(AchievementProgress.is_completed, self.get_achievements(stops, stop_groups))))

    def get_lines(self) -> Iterable[Discovery[Line]]:
        return reversed(self.lines)

    def get_vehicles(self) -> Iterable[Discovery[Vehicle]]:
        return reversed(self.vehicles)

    def get_n_vehicles(self) -> int:
        return len(self.vehicles)


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

    def __lt__(self, other):
        return self.nickname < other.nickname if isinstance(other, type(self)) else False

    @staticmethod
    def __init_file__(path: str, header: str = '') -> None:
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'x') as new_file:
                new_file.write(f'{header}\n')

    def __init_files__(self) -> None:
        self.__init_file__(self.__stops_file__, 'stop_id,date_visited')
        self.__init_file__(self.__ev_file__, 'stop_id')
        self.__init_file__(self.__terminals_file__, 'terminal_id,closest_arrival,closest_departure')
        self.__init_file__(self.__lines_file__, 'line_number,date_discovered')
        self.__init_file__(self.__vehicles_file__, 'vehicle_id,date_discovered')

    def __load_stops__(self, db: Database) -> None:
        stop_rows, stop_comments = get_csv_rows(self.__stops_file__)
        for row in stop_rows:
            stop = db.stops.get(row[0])
            if stop:
                stop.add_visit(Discovery(self, row[1]))
                self.logbook.add_stop(stop)
            else:
                error(f'{self.nickname} has visited stop {row[0]}, which is currently not in the database, '
                      f'comment or remove the {row[1]} entry from her stops file')
        for row in stop_comments:
            stop_id = row[0].replace('#', '').lstrip()
            if db.stops.get(stop_id):
                error(f'{self.nickname} has visited stop {stop_id}, which is now in the database, '
                      f'restore the {row[1]} entry in her stops file')

    def __load_ev_stops__(self, db: Database) -> None:
        ev_stop_rows, ev_stop_comments = get_csv_rows(self.__ev_file__)
        for row in ev_stop_rows:
            stop = db.stops.get(row[0])
            if stop:
                stop.add_visit(Discovery(self))
                self.logbook.add_stop(stop)
            else:
                error(f'{self.nickname} has visited stop {row[0]}, which is currently not in the database, '
                      f'comment or remove the entry from her EV stops file')
        for row in ev_stop_comments:
            stop_id = row[0].replace('#', '').lstrip()
            if db.stops.get(stop_id):
                error(f'{self.nickname} has visited stop {stop_id}, which is now in the database, '
                      f'restore the entry in her EV stops file')

    def __load_terminals__(self, db: Database) -> None:
        terminal_rows, terminal_comments = get_csv_rows(self.__terminals_file__)
        for row in terminal_rows:
            terminal = next((t for t in db.terminals if t.id == row[0]), None)
            if terminal:
                closest_arrival: Stop = db.stops.get(row[1])
                closest_departure: Stop = db.stops.get(row[2])
                terminal.add_player_progress(self, closest_arrival, closest_departure)
            else:
                error(f'{self.nickname} has visited terminal {row[0]}, which is currently not in the database, '
                      f'comment or remove the entry from her terminals file')
        for row in terminal_comments:
            terminal_id = row[0].replace('#', '').lstrip()
            if next((t for t in db.terminals if t.id == terminal_id), None):
                error(f'{self.nickname} has visited terminal {terminal_id}, which is now in the database, '
                      f'restore the entry in her terminals file')

    def __load_lines__(self, db: Database) -> None:
        line_rows, line_comments = get_csv_rows(self.__lines_file__)
        for row in line_rows:
            line = db.lines.get(row[0])
            if line:
                line.add_discovery(Discovery(self, row[1]))
                self.logbook.add_line(line, row[1])
            else:
                error(f'{self.nickname} has discovered line {row[0]}, which is currently not in the database, '
                      f'comment or remove the {row[1]} entry from her lines file')
        for row in line_comments:
            line_id = row[0].replace('#', '').lstrip()
            if db.lines.get(line_id):
                error(f'{self.nickname} has discovered line {line_id}, which is now in the database, '
                      f'restore the {row[1]} entry in her lines file')

    def __load_vehicles__(self, db: Database) -> None:
        vehicle_rows, vehicle_comments = get_csv_rows(self.__vehicles_file__)
        for row in vehicle_rows:
            vehicle = db.vehicles.get(row[0])
            if vehicle:
                vehicle.add_discovery(Discovery(self, row[1]))
                self.logbook.add_vehicle(vehicle, row[1])
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
            vehicle_id = row[0].replace('#', '').lstrip()
            if db.vehicles.get(vehicle_id):
                error(f'{self.nickname} has discovered vehicle #{vehicle_id}, which is now in the database, '
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
        print(f'  Reading players data from {source}... ', end='')
        # warning caused by Pycharm issue PY-70668
        # noinspection PyTypeChecker
        return __read_collection__(source, [], Player, list.append)

    def __json_entry__(self, db: Database = None) -> str:
        stops: dict[str, Stop] = db.stops if db else {}
        return (f'"{self.nickname}":{{\n'
                f's:[{','.join(sorted(f'"{s.short_name}"' for s in stops.values() if s.is_visited_by(self)))}],\n'
                f'l:[{','.join(sorted(f'"{l.item.number}"' for l in self.logbook.get_lines()))}],\n'
                f'v:[{','.join(sorted(f'"{v.item.vehicle_id}"' for v in self.logbook.get_vehicles()))}],\n'
                f'}},')
