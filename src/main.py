import args
from announcements import *
from geo import *
from gtfs import update_gtfs_data
from log import print_errors
from postprocess import *
from uibuilder import *
from util import *


def load_data(initial_db: Database) -> Database:
    players: list[Player] = initial_db.players
    regions: dict[str, Region] = initial_db.regions
    if 'stops' not in initial_db or 'lines' not in initial_db:
        initial_db.stops = (stops_and_groups := Stop.read_stops(ref.rawdata_stops, initial_db))[0]
        initial_db.stop_groups = stops_and_groups[1]
        initial_db.routes = Route.read_dict(ref.rawdata_routes)
        initial_db.lines = Line.read_dict(ref.rawdata_lines)
    stops: dict[str, Stop] = initial_db.stops
    terminals: list[Terminal] = Terminal.read_list(ref.rawdata_terminals, stops)
    carriers: dict[str, Carrier] = Carrier.read_dict(ref.rawdata_carriers)
    models: dict[str, VehicleModel] = VehicleModel.read_dict(ref.rawdata_vehicle_models)
    vehicles: dict[str, Vehicle] = Vehicle.read_dict(ref.rawdata_vehicles, carriers, models)
    raids: list[Raid] = Raid.read_list(ref.rawdata_raids, players)
    announcements: list[Announcement] = Announcement.read_list(ref.rawdata_announcements, initial_db.lines)

    initial_db.terminals = terminals
    initial_db.vehicles = vehicles
    log('  Reading players save data from their respective directories... ', end='')
    for player in initial_db.players:
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
                                  len(list(filter(lambda s: s in r, stops.values()))) * 100, 1) for p in players
            },
            **{
                f'ev-{p.nickname}': round(len(list(filter(lambda s: s in r and s.is_visited_by(p), ever_visited_stops))) /
                                          len(list(filter(lambda s: s in r, stops.values()))) * 100, 1) for p in players
            },
        } for r in regions.values()},
        'LN': {
            f'{p.nickname}': round(sum(1 if ln.discovered_by(p) else 0
                                       for ln in initial_db.lines.values()) / len(initial_db.lines) * 100, 1) for p in players
        },
        'SV': {
            f'{p.nickname}': round(sum(1 if t.completed_by(p) else 0.5 if t.reached_by(p) else 0
                                       for t in terminals) / len(terminals) * 100, 1) for p in players
        }
    }

    return Database(players, progress, stops, initial_db.stop_groups, terminals, carriers, regions, initial_db.district,
                    vehicles, models, initial_db.routes, initial_db.lines, raids, initial_db.scheduled_changes, announcements)


def create_line_map(line: Line, db: Database, all_variants: bool) -> None:
    variant: int = 0
    for line_variant in line.variants if all_variants else [line.variants[0]]:
        variant += 1
        stops: list[Stop] = []
        for stop_id in line_variant:
            stop: Stop = db.stops.get(stop_id)
            if stop and not any(stop.full_name == s.full_name for s in stops):
                stops.append(stop)
        stops_locations: list[geopoint] = list(map(db.group_location, stops))
        create_route_diagram(stops_locations, line.background_color, f'{ref.mapdata_paths_lines}/{line.number}/{variant}.svg')


def create_raid_map(raid: Raid) -> None:
    stops_locations: list[list[geopoint]] = [r.shape for r in raid.routes if r.shape_defined()]
    create_multi_route_map(stops_locations, ref.color_raid_route, f'{ref.mapdata_paths_raids}/{raid.raid_id}.svg')


