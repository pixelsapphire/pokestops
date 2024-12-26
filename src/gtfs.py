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


def attach_line_routes(gtfs_db: sqlite3.Connection) -> None:
    print('    Attaching route ids to lines... ', end='')
    cursor: sqlite3.Cursor = gtfs_db.cursor()
    cursor.execute('WITH Filtered AS (SELECT route_id, shape_id FROM trips WHERE trip_id LIKE \'%+\'),'
                   '     Fallback AS (SELECT route_id, shape_id FROM trips) '
                   'SELECT * FROM Filtered '
                   'WHERE route_id IN (SELECT DISTINCT route_id FROM Filtered) GROUP BY shape_id, route_id '
                   'UNION ALL '
                   'SELECT * FROM Fallback '
                   'WHERE route_id NOT IN (SELECT DISTINCT route_id FROM Filtered) GROUP BY shape_id, route_id ;')
    line_routes: dict[str, list[str]] = defaultdict(list)
    for line_id, shape_id in cursor.fetchall():
        line_routes[line_id].append(shape_id)
    cursor.close()

    lines_header_row: list[str]
    lines_data: list[list[str]]
    with open(ref.rawdata_lines, 'r') as file:
        reader = csv.reader(file)
        lines_header_row = next(reader)
        lines_data = list(reader)

    with open(prepare_path(ref.rawdata_lines), 'w') as file:
        writer = csv.writer(file)
        writer.writerow([*lines_header_row, 'routes'])
        for line in lines_data:
            writer.writerow([*line, '&'.join(line_routes[line[0]])])

    print('Done!')


def attach_line_stops(gtfs_db: sqlite3.Connection) -> None:
    print('    Attaching stop codes to lines... ', end='')
    cursor: sqlite3.Cursor = gtfs_db.cursor()
    cursor.execute('WITH Filtered AS (SELECT route_id, trip_id, shape_id, stop_code, stop_sequence '
                   '                  FROM trips JOIN stop_times USING (trip_id) JOIN stops USING (stop_id) '
                   '                  WHERE trip_id LIKE \'%+\'),'
                   '     Fallback AS (SELECT route_id, trip_id, shape_id, stop_code, stop_sequence '
                   '                  FROM trips JOIN stop_times USING (trip_id) JOIN stops USING (stop_id)) '
                   'SELECT * FROM (SELECT route_id, trip_id, stop_code, stop_sequence FROM Filtered '
                   'WHERE route_id IN (SELECT DISTINCT route_id FROM Filtered) '
                   'GROUP BY route_id, trip_id, shape_id, stop_sequence '
                   'UNION ALL '
                   'SELECT route_id, trip_id, stop_code, stop_sequence FROM Fallback '
                   'WHERE route_id NOT IN (SELECT DISTINCT route_id FROM Filtered) '
                   'GROUP BY route_id, trip_id, shape_id, stop_sequence) '
                   'ORDER BY CAST(route_id AS INTEGER), trip_id, CAST(stop_sequence AS INTEGER)')
    line_stops: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for record in cursor.fetchall():
        line_id, trip_id, stop_code, _ = record
        line_stops[line_id][trip_id].append(stop_code)
    cursor.close()

    line_stops_unique: dict[str, list[list[str]]] = defaultdict(list)
    for line_id, trips in line_stops.items():
        for trip_id, trip_stops in trips.items():
            if ((trip_id.startswith('1_') or not any(filter(lambda t: t.startswith('1_'), line_stops[line_id].keys())))
                    and trip_stops not in line_stops_unique[line_id]):
                line_stops_unique[line_id].append(trip_stops)

    lines_header_row: list[str]
    lines_data: list[list[str]]
    with open(ref.rawdata_lines, 'r') as file:
        reader = csv.reader(file)
        lines_header_row = next(reader)
        lines_data = list(reader)

    with open(prepare_path(ref.rawdata_lines), 'w') as file:
        writer = csv.writer(file)
        writer.writerow([*lines_header_row, 'stops'])
        for line in lines_data:
            writer.writerow([*line, '|'.join(map(lambda stops: '&'.join(stops), line_stops_unique[line[0]]))])

    print('Done!')


def update_gtfs_data(first_update: bool, initial_db: Database) -> None:
    old_db: Database = Database.partial()
    if not first_update:
        if os.path.exists(ref.rawdata_stops):
            old_db.stops = Stop.read_stops(ref.rawdata_stops, initial_db)[0]
        if os.path.exists(ref.rawdata_lines):
            old_db.lines = Line.read_dict(ref.rawdata_lines)
    print(f'  Downloading latest GTFS data from {ref.url_ztm_gtfs}... ', end='')
    os.system('wget --header="Accept: application/octet-stream" '
              f'"{ref.url_ztm_gtfs}" -O "{ref.tmpdata_gtfs}" > /dev/null 2>&1')
    print('Done!')
    print('  Extracting GTFS data... ', end='')
    with zip_file(ref.tmpdata_gtfs, 'r') as gtfs_zip:
        gtfs_zip.extract_as('stops.txt', ref.rawdata_stops)
        gtfs_zip.extract_as('stop_times.txt', ref.rawdata_stop_times)
        gtfs_zip.extract_as('trips.txt', ref.rawdata_trips)
        gtfs_zip.extract_as('shapes.txt', ref.rawdata_routes)
        gtfs_zip.extract_as('routes.txt', ref.rawdata_lines)
    os.remove(ref.tmpdata_gtfs)
    print('Done!')
    print('  Processing GTFS data... ')
    gtfs_db: sqlite3.Connection = create_gtfs_database()
    attach_stop_lines(gtfs_db)
    attach_line_routes(gtfs_db)
    attach_line_stops(gtfs_db)
    os.remove(ref.rawdata_stop_times)
    os.remove(ref.rawdata_trips)

    initial_db.stops, initial_db.stop_groups = Stop.read_stops(ref.rawdata_stops, initial_db)
    initial_db.routes = Route.read_dict(ref.rawdata_routes)
    initial_db.lines = Line.read_dict(ref.rawdata_lines)

    if first_update:
        print('  GTFS database created.', end='')
    else:
        print('  GTFS database updated.', end='')
        Database.make_update_report(old_db, initial_db)
