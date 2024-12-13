import requests
import sqlite3
from data import *
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
    with zip_file(ref.tmpdata_gtfs, 'r') as zip_ref:
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
        Database.make_update_report(old_db, initial_db)
