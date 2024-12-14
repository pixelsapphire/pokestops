import folium
import gtfs
from postprocess import *
from uibuilder import *
from util import *


def load_data(initial_db: Database) -> Database:
    players: list[Player] = initial_db.players
    regions: dict[str, Region] = initial_db.regions
    if not initial_db.has_collection('stops') or not initial_db.has_collection('lines'):
        initial_db.add_collection('stops', (stops_and_groups := Stop.read_stops(ref.rawdata_stops, initial_db))[0])
        initial_db.add_collection('stop_groups', stops_and_groups[1])
        initial_db.add_collection('lines', Line.read_dict(ref.rawdata_lines))
    stops: dict[str, Stop] = initial_db.stops
    terminals: list[Terminal] = Terminal.read_list(ref.rawdata_terminals, stops)
    carriers: dict[str, Carrier] = Carrier.read_dict(ref.rawdata_carriers)
    models: dict[str, VehicleModel] = VehicleModel.read_dict(ref.rawdata_vehicle_models)
    vehicles: dict[str, Vehicle] = Vehicle.read_dict(ref.rawdata_vehicles, carriers, models)

    initial_db.add_collection('terminals', terminals)
    initial_db.add_collection('vehicles', vehicles)
    print('  Reading players save data from their respective directories... ', end='')
    for player in initial_db.players:
        player.load_data(initial_db)
    print('Done!')

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
        'SV': {
            f'{p.nickname}': round(sum(1 if t.completed_by(p) else 0.5 if t.reached_by(p) else 0
                                       for t in terminals) / len(terminals) * 100, 1) for p in players
        }
    }

    return Database(players, progress, stops, initial_db.stop_groups, terminals,
                    carriers, regions, initial_db.district, vehicles, models, initial_db.lines)


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
    documented_visited_stops: list[Stop] = list(filter(lambda s: s.is_visited(include_ev=False), db.stops.values()))
    visible_stops = documented_visited_stops if len(documented_visited_stops) > 0 else db.stops.values()
    avg_lat = (min(s.location.latitude for s in visible_stops) + max(s.location.latitude for s in visible_stops)) / 2
    avg_lon = (min(s.location.longitude for s in visible_stops) + max(s.location.longitude for s in visible_stops)) / 2
    fmap: folium.Map = folium.Map(location=(avg_lat, avg_lon), zoom_start=12, prefer_canvas=True, zoom_control='bottomleft')

    print('  Placing markers... ', end='')
    for stop in db.stops.values():
        stop_visits: list[Discovery] = sorted(stop.visits)
        # noinspection PyUnresolvedReferences
        classes: str = ' '.join(
            [f'v-{visit.item.nickname.lower()}' for visit in stop_visits] +
            [f'ev-{visit.item.nickname.lower()}' for visit in stop_visits if not visit.date] +
            [f'r-{region.short_name}' for region in stop.regions] +
            [f'tp-{player.nickname.lower()}' for _, player, _ in stop.terminals_progress]
        )
        visited_label: str = '<br>'.join(
            [f'visited by {visit.item.nickname} {f'on {visit.date}' if visit.date else 'a long time ago'}'
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
    from player import Player
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


def main() -> None:
    from player import Player
    print('Building initial database...')
    district, regions = Region.read_regions(ref.rawdata_regions)
    players: list[Player] = Player.read_list(ref.rawdata_players)
    initial_db: Database = Database.partial(regions=regions, district=district, players=players)

    if update_ztm_stops:
        print('Updating GTFS data...')
        gtfs.update_gtfs_data(not os.path.exists(ref.rawdata_stops), initial_db)
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
        print('Done!')


update_ztm_stops: bool = '--update' in sys.argv or '-u' in sys.argv
update_map: bool = '--map' in sys.argv or '-m' in sys.argv
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
    print_errors()
