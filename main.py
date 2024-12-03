import folium
import ref
import requests
import sqlite3
import sys
from postprocess import *
from uibuilder import *


# noinspection SqlNoDataSourceInspection,DuplicatedCode
def attach_stop_routes() -> None:
    gtfs_db: sqlite3.Connection = sqlite3.connect(':memory:')

    with open(ref.rawdata_stops, 'r') as file:
        reader = csv.reader(file)
        header_row = next(reader)
        stops_header_row = header_row
        gtfs_db.execute(f'CREATE TABLE stops ({", ".join(f'{col} TEXT' for col in header_row)})')
        gtfs_db.executemany(f'INSERT INTO stops VALUES ({','.join('?' * len(header_row))})', reader)

    with open(ref.rawdata_stop_times, 'r') as file:
        reader = csv.reader(file)
        header_row = next(reader)
        gtfs_db.execute(f'CREATE TABLE stop_times ({", ".join(f'{col} TEXT' for col in header_row)})')
        gtfs_db.executemany(f'INSERT INTO stop_times VALUES ({','.join('?' * len(header_row))})', reader)

    with open(ref.rawdata_trips, 'r') as file:
        reader = csv.reader(file)
        header_row = next(reader)
        gtfs_db.execute(f'CREATE TABLE trips ({", ".join(f'{col} TEXT' for col in header_row)})')
        gtfs_db.executemany(f'INSERT INTO trips VALUES ({','.join('?' * len(header_row))})', reader)

    cursor = gtfs_db.cursor()
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

    with open(ref.rawdata_stops, 'w') as file:
        writer = csv.writer(file)
        writer.writerow([*stops_header_row, 'routes'])
        writer.writerows(cursor.fetchall())


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
                        stop.add_visit(Visit(player.nickname, row[1]))
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
                        stop.add_visit(Visit(player.nickname, '2000-01-01'))
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
    stops, stop_groups = Stop.read_stops(ref.rawdata_stops, initial_db)
    initial_db.add_collection('stops', stops)
    terminals: list[Terminal] = Terminal.read_list(ref.rawdata_terminals, stops)
    carriers: dict[str, Carrier] = Carrier.read_dict(ref.rawdata_carriers)
    models: dict[str, VehicleModel] = VehicleModel.read_dict(ref.rawdata_vehicle_models)
    vehicles: dict[str, Vehicle] = Vehicle.read_dict(ref.rawdata_vehicles, carriers, models)

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

    return Database(players, progress, stops, stop_groups, terminals, carriers, regions, district, vehicles, models)


def build_app(fmap: folium.Map, db: Database) -> None:
    folium_html: str = fmap.get_root().render()
    map_script: str = folium_html[folium_html.rfind('<script>') + 8:folium_html.rfind('</script>')]
    with open(ref.compileddata_map, 'w') as script_file:
        script_file.write(clean_js(map_script))

    html_application: Html = create_application(folium_html, db)
    rendered_application: str = clean_html(html_application.render(True, True))
    with open(ref.document_map, 'w') as file:
        file.write(rendered_application)

    with open(ref.compileddata_stops, 'w') as file:
        file.write(f'const stops = {{\n{'\n'.join(map(Stop.json_entry, db.stops.values()))}\n}};')
        file.write(f'const terminals = {{\n{'\n'.join(map(Terminal.json_entry, db.terminals))}\n}};')

    with open(ref.compileddata_vehicles, 'w') as file:
        file.write(f'const vehicle_models = {{\n{'\n'.join(map(VehicleModel.json_entry, db.models.values()))}\n}};\n')
        file.write(f'const carriers = {{\n{'\n'.join(map(Carrier.json_entry, db.carriers.values()))}\n}};\n')
        file.write(f'const vehicles = {{\n{'\n'.join(map(Vehicle.json_entry, db.vehicles.values()))}\n}};')

    with open(ref.compileddata_players, 'w') as file:
        file.write(f'const players = {{\n{'\n'.join(map(lambda p: p.json_entry(db.stops), db.players))}\n}};')

    html_archive: Html = create_archive(db)
    rendered_archive: str = clean_html(html_archive.render(True, True))
    with open(ref.document_archive, 'w') as file:
        file.write(rendered_archive)


