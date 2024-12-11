import folium
import requests
import sqlite3
import sys
from postprocess import *
from uibuilder import *
from util import *


# noinspection SqlNoDataSourceInspection,DuplicatedCode,SqlInsertValues
def create_gtfs_database() -> sqlite3.Connection:
    print('    Creating temporary SQL database... ')
    db: sqlite3.Connection = sqlite3.connect(':memory:')

    with open(ref.rawdata_stops, 'r') as file:
        print(f'      Reading stops data from {ref.rawdata_stops}... ', end='')
        reader = csv.reader(file)
        header_row = next(reader)
        db.execute(f'CREATE TABLE stops ({", ".join(f'{col} TEXT' for col in header_row)})')
        db.executemany(f'INSERT INTO stops VALUES ({','.join('?' * len(header_row))})', reader)
        print('Done!')

    with open(ref.rawdata_stop_times, 'r') as file:
        print(f'      Reading stop times data from {ref.rawdata_stop_times}... ', end='')
        reader = csv.reader(file)
        header_row = next(reader)
        db.execute(f'CREATE TABLE stop_times ({", ".join(f'{col} TEXT' for col in header_row)})')
        db.executemany(f'INSERT INTO stop_times VALUES ({','.join('?' * len(header_row))})', reader)
        print('Done!')

    with open(ref.rawdata_trips, 'r') as file:
        print(f'      Reading trips data from {ref.rawdata_trips}... ', end='')
        reader = csv.reader(file)
        header_row = next(reader)
        db.execute(f'CREATE TABLE trips ({", ".join(f'{col} TEXT' for col in header_row)})')
        db.executemany(f'INSERT INTO trips VALUES ({','.join('?' * len(header_row))})', reader)
        print('Done!')

    return db


# noinspection SqlNoDataSourceInspection
def attach_stop_lines(gtfs_db: sqlite3.Connection) -> None:
    print('    Attaching line nubmers to stops... ', end='')
    cursor: sqlite3.Cursor = gtfs_db.cursor()
    cursor.execute('WITH stop_routes_groupped AS'
                   '(WITH stop_routes_ungroupped AS '
                   ' (SELECT stop_id, route_id, trip_headsign'
                   '  FROM stop_times JOIN trips USING(trip_id)'
                   '  WHERE trip_id LIKE \'%+\''
                   '  GROUP BY stop_id, route_id, trip_headsign '
                   '  ORDER BY CAST(route_id AS NUMBER))'
                   ' SELECT stop_id, GROUP_CONCAT(route_id || \':\' || trip_headsign, \'&\') AS routes'
                   ' FROM stop_routes_ungroupped'
                   ' GROUP BY stop_id)'
                   'SELECT stops.*, routes '
                   'FROM stops JOIN stop_routes_groupped USING(stop_id)')

    stops_header_row: list[str]
    with open(ref.rawdata_stops, 'r') as file:
        stops_header_row = next(csv.reader(file))

    with open(prepare_path(ref.rawdata_stops), 'w') as file:
        writer = csv.writer(file)
        writer.writerow([*stops_header_row, 'routes'])
        writer.writerows(cursor.fetchall())

    cursor.close()
    print('Done!')


