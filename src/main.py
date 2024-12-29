import args
import folium
from announcements import *
from branca.element import Element
from gtfs import update_gtfs_data
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
    announcements: list[Announcement] = Announcement.read_list(ref.rawdata_announcements, initial_db.lines)

    initial_db.terminals = terminals
    initial_db.vehicles = vehicles
    print('  Reading players save data from their respective directories... ', end='')
    for player in initial_db.players:
        player.load_data(initial_db)
    print('Done!')

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
                    vehicles, models, initial_db.lines, initial_db.routes, initial_db.scheduled_changes, announcements)


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


def create_route_map(line: Line, db: Database, all_variants: bool) -> None:
    variant: int = 0
    for line_variant in line.stops if all_variants else [line.stops[0]]:
        variant += 1
        stops: list[Stop] = []
        for stop_id in line_variant:
            stop: Stop = db.stops.get(stop_id)
            if stop and not any(stop.full_name == s.full_name for s in stops):
                stops.append(stop)
        stops_locations: list[geopoint] = list(map(db.group_location, stops))
        lat_min: float = min(s.latitude for s in stops_locations)
        lat_max: float = max(s.latitude for s in stops_locations)
        lon_min: float = min(s.longitude for s in stops_locations)
        lon_max: float = max(s.longitude for s in stops_locations)
        lat_range: float = lat_max - lat_min
        lon_range: float = lon_max - lon_min
        coord_range: float = max(lat_range, lon_range)
        scale_factor: float = 1000 / coord_range
        points = [vector2f(12 + (s.longitude - lon_min) * scale_factor, 12 + (lat_max - s.latitude) * scale_factor)
                  for s in stops_locations]
        with open(prepare_path(f'{ref.mapdata_path}/{line.number}/{variant}.svg'), 'w') as file:
            file.write(f'<svg'
                       f' width="{24 + 1000 * lon_range / coord_range:.1f}"'
                       f' height="{24 + 1000 * lat_range / coord_range:.1f}"'
                       f' xmlns="http://www.w3.org/2000/svg">\n')
            sequence: list[vector2f] = midpoints(points)
            file.write(f'<path d="M{sequence[0].x} {sequence[0].y} ')
            for p in sequence[1:]:
                file.write(f'L{p.x:.1f} {p.y:.1f} ')
            file.write(f'" />\n')
            for p in sequence[::2]:
                file.write(f'<circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="8" />\n')
            file.write(f'<style>\n{to_css({
                'circle': {
                    'fill': 'white',
                    'stroke': f'#{line.background_color}' if line.background_color.lower() != 'ffffff' else 'black',
                    'stroke-width': '4'
                },
                'path': {
                    'fill': 'none',
                    'stroke': f'#{line.background_color}',
                    'stroke-width': '8'
                }
            })}</style>\n')
            file.write('</svg>')


def place_stop_markers(db: Database, fmap: folium.Map) -> None:
    print('  Placing Pokestops markers... ', end='')
    for stop in db.stops.values():
        stop_visits: list[Discovery] = sorted(stop.visits)
        classes: str = ' '.join(
            [f'v-{visit.item.nickname.lower()}' for visit in stop_visits] +
            [f'ev-{visit.item.nickname.lower()}' for visit in stop_visits if not visit.date.is_known()] +
            [f'r-{region.short_name}' for region in stop.regions] +
            [f'tp-{player.nickname.lower()}' for _, player, _ in stop.terminals_progress]
        )
        visited_label: str = '<br>'.join(
            [f'visited by {visit.item.nickname} {f'on {visit.date:y-m-d}' if visit.date.is_known() else 'a long time ago'}'
             for visit in sorted(stop.visits)]) if stop.visits else 'not yet visited'
        terminal_progress_label: str = '<br>'.join([f'{player.nickname}\'s closest {kind} point to {terminal.name} '
                                                    for kind, player, terminal in stop.terminals_progress])
        marker: folium.DivIcon = folium.DivIcon(
            html=f'<div class="marker {classes}">{stop.marker()}</div>',
            icon_anchor=(10, 10)
        )
        popup: folium.Popup = folium.Popup(f'<span class="stop-name">{stop.full_name} [{stop.short_name}]</span>'
                                           f'<span class="stop-visitors"><br>{visited_label}</span>'
                                           f'<span class="stop-tp"><br>{terminal_progress_label}</span>')
        # see: https://github.com/python-visualization/folium/pull/2056
        # noinspection PyTypeChecker
        folium.Marker(location=stop.location, popup=popup, icon=marker).add_to(fmap)
    print('Done!')