def main() -> None:
    district, regions = Region.read_regions(ref.rawdata_regions)
    players: list[Player] = Player.read_list(ref.rawdata_players)
    initial_db: Database = Database.partial(regions=regions, district=district, players=players)

    old_stops = {}
    first_update = not os.path.exists(ref.rawdata_stops)
    if update_ztm_stops:
        if not first_update:
            old_stops, _ = Stop.read_stops(ref.rawdata_stops, initial_db)
        response: requests.Response = requests.get(ref.url_ztm_gtfs)
        with open(ref.tmpdata_gtfs, 'wb') as file:
            file.write(response.content)
        with util.zip_file(ref.tmpdata_gtfs, 'r') as zip_ref:
            zip_ref.extract_as('stops.txt', ref.rawdata_stops)
            zip_ref.extract_as('stop_times.txt', ref.rawdata_stop_times)
            zip_ref.extract_as('trips.txt', ref.rawdata_trips)
        os.remove(ref.tmpdata_gtfs)
        attach_stop_routes()
        os.remove(ref.rawdata_stop_times)
        os.remove(ref.rawdata_trips)

        new_stops, _ = Stop.read_stops(ref.rawdata_stops, initial_db)

        added_stops = {s for s in new_stops.values() if s not in old_stops.values()}
        removed_stops = {s for s in old_stops.values() if s not in new_stops.values()}
        if first_update:
            print('Stops database created.')
        else:
            print('Stops database updated.')
            if added_stops:
                print(f'Added stops:\n- {'\n- '.join(f'{s.full_name} [{s.short_name}]' for s in added_stops)}')
            if removed_stops:
                print(f'Removed stops:\n- {'\n- '.join(f'{s.full_name} [{s.short_name}]' for s in removed_stops)}')
            if not added_stops and not removed_stops:
                print('No changes')
    elif not os.path.exists(ref.rawdata_stops):
        raise FileNotFoundError(f'{ref.rawdata_stops} not found. '
                                f'Run the script with the --update flag to download the latest data.')

    if update_map:

        db: Database = load_data(initial_db)

        documented_visited_stops: list[Stop] = list(filter(lambda s: s.visited(include_ev=False), db.stops.values()))
        visible_stops = documented_visited_stops if len(documented_visited_stops) > 0 else db.stops.values()
        avg_lat = (min(float(s.latitude) for s in visible_stops) + max(float(s.latitude) for s in visible_stops)) / 2
        avg_lon = (min(float(s.longitude) for s in visible_stops) + max(float(s.longitude) for s in visible_stops)) / 2
        fmap: folium.Map = folium.Map(location=(avg_lat, avg_lon), zoom_start=12, prefer_canvas=True, zoom_control='bottomleft')

        for stop in db.stops.values():
            stop_visits: list[Visit] = sorted(stop.visits)
            classes: str = ' '.join(
                [f'visited-{visit.name.lower()}' for visit in stop_visits] +
                [f'ever-visited-{visit.name.lower()}' for visit in stop_visits if visit.date == '2000-01-01'] +
                [f'region-{region.short_name}' for region in stop.regions] +
                [f'tp-{player.nickname.lower()}' for _, player, _ in stop.terminals_progress]
            )
            visited_label: str = '<br>'.join(
                [f'visited by {visit.name} {f'on {visit.date}' if visit.date != '2000-01-01' else 'a long time ago'}'
                 for visit in sorted(stop.visits)]) if stop.visits else 'not yet visited'
            terminal_progress_label: str = '<br>'.join([f'{player.nickname}\'s closest {kind} point to {terminal.name} '
                                                        for kind, player, terminal in stop.terminals_progress])
            _, icon, scale, style = stop.marker()
            marker: str = f'<div class="marker {classes}" style="font-size: {scale}em; {style}">{icon}</div>'
            popup: folium.Popup = folium.Popup(f'<span class="stop-name">{stop.full_name} [{stop.short_name}]</span>'
                                               f'<span class="stop-visitors"><br>{visited_label}</span>'
                                               f'<span class="stop-tp"><br>{terminal_progress_label}</span>')
            # noinspection PyTypeChecker
            folium.Marker(location=(stop.latitude, stop.longitude), popup=popup, icon=folium.DivIcon(html=marker)).add_to(fmap)

        def tp_message(tp: TerminalProgress) -> str:
            if tp.completed():
                return f'{tp.player.nickname} has completed this terminal'
            else:
                return f'{tp.player.nickname} has {'arrived at' if tp.arrived() else 'departed from'} this terminal'

        for terminal in db.terminals:
            classes: list[str] = [f'reached-{player.nickname.lower()}' for player in players if terminal.reached_by(player)]
            visited_label: str = '<br>'.join([tp_message(tp) for tp in terminal.progress if tp.reached()]
                                             ) if terminal.anybody_reached() else 'not yet reached'
            marker: str = f'<div class="marker terminal {' '.join(classes)}" style="font-size: 1em;">★</div>'
            popup: folium.Popup = folium.Popup(f'<span class="stop-name">{terminal.name}</span>'
                                               f'<br><span class="stop-tp">{visited_label}</span>')
            # noinspection PyTypeChecker
            folium.Marker(location=(terminal.latitude, terminal.longitude),
                          popup=popup, icon=folium.DivIcon(html=marker)).add_to(fmap)

        build_app(fmap, db)


update_ztm_stops = '--update' in sys.argv or '-u' in sys.argv
update_map = '--map' in sys.argv or '-m' in sys.argv
if __name__ == '__main__':
    main()
