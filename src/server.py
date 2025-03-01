from announcements import fetch_announcements
from database import *
from flask import Flask, request
from flask.wrappers import Response
from folium import Map
from gtfs import update_gtfs_data
from log import flush_errors, log
from typing import Any, Callable, Iterable, MutableMapping
from uibuilder import UIBuilder
from waitress import serve
import postprocess
import ref
import util


class Server:
    def __init__(self, host: str = '127.0.0.1', port: int = 39610):
        self.app: Flask = Flask(__name__)
        self.host: str = host
        self.port: int = port
        self.database: Database = load_database()
        self.ui_builder: UIBuilder = UIBuilder(database=self.database, lexmap_file=ref.lexmap_polish)
        self._setup_routes()

    @staticmethod
    def as_json(data: Any, mapper: Callable[[Any], dict[str, Any]] | None = None) -> Response:
        if mapper is not None:
            if isinstance(data, MutableMapping):
                return Server.as_json({key: mapper(value) for key, value in data.items()})
            elif isinstance(data, Iterable):
                return Server.as_json(list(map(mapper, data)))
            else:
                return Server.as_json(mapper(data))
        return Response(status=200, mimetype='application/json', response=json.dumps(data))

    def _setup_routes(self) -> None:

        def _post_command(*commands: Callable[[], None]) -> Response:
            success: bool = True
            error_message: str = ''
            try:
                for command in commands:
                    command()
            except Exception as e:
                success = False
                error_message = str(e)
            return Server.as_json({'success': success, 'error_message': error_message, 'errors': flush_errors()})

        @self.app.route('/info/status', methods=['GET'])
        def get_info_status() -> str:
            return 'online'

        @self.app.route('/info/players', methods=['GET'])
        def get_info_players() -> Response:
            json_mapper: Callable[[Player], dict[str, Any]] = lambda p: {'nickname': p.nickname, 'color': p.primary_color}
            return Server.as_json(self.database.players, mapper=json_mapper)

        @self.app.route('/info/last_update/gtfs', methods=['GET'])
        def get_info_last_update_gtfs() -> str:
            lines_last_update: datetime | None = util.file_last_modified(ref.rawdata_lines)
            routes_last_update: datetime | None = util.file_last_modified(ref.rawdata_routes)
            stops_last_update: datetime | None = util.file_last_modified(ref.rawdata_stops)
            if lines_last_update is None or routes_last_update is None or stops_last_update is None:
                return 'never'
            return min(lines_last_update, routes_last_update, stops_last_update).replace(microsecond=0).isoformat()

        @self.app.route('/info/last_update/announcements', methods=['GET'])
        def get_info_last_update_announcements() -> str:
            announcements_last_update: datetime | None = util.file_last_modified(ref.rawdata_announcements)
            if announcements_last_update is None:
                return 'never'
            return announcements_last_update.replace(microsecond=0).isoformat()

        @self.app.route('/update/gtfs', methods=['POST'])
        def post_update_gtfs() -> Response:
            response: Response = _post_command(self.update_gtfs_and_draw_lines)
            self.database.make_update_report()
            return response

        @self.app.route('/update/announcements', methods=['POST'])
        def post_update_announcements() -> Response:
            response: Response = _post_command(lambda: fetch_announcements(self.database))
            self.database.make_update_report()
            return response

        @self.app.route('/update/all', methods=['POST'])
        def post_update_all() -> Response:
            response: Response = _post_command(self.update_gtfs_and_draw_lines, lambda: fetch_announcements(self.database))
            self.database.make_update_report()
            return response

        @self.app.route('/compile/map', methods=['POST'])
        def post_compile_map() -> Response:
            return _post_command(self.ui_builder.compile_data, self.compile_map)

        @self.app.route('/compile/archive', methods=['POST'])
        def post_compile_archive() -> Response:
            return _post_command(self.ui_builder.compile_data, self.compile_archive)

        @self.app.route('/compile/announcements', methods=['POST'])
        def post_compile_announcements() -> Response:
            return _post_command(self.ui_builder.compile_data, self.compile_announcements)

        @self.app.route('/compile/raids', methods=['POST'])
        def post_compile_raids() -> Response:
            return _post_command(self.compile_raids)

        @self.app.route('/compile/all', methods=['POST'])
        def post_compile_all() -> Response:
            return _post_command(self.ui_builder.compile_data, self.compile_map, self.compile_archive,
                                 self.compile_announcements, self.compile_raids)

        def _reload_database() -> None:
            self.database = load_database()

        @self.app.route('/reload', methods=['POST'])
        def post_reload() -> Response:
            return _post_command(_reload_database)

        @self.app.route('/domain/stops', methods=['GET'])
        def get_domain_stops() -> Response:
            json_mapper: Callable[[Stop], dict[str, Any]] = lambda s: \
                {'short_name': s.short_name, 'full_name': s.full_name, 'zone': s.zone}
            return Server.as_json(self.database.stops, mapper=json_mapper)

        @self.app.route('/domain/carriers', methods=['GET'])
        def get_domain_carriers() -> Response:
            json_mapper: Callable[[Carrier], dict[str, Any]] = lambda c: \
                {'symbol': c.symbol, 'name': c.short_name, 'colors': c.colors}
            return Server.as_json(self.database.carriers, mapper=json_mapper)

        @self.app.route('/domain/vehicles', methods=['GET'])
        def get_domain_vehicles() -> Response:
            json_mapper: Callable[[Vehicle], dict[str, Any]] = \
                lambda v: {'vehicle_id': v.vehicle_id, 'carrier': v.carrier.symbol, 'type': v.model.kind,
                           'brand': v.model.brand, 'model': v.model.model
                           } if v.model else {'vehicle_id': v.vehicle_id, 'carrier': v.carrier.symbol}
            return Server.as_json(self.database.vehicles, mapper=json_mapper)

        @self.app.route('/domain/lines', methods=['GET'])
        def get_domain_lines() -> Response:
            json_mapper: Callable[[Stop], dict[str, Any]] = lambda l: \
                {'number': l.number, 'terminals': l.terminals, 'description': l.description,
                 'zones': l.get_zones(self.database.stops)}
            return Server.as_json(self.database.lines, mapper=json_mapper)

        def _get_playerdata(nickname: str, collection: Callable[[Player], dict[str, Any]],
                            mapper: Callable[[Discovery[Any]], dict[str, Any]]) -> Response:
            player: Player = find_first(lambda p: p.nickname == nickname, self.database.players)
            return Server.as_json(collection(player), mapper=mapper)

        def _get_playerdata_stops(nickname: str, ev: Literal['exclude', 'only']) -> Response:
            json_mapper: Callable[[Discovery[Stop]], dict[str, Any]] = lambda d: \
                {'date': d.date.format('y-m-d'), 'item': d.item.short_name}
            return _get_playerdata(nickname, lambda p: p.logbook.get_stops(ev=ev), json_mapper)

        @self.app.route('/playerdata/stops', methods=['GET'])
        def get_playerdata_stops() -> Response:
            return _get_playerdata_stops(request.args.get('player'), ev='exclude')

        @self.app.route('/playerdata/ev_stops', methods=['GET'])
        def get_playerdata_ev_stops() -> Response:
            return _get_playerdata_stops(request.args.get('player'), ev='only')

        @self.app.route('/playerdata/vehicles', methods=['GET'])
        def get_playerdata_vehicles() -> Response:
            json_mapper: Callable[[Discovery[Vehicle]], dict[str, Any]] = lambda d: \
                {'date': d.date.format('y-m-d'), 'item': d.item.vehicle_id}
            return _get_playerdata(request.args.get('player'), lambda p: p.logbook.get_vehicles(), json_mapper)

        @self.app.route('/playerdata/lines', methods=['GET'])
        def get_playerdata_lines() -> Response:
            json_mapper: Callable[[Discovery[Line]], dict[str, Any]] = lambda d: \
                {'date': d.date.format('y-m-d'), 'item': d.item.number}
            return _get_playerdata(request.args.get('player'), lambda p: p.logbook.get_lines(), json_mapper)

    def compile_map(self) -> None:
        log('  Building Folium map...')
        fmap: Map = self.ui_builder.build_fmap()
        log('    Compiling... ', end='')
        folium_html = fmap.get_root().render()
        map_script: str = folium_html[folium_html.rfind('<script>') + 8:folium_html.rfind('</script>')]
        with open(util.prepare_path(ref.compileddata_map), 'w') as script_file:
            script_file.write(postprocess.clean_js(map_script))
        log('Done!')

        log('  Building map HTML document... ', end='')
        map_html: str = postprocess.clean_html(self.ui_builder.create_map(folium_html).render())
        with open(util.prepare_path(ref.document_map), 'w') as file:
            file.write(map_html)
        log('Done!')

    def compile_archive(self) -> None:
        log('  Building archive HTML document... ', end='')
        archive_html: str = postprocess.clean_html(self.ui_builder.create_archive().render())
        with open(util.prepare_path(ref.document_archive), 'w') as file:
            file.write(archive_html)
        log('Done!')

    def compile_announcements(self) -> None:
        log('  Building announcements HTML document... ', end='')
        announcements_html: str = postprocess.clean_html(self.ui_builder.create_announcements().render())
        with open(util.prepare_path(ref.document_announcements), 'w') as file:
            file.write(announcements_html)
        log('Done!')

    def compile_raids(self) -> None:
        log('  Building raids HTML document... ', end='')
        self.ui_builder.create_raid_maps()
        raids_html: str = postprocess.clean_html(self.ui_builder.create_raids().render())
        with open(util.prepare_path(ref.document_raids), 'w') as file:
            file.write(raids_html)
        log('Done!')

    def update_gtfs_and_draw_lines(self) -> None:
        update_gtfs_data(self.database)
        log('Drawing line route diagrams... ', end='')
        util.clear_directory(util.prepare_path(ref.mapdata_paths_lines, path_is_directory=True))
        self.ui_builder.create_line_maps(False)
        log('Done!')

    def run(self) -> None:
        print(f'Server started at {self.host}:{self.port}/')
        serve(self.app, host=self.host, port=self.port)