def place_line_markers(db: Database, fmap: folium.Map) -> None:
    print('  Placing Pokelines markers... ', end='')

    already_drawn: set[tuple[LineSegment[geopoint], HashableSet[str]]] = set()

    def draw_line(pts: Sequence[geopoint], cls: HashableSet[str]) -> None:
        if isinstance(pts, LineSegment) and (pts, cls) in already_drawn:
            return
        folium.PolyLine(fill_color=' '.join(cls),  # see: https://github.com/python-visualization/folium/issues/2055
                        locations=[pts], fill_opacity=0, weight=3, bubbling_mouse_events=False).add_to(fmap)

    for line in [line for line in db.lines.values() if not line.is_discovered()]:
        for route in line.routes:
            draw_line(db.routes[route].points, HashableSet(('undiscovered',)))

    segments_and_players: dict[LineSegment[geopoint], set[Player]] = defaultdict(set)
    for line in [line for line in db.lines.values() if line.is_discovered()]:
        for route in line.routes:
            points: list[geopoint] = db.routes[route].points
            for i in range(len(points) - 1):
                segments_and_players[LineSegment(points[i], points[i + 1])] |= {p for p in db.players if line.discovered_by(p)}
    for segment, players in segments_and_players.items():
        draw_line(segment, HashableSet(['disc'] + [f'd-{player.nickname.lower()}' for player in players]))

    segments_and_lines: dict[LineSegment[geopoint], set[Line]] = defaultdict(set)
    for line in db.lines.values():
        for route in line.routes:
            points: list[geopoint] = db.routes[route].points
            for i in range(len(points) - 1):
                segments_and_lines[LineSegment(points[i], points[i + 1])].add(line)
    for segment, lines in segments_and_lines.items():
        players_who_completed: list[Player] = [p for p in db.players if all(ln.discovered_by(p) for ln in lines)]
        if len(players_who_completed) > 0:
            draw_line(segment, HashableSet(['compl'] + [f'c-{player.nickname.lower()}' for player in players_who_completed]))

    print('Done!')


def place_terminal_markers(db: Database, fmap: folium.Map) -> None:
    def tp_message(tp: TerminalProgress) -> str:
        if tp.completed():
            return f'{tp.player.nickname} has completed this terminal'
        else:
            return f'{tp.player.nickname} has {'arrived at' if tp.arrived() else 'departed from'} this terminal'

    print('  Placing Stellar Voyage markers... ', end='')
    for terminal in db.terminals:
        classes: list[str] = [f'reached-{player.nickname.lower()}' for player in db.players if terminal.reached_by(player)]
        visited_label: str = '<br>'.join([tp_message(tp) for tp in terminal.progress if tp.reached()]
                                         ) if terminal.anybody_reached() else 'not yet reached'
        marker: folium.DivIcon = folium.DivIcon(
            html=f'<div class="marker terminal {' '.join(classes)}">T</div>',
            icon_anchor=(10, 10)
        )
        popup: folium.Popup = folium.Popup(f'<span class="stop-name">{terminal.name}</span>'
                                           f'<br><span class="stop-tp">{visited_label}</span>')
        # noinspection PyTypeChecker
        folium.Marker(location=(terminal.latitude, terminal.longitude), popup=popup, icon=marker).add_to(fmap)
    print('Done!')


def generate_map(db: Database) -> folium.Map:
    documented_visited_stops: list[Stop] = list(filter(lambda s: s.is_visited(include_ev=False), db.stops.values()))
    visible_stops = documented_visited_stops if len(documented_visited_stops) > 0 else db.stops.values()
    avg_lat = (min(s.location.latitude for s in visible_stops) + max(s.location.latitude for s in visible_stops)) / 2
    avg_lon = (min(s.location.longitude for s in visible_stops) + max(s.location.longitude for s in visible_stops)) / 2
    fmap: folium.Map = folium.Map(location=(avg_lat, avg_lon), zoom_start=12, prefer_canvas=False, zoom_control='bottomleft')

    place_stop_markers(db, fmap)
    place_line_markers(db, fmap)
    place_terminal_markers(db, fmap)

    return fmap


def build_app(db: Database, fmap: folium.Map | None) -> None:
    folium_html: str | None = None
    if build_map:
        print('  Compiling Folium map... ', end='')
        map_element: Element = fmap.get_root()
        folium_html = map_element.render()
        print('Done!')

    from player import Player
    print('  Compiling data to JavaScript... ', end='')

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

    print('Done!')

    print('  Building HTML documents... ', end='')

    builder: UIBuilder = UIBuilder(database=db, lexmap_file=ref.lexmap_polish)

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

    print('Done!')


def main() -> None:
    from player import Player
    print('Building initial database...')
    district, regions = Region.read_regions(ref.rawdata_regions)
    players: list[Player] = Player.read_list(ref.rawdata_players)
    scheduled_changes: list[StopChange] = StopChange.read_list(ref.rawdata_scheduled_changes)
    initial_db: Database = Database.partial(regions=regions, district=district, players=players,
                                            scheduled_changes=scheduled_changes)

    if update_gtfs:
        print('Updating GTFS data...')
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

    print('Building full database...')
    db: Database = load_data(initial_db)
    del initial_db

    if update_gtfs:
        print('Drawing line route diagrams... ', end='')
        clear_directory(ref.mapdata_path)
        for line in db.lines.values():
            create_route_map(line, db, False)
        print('Done!')

    fmap: folium.Map | None = None
    if build_map:
        print('Generating map data...')
        fmap = generate_map(db)
    if build_map or build_archive or build_announcements:
        print('Compiling application...')
        build_app(db, fmap)


args.validate_flags('-A', '-a', '-b', '-G', '-m', '-N', '-n', '-U')
args.validate_options('--all', '--update-all', '--build-all',
                      '--update-gtfs', '--update-announcements',
                      '--build-map', '--build-archive', '--build-announcements')

update_gtfs: bool = args.one_of_present('--update-gtfs', '--update-all', '--all', '-G', '-U', '-A')
update_announcements: bool = args.one_of_present('--update-announcements', '--update-all', '--all', '-N', '-U', '-A')
build_map: bool = args.one_of_present('--build-map', '--build-all', '--all', '-m', '-b', '-A')
build_archive: bool = args.one_of_present('--build-archive', '--build-all', '--all', '-a', '-b', '-A')
build_announcements: bool = args.one_of_present('--build-announcements', '--build-all', '--all', '-n', '-b', '-A')

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
    print_errors()