# noinspection SqlNoDataSourceInspection
def attach_line_stops(gtfs_db: sqlite3.Connection) -> None:
    print('    Attaching stop codes to lines... ', end='')
    cursor: sqlite3.Cursor = gtfs_db.cursor()
    cursor.execute('SELECT route_id, trip_id, stop_code '
                   'FROM trips JOIN stop_times USING (trip_id) JOIN stops USING (stop_id)'
                   'WHERE trip_id LIKE \'%+\''
                   'GROUP BY route_id, trip_id, shape_id, stop_sequence '
                   'ORDER BY CAST(route_id AS INTEGER), trip_id, CAST(stop_sequence AS INTEGER)')

    line_stops: dict[str, dict[str, list[str]]] = {}
    for record in cursor.fetchall():
        route_id, trip_id, stop_code = record
        if route_id not in line_stops:
            line_stops[route_id] = {}
        if trip_id not in line_stops[route_id]:
            line_stops[route_id][trip_id] = []
        line_stops[route_id][trip_id].append(stop_code)

    line_stops_unique: dict[str, list[list[str]]] = {}
    for route_id, trips in line_stops.items():
        for trip_id, trip_stops in trips.items():
            if route_id not in line_stops_unique:
                line_stops_unique[route_id] = []
            if ((trip_id.startswith('1_') or not any(filter(lambda t: t.startswith('1_'), line_stops[route_id].keys())))
                    and trip_stops not in line_stops_unique[route_id]):
                line_stops_unique[route_id].append(trip_stops)

    routes_header_row: list[str]
    routes_data: list[list[str]]
    with open(ref.rawdata_lines, 'r') as file:
        reader: csv.reader = csv.reader(file)
        routes_header_row = next(reader)
        routes_data = list(reader)

    with open(prepare_path(ref.rawdata_lines), 'w') as file:
        writer: csv.writer = csv.writer(file)
        writer.writerow([*routes_header_row, 'stops'])
        for route in routes_data:
            writer.writerow([*route, '|'.join(map(lambda stops: '&'.join(stops), line_stops_unique[route[0]]))])

    cursor.close()
    print('Done!')


def make_update_report(old_data: Database, new_data: Database) -> None:
    added_stops: set[Stop] = {s for s in new_data.stops.values() if s not in old_data.stops.values()}
    removed_stops: set[Stop] = {s for s in old_data.stops.values() if s not in new_data.stops.values()}
    added_lines: set[str] = {r for r in new_data.lines.keys() if r not in old_data.lines.keys()}
    removed_lines: set[str] = {r for r in old_data.lines.keys() if r not in new_data.lines.keys()}
    changed_lines: set[str] = {r for r in new_data.lines.keys()
                               if r in old_data.lines.keys() and new_data.lines[r].stops != old_data.lines[r].stops}
    if not added_stops and not removed_stops and not added_lines and not removed_lines and not changed_lines:
        print('  No changes, no report created.')
    else:
        print('  Data has changed, creating report... ', end='')
        lines: int = max(len(added_lines), len(removed_lines), len(changed_lines))
        lexmap: dict[str, float] = create_lexicographic_mapping(file_to_string(ref.lexmap_polish))
        line_key = lambda line: int(line) if line.isdigit() else int(re.sub(r'\D', '', line)) - lines
        stop_key = lambda stop: lexicographic_sequence(f'{stop.full_name}{stop.short_name}', lexmap)
        with open(prepare_path(ref.report_gtfs), 'w') as file:
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


def update_gtfs_data(first_update: bool, initial_db: Database) -> None:
    old_db: Database = Database.partial()
    if not first_update:
        if os.path.exists(ref.rawdata_stops):
            old_db.add_collection('stops', Stop.read_stops(ref.rawdata_stops, initial_db)[0])
        if os.path.exists(ref.rawdata_lines):
            old_db.add_collection('lines', Line.read_dict(ref.rawdata_lines))
    print(f'  Downloading latest GTFS data from {ref.url_ztm_gtfs}... ', end='')
    try:
        response: requests.Response = requests.get(ref.url_ztm_gtfs)
    except requests.RequestException as e:
        print(f'Failed!\n  Connection error: {e}')
        return
    if response.status_code != 200:
        print(f'Failed!\n  Request error: {response.reason}')
        return
    print('Done!')
    print('  Extracting GTFS data... ', end='')
    with open(prepare_path(ref.tmpdata_gtfs), 'wb') as file:
        file.write(response.content)
    with util.zip_file(ref.tmpdata_gtfs, 'r') as zip_ref:
        zip_ref.extract_as('stops.txt', ref.rawdata_stops)
        zip_ref.extract_as('stop_times.txt', ref.rawdata_stop_times)
        zip_ref.extract_as('trips.txt', ref.rawdata_trips)
        zip_ref.extract_as('routes.txt', ref.rawdata_lines)
    os.remove(ref.tmpdata_gtfs)
    print('Done!')
    print('  Processing GTFS data... ')
    gtfs_db: sqlite3.Connection = create_gtfs_database()
    attach_stop_lines(gtfs_db)
    attach_line_stops(gtfs_db)
    os.remove(ref.rawdata_stop_times)
    os.remove(ref.rawdata_trips)

    new_stops, new_stop_groups = Stop.read_stops(ref.rawdata_stops, initial_db)
    new_lines = Line.read_dict(ref.rawdata_lines)

    initial_db.add_collection('stops', new_stops)
    initial_db.add_collection('stop_groups', new_stop_groups)
    initial_db.add_collection('lines', new_lines)

    if first_update:
        print('  GTFS database created.')
    else:
        print('  GTFS database updated.')
        make_update_report(old_db, initial_db)


