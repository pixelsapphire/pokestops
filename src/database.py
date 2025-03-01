from __future__ import annotations
from announcements import Announcement
from data import *
from player import Player
from typing import get_args


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
        old_stops: set[Stop] = coalesce(self.__old_data__.stops, {}).values() if self.__old_data__ else set()
        old_lines: dict[str, Line] = coalesce(self.__old_data__.lines, {}) if self.__old_data__ else {}
        old_announcements: set[Announcement] = coalesce(self.__old_data__.announcements, set()) if self.__old_data__ else set()
        added_stops: set[Stop] = {s for s in self.stops.values() if s not in old_stops}
        removed_stops: set[Stop] = {s for s in old_stops if s not in self.stops.values()}
        changed_stops: set[tuple[Stop, Stop]] = set()
        added_lines: set[str] = {r for r in self.lines.keys() if r not in old_lines.keys()}
        removed_lines: set[str] = {r for r in old_lines.keys() if r not in self.lines.keys()}
        changed_lines: set[str] = {r for r in self.lines.keys() if r in old_lines.keys() and
                                   self.lines[r].variants != old_lines[r].variants}
        added_announcements: set[Announcement] = {a for a in self.announcements if a not in old_announcements}
        removed_announcements: set[Announcement] = {a for a in old_announcements if a not in self.announcements}
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


def load_database() -> Database:
    log('Loading database...')
    district, regions = Region.read_regions(ref.rawdata_regions)
    players: list[Player] = Player.read_list(ref.rawdata_players)
    carriers: dict[str, Carrier] = Carrier.read_dict(ref.rawdata_carriers)
    scheduled_changes: list[StopChange] = StopChange.read_list(ref.rawdata_scheduled_changes)
    models: dict[str, VehicleModel] = VehicleModel.read_dict(ref.rawdata_vehicle_models)
    vehicles: dict[str, Vehicle] = Vehicle.read_dict(ref.rawdata_vehicles, carriers, models)
    raids: list[Raid] = Raid.read_list(ref.rawdata_raids, players)
    initial_db: Database = Database.partial(regions=regions, district=district, players=players,
                                            scheduled_changes=scheduled_changes, carriers=carriers,
                                            models=models, vehicles=vehicles, raids=raids)
    if not os.path.exists(ref.rawdata_stops) or not os.path.exists(ref.rawdata_routes) or not os.path.exists(ref.rawdata_lines):
        return initial_db
    initial_db.stops = (stops_and_groups := Stop.read_stops(ref.rawdata_stops, initial_db))[0]
    initial_db.stop_groups = stops_and_groups[1]
    initial_db.routes = Route.read_dict(ref.rawdata_routes)
    initial_db.lines = Line.read_dict(ref.rawdata_lines)
    stops: dict[str, Stop] = initial_db.stops
    terminals: list[Terminal] = Terminal.read_list(ref.rawdata_terminals, stops)
    announcements: list[Announcement] = Announcement.read_list(ref.rawdata_announcements, initial_db.lines) \
        if os.path.exists(ref.rawdata_announcements) else []

    initial_db.terminals = terminals
    initial_db.vehicles = vehicles
    log('  Reading players save data from their respective directories... ', end='')
    for player in players:
        player.load_data(initial_db)
    log('Done!')

    for vehicle in vehicles.values():
        if vehicle.is_discovered() and vehicle.model is None:
            error('Vehicle without specified model marked as found:', vehicle.vehicle_id)

    ever_visited_stops: list[Stop] = list(filter(lambda s: s.is_visited(), stops.values()))
    progress: dict[str, dict[str, float]] = {
        **{r.short_name: {
            **{
                p.nickname: round(len(list(filter(lambda s: s in r and s.is_visited_by(p, False), ever_visited_stops))) /
                                  max(len(list(filter(lambda s: s in r, stops.values()))), 1) * 100, 1) for p in players
            },
            **{
                f'ev-{p.nickname}': round(len(list(filter(lambda s: s in r and s.is_visited_by(p), ever_visited_stops))) /
                                          max(len(list(filter(lambda s: s in r, stops.values()))), 1) * 100, 1) for p in players
            },
        } for r in regions.values()},
        'LN': {
            f'{p.nickname}': round(sum(1 if ln.discovered_by(p) else 0 for ln in initial_db.lines.values()) /
                                   max(len(initial_db.lines), 1) * 100, 1) for p in players
        },
        'SV': {
            f'{p.nickname}': round(sum(1 if t.completed_by(p) else 0.5 if t.reached_by(p) else 0
                                       for t in terminals) / max(len(terminals), 1) * 100, 1) for p in players
        }
    }

    return Database(players, progress, stops, initial_db.stop_groups, terminals, carriers, regions, initial_db.district,
                    vehicles, models, initial_db.routes, initial_db.lines, raids, initial_db.scheduled_changes, announcements)
