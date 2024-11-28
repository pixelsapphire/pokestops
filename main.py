import csv
import folium
import requests
import sqlite3
import sys
from postprocess import *
from uibuilder import *

district = Region(0, 'PZD', 'Poznań', lambda s: True)
regions: dict[str, Region] = {r.short_name: r for r in {
    Region(1, 'POZ', 'Poznań City', lambda s: s.zone == 'A' or '/' not in s.full_name),
    Region(3, 'SAR', 'San Region', lambda s: s.in_one_of({
        'Annowo', 'Biedrusko', 'Bolechowo', 'Bolechowo-Os.', 'Bolechówko', 'Czerwonak', 'Dębogóra', 'Karłowice',
        'Kicin', 'Kliny', 'Koziegłowy', 'Mielno', 'Miękowo', 'M. Goślina', 'Owińska', 'Potasze', 'Promnice',
        'Przebędowo', 'Szlachęcin', 'Trzaskowo', 'Tuczno', 'Wierzonka'
    })),
    Region(4, 'YOR', 'Yon Region', lambda s: s.in_one_of({
        'Biskupice', 'Bogucin', 'Bugaj', 'Bylin', 'Gortatowo', 'Gowarzewo', 'Garby Małe', 'Garby Wielkie', 'Gruszczyn',
        'Janikowo', 'Jankowo', 'Jasin', 'Jerzykowo', 'Kleszczewo', 'Kobylnica', 'Komorniki gm.Kleszczewo',
        'Krerowo', 'Kruszewnia', 'Krzyżowniki', 'Lipowiec', 'Łowęcin', 'Markowice', 'Nagradowice', 'Paczkowo',
        'Pobiedziska', 'Poklatki', 'Promno', 'Rabowice', 'Sarbinowo', 'Siekierki Wielkie', 'Sokolniki Gwiazdowskie',
        'Swarzędz', 'Szewce', 'Śródka', 'Tanibórz', 'Trzek', 'Tulce', 'Uzarzewo', 'Wierzenica', 'Zalasewo', 'Zimin'
    })),
    Region(5, 'GOR', 'Go Region', lambda s: s.in_one_of({
        'Babki', 'Biernatki', 'Błażejewko', 'Błażejewo', 'Borówiec', 'Czapury', 'Dachowa', 'Daszewice', 'Dziećmierowo',
        'Gądki', 'Jaryszki', 'Jeziory Małe', 'Jeziory Wielkie', 'Kamionki', 'Koninko', 'Kórnik', 'Łękno', 'Prusinowo',
        'Robakowo', 'Skrzynki', 'Szczodrzykowo', 'Szczytniki', 'Świątniczki', 'Wiórek', 'Zaniemyśl', 'Żerniki'
    })),
    Region(6, 'ROR', 'Roku Region', lambda s: s.in_one_of({
        'Luboń', 'Łęczyca', 'Mosina', 'Puszczykowo'
    })),
    Region(7, 'SHR', 'Shichi Region', lambda s: s.in_one_of({
        'Chomęcice', 'Dąbrowa', 'Dąbrówka', 'Dopiewiec', 'Dopiewo', 'Fiałkowo', 'Głuchowo', 'Gołuski', 'Komorniki',
        'Konarzewo', 'Lisówki', 'Palędzie', 'Plewiska', 'Pokrzywnica', 'Rosnowo', 'Rosnówko', 'Skórzewo', 'Szreniawa',
        'Trzcielin', 'Walerianowo', 'Więckowice', 'Wiry', 'Zakrzewo', 'Zborowo'
    })),
    Region(8, 'HAR', 'Hachi Region', lambda s: s.in_one_of({
        'Baranowo', 'Batorowo', 'Brzezno', 'Bytkowo', 'Bytyń', 'Ceradz Dolny', 'Ceradz Kościelny', 'Cerekwica', 'Chyby',
        'Dalekie', 'Gaj Wielki', 'Góra', 'Grzebienisko', 'Jankowice', 'Kaźmierz', 'Kiekrz', 'Kobylniki', 'Kokoszczyn',
        'Krzyszkowo', 'Lusowo', 'Lusówko', 'Młodasko', 'Mrowino', 'Napachanie', 'Otowo', 'Pawłowice', 'Piersko',
        'Pólko', 'Przecław', 'Przeźmierowo', 'Przybroda', 'Rogierówko', 'Rokietnica', 'Rostworowo', 'Rumianek', 'Sady',
        'Sierosław', 'Sobota', 'Starzyny', 'Swadzim', 'Tarnowo Pdg', 'Witkowice', 'Wysogotowo', 'Żydowo'
    })),
    Region(9, 'KYR', 'Kyuu Region', lambda s: s.in_one_of({
        'Chludowo', 'Golęczewo', 'Jelonek', 'Suchy Las', 'Zielątkowo', 'Złotniki', 'Złotkowo'
    })),
}}