def process_players_data(players: list[Player], stops: dict[str, Stop],
                         terminals: list[Terminal], vehicles: dict[str, Vehicle]):
    for player in players:
        player.init_files()
        with open(player.stops_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if len(row) == 0:
                    continue
                elif not row[0].lstrip().startswith('#'):
                    stop = stops.get(row[0])
                    if stop:
                        stop.add_visit(Discovery(player.nickname, row[1]))
                        player.add_stop(stop)
                    else:
                        print(f'Stop {row[0].lstrip()} not found, remove {player.nickname}\'s entry from her save file')
                else:
                    stop_id = row[0].replace('#', '').lstrip()
                    if stops.get(stop_id):
                        print(f'Found a commented out {player.nickname}\'s {stop_id} save file entry, restore it')
        with open(player.ev_file) as file:
            for stop_id in map(lambda s: s.strip(), file.readlines()):
                if len(stop_id) == 0:
                    continue
                elif not stop_id.startswith('#'):
                    stop = stops.get(stop_id)
                    if stop:
                        stop.add_visit(Discovery(player.nickname, '2000-01-01'))
                        player.add_stop(stop)
                    else:
                        print(f'Stop {stop_id} not found, remove {player.nickname}\'s entry from her EV file')
                else:
                    stop_id = stop_id.replace('#', '').lstrip()
                    if stops.get(stop_id):
                        print(f'Found a commented out {player.nickname}\'s {stop_id} EV file entry, restore it')
        with open(player.terminals_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if len(row) == 0:
                    continue
                elif not row[0].lstrip().startswith('#'):
                    terminal = next((t for t in terminals if t.id == row[0]), None)
                    if terminal:
                        closest_arrival: Stop = stops.get(row[1])
                        closest_departure: Stop = stops.get(row[2])
                        terminal.add_player_progress(player, closest_arrival, closest_departure)
                    else:
                        print(f'Terminal {row[0]} not found, remove {player.nickname}\'s entry from her terminals file')
        with open(player.vehicles_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if len(row) == 0:
                    continue
                elif not row[0].lstrip().startswith('#'):
                    vehicle_id = row[0].lstrip()
                    vehicle = vehicles.get(vehicle_id)
                    if vehicle:
                        vehicle.add_discovery(Discovery(player.nickname, row[1]))
                        player.add_vehicle(vehicle, row[1])
                    else:
                        combined: str | None = next((v for v in vehicles.keys() if
                                                     v.startswith(f'{vehicle_id}+') or v.endswith(f'+{vehicle_id}') or
                                                     v == f'{'+'.join(vehicle_id.split('+')[::-1])}'), None)
                        if combined:
                            print(f'Vehicle #{vehicle_id} not found, but there is vehicle #{combined},'
                                  f' modify {player.nickname}\'s entry in her vehicles file')
                        else:
                            print(f'Vehicle #{vehicle_id} not found, remove {player.nickname}\'s '
                                  f'entry from her vehicles file or add a definition to vehicles.csv')
                else:
                    vehicle_id = row[0].replace('#', '').lstrip()
                    if vehicles.get(vehicle_id):
                        print(f'Found a commented out {player.nickname}\'s {vehicle_id} vehicles file entry, restore it')


def load_data(initial_db: Database) -> Database:
    players: list[Player] = initial_db.players
    regions: dict[str, Region] = initial_db.regions
    district: Region = initial_db.district
    if not initial_db.has_collection('stops') or not initial_db.has_collection('lines'):
        initial_db.add_collection('stops', (stops_and_groups := Stop.read_stops(ref.rawdata_stops, initial_db))[0])
        initial_db.add_collection('stop_groups', stops_and_groups[1])
        initial_db.add_collection('lines', Line.read_dict(ref.rawdata_lines))
    stops: dict[str, Stop] = initial_db.stops
    stop_groups: dict[str, set[str]] = initial_db.stop_groups
    terminals: list[Terminal] = Terminal.read_list(ref.rawdata_terminals, stops)
    carriers: dict[str, Carrier] = Carrier.read_dict(ref.rawdata_carriers)
    models: dict[str, VehicleModel] = VehicleModel.read_dict(ref.rawdata_vehicle_models)
    vehicles: dict[str, Vehicle] = Vehicle.read_dict(ref.rawdata_vehicles, carriers, models)
    lines: dict[str, Line] = initial_db.lines

    process_players_data(players, stops, terminals, vehicles)

    ever_visited_stops: list[Stop] = list(filter(lambda s: s.visited(), stops.values()))
    progress: dict[str, dict[str, float]] = {
        **{r.short_name: {
            **{
                p.nickname: round(len(list(filter(lambda s: s in r and s.visited_by(p, False), ever_visited_stops))) /
                                  len(list(filter(lambda s: s in r, stops.values()))) * 100, 1) for p in players
            },
            **{
                f'ev-{p.nickname}': round(len(list(filter(lambda s: s in r and s.visited_by(p), ever_visited_stops))) /
                                          len(list(filter(lambda s: s in r, stops.values()))) * 100, 1) for p in players
            },
        } for r in regions.values()},
        'SV': {
            f'{p.nickname}': round(sum(1 if t.completed_by(p) else 0.5 if t.reached_by(p) else 0
                                       for t in terminals) / len(terminals) * 100, 1) for p in players
        }
    }

    return Database(players, progress, stops, stop_groups, terminals, carriers, regions, district, vehicles, models, lines)


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
            stop: Stop = db.stops[stop_id]
            if not any(stop.full_name == s.full_name for s in stops):
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


def generate_map(db: Database) -> folium.Map:
    documented_visited_stops: list[Stop] = list(filter(lambda s: s.visited(include_ev=False), db.stops.values()))
    visible_stops = documented_visited_stops if len(documented_visited_stops) > 0 else db.stops.values()
    avg_lat = (min(s.location.latitude for s in visible_stops) + max(s.location.latitude for s in visible_stops)) / 2
    avg_lon = (min(s.location.longitude for s in visible_stops) + max(s.location.longitude for s in visible_stops)) / 2
    fmap: folium.Map = folium.Map(location=(avg_lat, avg_lon), zoom_start=12, prefer_canvas=True, zoom_control='bottomleft')

    print('  Placing markers... ', end='')
    for stop in db.stops.values():
        stop_visits: list[Discovery] = sorted(stop.visits)
        # noinspection PyUnresolvedReferences
        classes: str = ' '.join(
            [f'v-{visit.name.lower()}' for visit in stop_visits] +
            [f'ev-{visit.name.lower()}' for visit in stop_visits if visit.date == '2000-01-01'] +
            [f'r-{region.short_name}' for region in stop.regions] +
            [f'tp-{player.nickname.lower()}' for _, player, _ in stop.terminals_progress]
        )
        visited_label: str = '<br>'.join(
            [f'visited by {visit.name} {f'on {visit.date}' if visit.date != '2000-01-01' else 'a long time ago'}'
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
        # noinspection PyTypeChecker
        folium.Marker(location=stop.location, popup=popup, icon=marker).add_to(fmap)

    def tp_message(tp: TerminalProgress) -> str:
        if tp.completed():
            return f'{tp.player.nickname} has completed this terminal'
        else:
            return f'{tp.player.nickname} has {'arrived at' if tp.arrived() else 'departed from'} this terminal'

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

    return fmap


def build_app(fmap: folium.Map, db: Database) -> None:
    print('  Compiling data to JavaScript... ', end='')

    with open(prepare_path(ref.compileddata_stops), 'w') as file:
        file.write(f'const stops = {{\n{'\n'.join(map(Stop.json_entry, db.stops.values()))}\n}};')
        file.write(f'const terminals = {{\n{'\n'.join(map(Terminal.json_entry, db.terminals))}\n}};')

    with open(prepare_path(ref.compileddata_vehicles), 'w') as file:
        file.write(f'const vehicle_models = {{\n{'\n'.join(map(VehicleModel.json_entry, db.models.values()))}\n}};\n')
        file.write(f'const carriers = {{\n{'\n'.join(map(Carrier.json_entry, db.carriers.values()))}\n}};\n')
        file.write(f'const vehicles = {{\n{'\n'.join(map(Vehicle.json_entry, db.vehicles.values()))}\n}};')

    with open(prepare_path(ref.compileddata_lines), 'w') as file:
        file.write(f'const lines = {{\n{'\n'.join(map(Line.json_entry, db.lines.values()))}\n}};')

    with open(prepare_path(ref.compileddata_players), 'w') as file:
        file.write(f'const players = {{\n{'\n'.join(map(lambda p: Player.json_entry(p, db), db.players))}\n}};')

    folium_html: str = fmap.get_root().render()
    map_script: str = folium_html[folium_html.rfind('<script>') + 8:folium_html.rfind('</script>')]
    with open(prepare_path(ref.compileddata_map), 'w') as script_file:
        script_file.write(clean_js(map_script))

    print('Done!')
    print('  Building HTML documents... ', end='')

    html_application: Html = create_application(folium_html, db)
    rendered_application: str = clean_html(html_application.render(True, True))
    with open(prepare_path(ref.document_map), 'w') as file:
        file.write(rendered_application)

    html_archive: Html = create_archive(db)
    rendered_archive: str = clean_html(html_archive.render(True, True))
    with open(prepare_path(ref.document_archive), 'w') as file:
        file.write(rendered_archive)

    print('Done!')


def main() -> None:
    print('Building initial database...')
    district, regions = Region.read_regions(ref.rawdata_regions)
    players: list[Player] = Player.read_list(ref.rawdata_players)
    initial_db: Database = Database.partial(regions=regions, district=district, players=players)

    if update_ztm_stops:
        print('Updating GTFS data...')
        update_gtfs_data(not os.path.exists(ref.rawdata_stops), initial_db)
    else:
        if not os.path.exists(ref.rawdata_stops):
            raise FileNotFoundError(f'{ref.rawdata_stops} not found. '
                                    f'Run the script with the --update flag to download the latest data.')
        if not os.path.exists(ref.rawdata_lines):
            raise FileNotFoundError(f'{ref.rawdata_lines} not found. '
                                    f'Run the script with the --update flag to download the latest data.')

    print('Building full database...')
    db: Database = load_data(initial_db)
    del initial_db

    print('Generating map data...')
    if update_ztm_stops:
        print('Drawing line route diagrams... ', end='')
        for line in db.lines.values():
            create_route_map(line, db, False)
        print('Done!')

    if update_map:
        fmap: folium.Map = generate_map(db)
        print('Compiling application...')
        build_app(fmap, db)


update_ztm_stops = '--update' in sys.argv or '-u' in sys.argv
update_map = '--map' in sys.argv or '-m' in sys.argv
if __name__ == '__main__':
    main()