def build_app(db: Database) -> None:
    builder: UIBuilder = UIBuilder(database=db, lexmap_file=ref.lexmap_polish)

    folium_html: str | None = None
    if build_map:
        log('  Building Folium map...')
        fmap: Map = builder.build_fmap()
        log('    Compiling... ', end='')
        folium_html = fmap.get_root().render()
        log('Done!')

    from player import Player
    log('  Compiling data to JavaScript... ', end='')

    with open(prepare_path(ref.compileddata_stops), 'w') as file:
        file.write(f'const stops = {{\n{'\n'.join(map(Stop.json_entry, sorted(db.stops.values())))}\n}};')
        file.write(f'const terminals = {{\n{'\n'.join(map(Terminal.json_entry, db.terminals))}\n}};')

    with open(prepare_path(ref.compileddata_vehicles), 'w') as file:
        file.write(f'const vehicle_models = {{\n{'\n'.join(map(VehicleModel.json_entry, db.models.values()))}\n}};\n')
        file.write(f'const carriers = {{\n{'\n'.join(map(Carrier.json_entry, db.carriers.values()))}\n}};\n')
        file.write(f'const vehicles = {{\n{'\n'.join(map(Vehicle.json_entry, db.vehicles.values()))}\n}};')

    with open(prepare_path(ref.compileddata_lines), 'w') as file:
        file.write(f'const lines = {{\n{'\n'.join(map(Line.json_entry, db.lines.values()))}\n}};')

    with open(prepare_path(ref.compileddata_players), 'w') as file:
        file.write(f'const players = {{\n{'\n'.join(map(Player.json_entry, db.players))}\n}};')

    if folium_html is not None:
        map_script: str = folium_html[folium_html.rfind('<script>') + 8:folium_html.rfind('</script>')]
        with open(prepare_path(ref.compileddata_map), 'w') as script_file:
            script_file.write(clean_js(map_script))

    log('Done!\n  Building HTML documents... ', end='')

    if build_map:
        map_html: str = clean_html(builder.create_map(folium_html).render())
        with open(prepare_path(ref.document_map), 'w') as file:
            file.write(map_html)

    if build_archive:
        archive_html: str = clean_html(builder.create_archive().render())
        with open(prepare_path(ref.document_archive), 'w') as file:
            file.write(archive_html)

    if build_announcements:
        announcements_html: str = clean_html(builder.create_announcements().render())
        with open(prepare_path(ref.document_announcements), 'w') as file:
            file.write(announcements_html)

    if build_raids:
        [create_raid_map(raid) for raid in db.raids]
        raids_html: str = clean_html(builder.create_raids().render())
        with open(prepare_path(ref.document_raids), 'w') as file:
            file.write(raids_html)

    log('Done!')


def main() -> None:
    from player import Player
    log('Building initial database...')
    district, regions = Region.read_regions(ref.rawdata_regions)
    players: list[Player] = Player.read_list(ref.rawdata_players)
    scheduled_changes: list[StopChange] = StopChange.read_list(ref.rawdata_scheduled_changes)
    initial_db: Database = Database.partial(regions=regions, district=district, players=players,
                                            scheduled_changes=scheduled_changes)

    if update_gtfs:
        log('Updating GTFS data...')
        update_gtfs_data(not os.path.exists(ref.rawdata_stops), initial_db)
    else:
        if not os.path.exists(ref.rawdata_stops):
            raise FileNotFoundError(f'{ref.rawdata_stops} not found. '
                                    f'Run the script with the --update-gtfs option to download the latest data.')
        if not os.path.exists(ref.rawdata_routes):
            raise FileNotFoundError(f'{ref.rawdata_routes} not found. '
                                    f'Run the script with the --update-gtfs option to download the latest data.')
        if not os.path.exists(ref.rawdata_lines):
            raise FileNotFoundError(f'{ref.rawdata_lines} not found. '
                                    f'Run the script with the --update-gtfs option to download the latest data.')

    if update_announcements:
        fetch_announcements(not os.path.exists(ref.rawdata_announcements), initial_db)
    elif not os.path.exists(ref.rawdata_announcements):
        raise FileNotFoundError(f'{ref.rawdata_announcements} not found. '
                                f'Run the script with the --update-announcements option to download the latest data.')

    if update_gtfs or update_announcements:
        initial_db.make_update_report()

    log('Building full database...')
    db: Database = load_data(initial_db)
    del initial_db

    if update_gtfs:
        log('Drawing line route diagrams... ', end='')
        clear_directory(ref.mapdata_paths_lines)
        for line in db.lines.values():
            create_line_map(line, db, False)
        log('Done!')

    if build_map or build_archive or build_announcements or build_raids:
        log('Compiling application...')
        build_app(db)


__options__: dict[str, str] = {
    '-A': '--all',
    '-U': '--update-all',
    '-G': '--update-gtfs',
    '-N': '--update-announcements',
    '-b': '--build-all',
    '-m': '--build-map',
    '-a': '--build-archive',
    '-n': '--build-announcements',
    '-r': '--build-raids',
}
args.validate_flags(*__options__.keys())
args.validate_options(*__options__.values())

update_gtfs: bool = args.one_of_present('--update-gtfs', '--update-all', '--all', '-G', '-U', '-A')
update_announcements: bool = args.one_of_present('--update-announcements', '--update-all', '--all', '-N', '-U', '-A')
build_map: bool = args.one_of_present('--build-map', '--build-all', '--all', '-m', '-b', '-A')
build_archive: bool = args.one_of_present('--build-archive', '--build-all', '--all', '-a', '-b', '-A')
build_announcements: bool = args.one_of_present('--build-announcements', '--build-all', '--all', '-n', '-b', '-A')
build_raids: bool = args.one_of_present('--build-raids', '--build-all', '--all', '-r', '-b', '-A')

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
    print_errors()