def read_stops() -> tuple[dict[str, Stop], dict[str, set[str]]]:
    stops: dict[str, Stop] = {}
    stop_groups: dict[str, set[str]] = {}
    with open('data/csv/stops.csv', 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            stop = Stop(row[1], row[2], row[3], row[4], row[5], row[6])
            region = next((r for r in regions.values() if stop in r), None)
            if not region:
                raise ValueError(f'Stop {stop.full_name} [{stop.short_name}] not in any region')
            region.add_stop(stop)
            district.add_stop(stop)
            stops[row[1]] = stop
            if stop.full_name not in stop_groups:
                stop_groups[stop.full_name] = set()
            stop_groups[stop.full_name].add(stop.short_name)
    return stops, stop_groups


def read_carriers() -> dict[str, Carrier]:
    with open('data/csv/carriers.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        return {row[0]: Carrier(*row)
                for row in reader if row and not row[0].lstrip().startswith('#')}


def read_models() -> dict[str, VehicleModel]:
    with open('data/csv/vehicle_models.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        return {row[0]: VehicleModel(*row)
                for row in reader if row and not row[0].lstrip().startswith('#')}


def read_vehicles(carriers: dict[str, Carrier], models: dict[str, VehicleModel]) -> dict[str, Vehicle]:
    with open('data/csv/vehicles.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        return {row[0]: Vehicle(row[0], carriers.get(row[1]), models.get(row[2]), row[3], row[4])
                for row in reader if row and not row[0].lstrip().startswith('#')}


def attach_stop_routes() -> None:
    gtfs_db: sqlite3.Connection = sqlite3.connect(':memory:')

    with open('data/csv/stops.csv', 'r') as file:
        reader = csv.reader(file)
        header_row = next(reader)
        stops_header_row = header_row
        gtfs_db.execute(f'CREATE TABLE stops ({", ".join(f'{col} TEXT' for col in header_row)})')
        gtfs_db.executemany(f'INSERT INTO stops VALUES ({','.join('?' * len(header_row))})', reader)

    with open('stop_times.csv', 'r') as file:
        reader = csv.reader(file)
        header_row = next(reader)
        gtfs_db.execute(f'CREATE TABLE stop_times ({", ".join(f'{col} TEXT' for col in header_row)})')
        gtfs_db.executemany(f'INSERT INTO stop_times VALUES ({','.join('?' * len(header_row))})', reader)

    with open('trips.csv', 'r') as file:
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

    with open('data/csv/stops.csv', 'w') as file:
        writer = csv.writer(file)
        writer.writerow([*stops_header_row, 'routes'])
        writer.writerows(cursor.fetchall())


def make_stop_entry(stop: Stop) -> str:
    return (f'"{stop.short_name}":{{'
            f'n:"{stop.full_name}",'
            f'lt:{stop.latitude},'
            f'ln:{stop.longitude},'
            f'l:[{','.join(f'[{line},"{destination}"]' for line, destination in stop.lines)}]'
            f'}},')


def make_vehicle_model_entry(model: VehicleModel) -> str:
    return (f'"{model.model_id}":{{'
            f'k:"{model.kind_detailed}",'
            f'b:"{model.brand}",'
            f'm:"{model.model}",'
            f'{f's:{model.seats},' if model.seats else ''}'
            f'l:"{model.lore}",'
            f'}},')


def make_carrier_entry(carrier: Carrier) -> str:
    return (f'"{carrier.symbol}":{{'
            f'n:"{carrier.full_name}",'
            f'}},')


def make_vehicle_entry(vehicle: Vehicle) -> str:
    return (f'"{vehicle.vehicle_id}":{{'
            f'm:"{vehicle.model.model_id}",'
            f'c:"{vehicle.carrier.symbol}",'
            f'{f'i:{f'"{vehicle.image_url}"'},' if vehicle.image_url else ''}'
            f'l:"{vehicle.lore}",'
            f'}},')


def make_player_entry(player: Player, stops: dict[str, Stop]) -> str:
    return (f'"{player.nickname}":{{'
            f'v:[{','.join(sorted(f'"{v[0].vehicle_id}"' for v in player.get_vehicles()))}],'
            f's:[{','.join(sorted(f'"{s.short_name}"' for s in stops.values() if s.visited_by(player.nickname)))}],'
            f'}},')


def main() -> None:
    players: list[Player] = []
    with open('data/csv/players.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            players.append(Player(*row))

    old_stops = {}
    first_update = not os.path.exists('data/csv/stops.csv')
    if update_ztm_stops:
        if not first_update:
            old_stops, _ = read_stops()
        response: requests.Response = requests.get('https://www.ztm.poznan.pl/pl/dla-deweloperow/getGTFSFile')
        with open('data/gtfs.zip', 'wb') as file:
            file.write(response.content)
        with util.zip_file('data/gtfs.zip', 'r') as zip_ref:
            zip_ref.extract_as('stops.txt', 'data/csv/stops.csv')
            zip_ref.extract_as('stop_times.txt', 'data/csv/stop_times.csv')
            zip_ref.extract_as('trips.txt', 'data/csv/trips.csv')
        os.remove('data/gtfs.zip')
        attach_stop_routes()
        os.remove('data/csv/stop_times.csv')
        os.remove('data/csv/trips.csv')
    elif not os.path.exists('data/csv/stops.csv'):
        raise FileNotFoundError('stops.csv not found. Run the script with the --update flag to download the latest data.')

    stops, stop_groups = read_stops()

    if update_ztm_stops:
        added_stops = {s for s in stops.values() if s not in old_stops.values()}
        removed_stops = {s for s in old_stops.values() if s not in stops.values()}
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

    carriers: dict[str, Carrier] = read_carriers()
    models: dict[str, VehicleModel] = read_models()
    vehicles: dict[str, Vehicle] = read_vehicles(carriers, models)

    ever_visited_stops: set[Stop] = set()
    documented_visited_stops: set[Stop] = set()

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
                        ever_visited_stops.add(stop)
                        documented_visited_stops.add(stop)
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
                        ever_visited_stops.add(stop)
                        player.add_stop(stop)
                    else:
                        print(f'Stop {stop_id} not found, remove {player.nickname}\'s entry from her EV file')
                else:
                    stop_id = stop_id.replace('#', '').lstrip()
                    if stops.get(stop_id):
                        print(f'Found a commented out {player.nickname}\'s {stop_id} EV file entry, restore it')
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

    if update_map:

        regions[district.short_name] = district
        progress: dict[str, dict[str, float]] = {r.short_name: {
            **{
                p.nickname: round(len(list(filter(lambda s: s in r and s.visited_by(p.nickname, False), ever_visited_stops))) /
                                  len(list(filter(lambda s: s in r, stops.values()))) * 100, 1) for p in players
            },
            **{
                f'ev-{p.nickname}': round(len(list(filter(lambda s: s in r and s.visited_by(p.nickname), ever_visited_stops))) /
                                          len(list(filter(lambda s: s in r, stops.values()))) * 100, 1) for p in players
            },
        } for r in regions.values()}

        visible_stops = documented_visited_stops if len(documented_visited_stops) > 0 else stops.values()
        avg_lat = (min(float(s.latitude) for s in visible_stops) + max(float(s.latitude) for s in visible_stops)) / 2
        avg_lon = (min(float(s.longitude) for s in visible_stops) + max(float(s.longitude) for s in visible_stops)) / 2
        fmap: folium.Map = folium.Map(location=(avg_lat, avg_lon), zoom_start=12, prefer_canvas=True, zoom_control='bottomleft')

        for stop in stops.values():
            stop_visits = sorted(stop.visits)
            classes = ' '.join(
                [f'visited-{visit.name.lower()}' for visit in stop_visits] +
                [f'ever-visited-{visit.name.lower()}' for visit in stop_visits if visit.date == '2000-01-01'] +
                [f'region-{region.short_name}' for region in stop.regions])
            visited_label = '<br>'.join(
                [f'visited by {visit.name} {f'on {visit.date}' if visit.date != '2000-01-01' else 'a long time ago'}'
                 for visit in sorted(stop.visits)]) if stop.visits else 'not yet visited'
            _, icon, scale, style = stop.marker()
            marker = f'<div class="marker {classes}" style="font-size: {scale}em; {style}">{icon}</div>'
            popup = folium.Popup(f'<span class="stop-name">{stop.full_name} [{stop.short_name}]</span>'
                                 f'<br><span class="stop-visitors">{visited_label}</span>')
            # noinspection PyTypeChecker
            folium.Marker(location=(stop.latitude, stop.longitude), popup=popup, icon=folium.DivIcon(html=marker)).add_to(fmap)

        folium_html: str = fmap.get_root().render()
        map_script: str = folium_html[folium_html.rfind('<script>') + 8:folium_html.rfind('</script>')]
        with open('data/js/map.min.js', 'w') as script_file:
            script_file.write(clean_js(map_script))

        accessor: DataAccessor = DataAccessor(players, stops, stop_groups, regions, district, progress, vehicles)
        html_application: Html = create_application(folium_html, accessor)
        rendered_application: str = clean_html(html_application.render(True, True))
        with open('index.html', 'w') as file:
            file.write(rendered_application)

        with open('data/js/stops_data.min.js', 'w') as file:
            file.write(f'const stops = {{\n{'\n'.join(map(make_stop_entry, stops.values()))}\n}};')

        with open('data/js/vehicles_data.min.js', 'w') as file:
            file.write(f'const vehicle_models = {{\n{'\n'.join(map(make_vehicle_model_entry, models.values()))}\n}};\n')
            file.write(f'const carriers = {{\n{'\n'.join(map(make_carrier_entry, carriers.values()))}\n}};\n')
            file.write(f'const vehicles = {{\n{'\n'.join(map(make_vehicle_entry, vehicles.values()))}\n}};')

        with open('data/js/players_data.min.js', 'w') as file:
            file.write(f'const players = {{\n{'\n'.join(map(lambda p: make_player_entry(p, stops), players))}\n}};')

        html_archive: Html = create_archive(accessor)
        rendered_archive: str = clean_html(html_archive.render(True, True))
        with open('archive.html', 'w') as file:
            file.write(rendered_archive)


update_ztm_stops = '--update' in sys.argv or '-u' in sys.argv
update_map = '--map' in sys.argv or '-m' in sys.argv
if __name__ == '__main__':
    main()
    # extract_stop_routes()
