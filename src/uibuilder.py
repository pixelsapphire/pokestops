import os.path
import util
from branca.element import MacroElement
from data import *
from folium import DivIcon, Map, Marker, PolyLine, Popup
from geo import LineSegment
from markupsafe import Markup
from jinja2 import Environment, FileSystemLoader, Template
from typing import Sequence


class JinjaLoader(FileSystemLoader):
    def __init__(self):
        super().__init__('templates')

    def get_source(self, environment: Environment, template_id: str) -> tuple[str, str, Callable]:
        template_path: str = template_id.replace('.', '/')
        template_path += '/_root.jinja' if os.path.isdir(f'templates/{template_path}') else '.jinja'
        return super().get_source(environment, template_path)


class UIBuilder(Environment):
    def __init__(self, database: Database, lexmap_file: str):
        super().__init__(loader=JinjaLoader())
        self.__lexmap__: dict[str, float] = util.create_lexicographic_mapping(util.file_to_string(lexmap_file))
        self.__database__: Database = database
        self.filters['lexicographic_sort'] = self.__lexicographic_sort__
        self.globals.update(db=database)
        self.globals.update(ref=ref)
        self.globals.update(util=util)
        self.globals.update(include_file=self.__include_file__)

    def __lexicographic_sort__[T](self, sequence: list[T], attribute: str | int | None = None) -> list[T]:
        return sorted(sequence, key=lambda item: util.lexicographic_sequence(self.getitem(item, attribute), self.__lexmap__))

    def __include_file__(self, file: str) -> Markup:
        return Markup(self.loader.get_source(self, file)[0])

    def build_fmap(self) -> Map:
        documented_visited_stops: list[Stop] = [s for s in self.__database__.stops.values() if s.is_visited(include_ev=False)]
        visible_stops: Iterable[Stop] = documented_visited_stops or self.__database__.stops.values()
        lat = (min(s.location.latitude for s in visible_stops) + max(s.location.latitude for s in visible_stops)) / 2
        lon = (min(s.location.longitude for s in visible_stops) + max(s.location.longitude for s in visible_stops)) / 2
        fmap: Map = Map(location=[lat, lon], zoom_start=12, prefer_canvas=False, zoom_control='bottomleft')
        log('    Drawing features... ', end='')
        [marker.add_to(fmap) for marker in self.make_stop_markers()]
        [line.add_to(fmap) for line in self.make_line_paths()]
        [marker.add_to(fmap) for marker in self.make_terminal_markers()]
        [element.add_to(fmap) for element in self.place_raid_markers()]
        log('Done!')
        return fmap

    def make_stop_markers(self) -> Iterable[Marker]:
        icon_template: Template = self.get_template('map.features.icons.stop')
        popup_template: Template = self.get_template('map.features.popups.stop')
        for stop in self.__database__.stops.values():
            yield Marker(
                location=stop.location,
                popup=Popup(popup_template.render(stop=stop).replace('\n', '')),
                icon=DivIcon(html=icon_template.render(stop=stop).replace('\n', ''), icon_anchor=(12, 16))
            )

    def make_line_paths(self) -> Iterable[PolyLine]:
        paths: list[PolyLine] = []
        already_drawn: set[tuple[LineSegment[geopoint], HashableSet[str]]] = set()

        def draw_line(pts: Sequence[geopoint], cls: HashableSet[str]) -> None:
            if isinstance(pts, LineSegment) and (pts, cls) in already_drawn:
                return
            already_drawn.add((pts, cls)) if isinstance(pts, LineSegment) else None
            paths.append(PolyLine(locations=[pts], class_name=' '.join(cls),
                                  fill_opacity=0, weight=3, bubbling_mouse_events=False))

        for line in [line for line in self.__database__.lines.values() if not line.is_discovered()]:
            for route in line.routes:
                draw_line(self.__database__.routes[route].points, HashableSet(('undiscovered',)))

        segments_and_players: dict[LineSegment[geopoint], set[Player]] = defaultdict(set)
        for line in [line for line in self.__database__.lines.values() if line.is_discovered()]:
            for route in line.routes:
                points: list[geopoint] = self.__database__.routes[route].points
                for i in range(len(points) - 1):
                    segments_and_players[LineSegment(points[i], points[i + 1])] |= {p for p in self.__database__.players
                                                                                    if line.discovered_by(p)}
        for segment, players in segments_and_players.items():
            draw_line(segment, HashableSet(['disc'] + [f'd-{player.nickname.lower()}' for player in players]))

        segments_and_lines: dict[LineSegment[geopoint], set[Line]] = defaultdict(set)
        for line in self.__database__.lines.values():
            for route in line.routes:
                points: list[geopoint] = self.__database__.routes[route].points
                for i in range(len(points) - 1):
                    segments_and_lines[LineSegment(points[i], points[i + 1])].add(line)
        for segment, lines in segments_and_lines.items():
            players_who_completed: list[Player] = [p for p in self.__database__.players
                                                   if all(ln.discovered_by(p) for ln in lines)]
            if len(players_who_completed) > 0:
                draw_line(segment, HashableSet(['compl'] + [f'c-{player.nickname.lower()}'
                                                            for player in players_who_completed]))

        return paths

    def make_terminal_markers(self) -> Iterable[Marker]:
        icon_template: Template = self.get_template('map.features.icons.terminal')
        popup_template: Template = self.get_template('map.features.popups.terminal')
        for terminal in self.__database__.terminals:
            yield Marker(
                location=(terminal.latitude, terminal.longitude),
                popup=Popup(popup_template.render(terminal=terminal).replace('\n', '')),
                icon=DivIcon(html=icon_template.render(terminal=terminal).replace('\n', ''), icon_anchor=(12, 16))
            )

    def place_raid_markers(self) -> Iterable[MacroElement]:
        icon_template: Template = self.get_template('map.features.icons.raid_point')
        popup_template: Template = self.get_template('map.features.popups.raid_point')

        def draw_point(point: PointRaidElement, raid_id: str) -> Marker:
            return Marker(
                location=point.location,
                popup=Popup(popup_template.render(point=point, raid_id=raid_id).replace('\n', '')),
                icon=DivIcon(html=icon_template.render(point=point, raid_id=raid_id).replace('\n', ''), icon_anchor=(12, 16))
            )

        def draw_route(route: RouteRaidElement, raid_id: str) -> PolyLine:
            return PolyLine(locations=[route.shape], class_name=f'raid r-{raid_id}',
                            fill_opacity=0, weight=3, bubbling_mouse_events=False)

        for raid in self.__database__.raids:
            for element in raid.elements:
                if isinstance(element, PointRaidElement):
                    yield draw_point(element, raid.raid_id)
                elif isinstance(element, RouteRaidElement):
                    yield draw_route(element, raid.raid_id)
                else:
                    raise ValueError(f'Unknown raid element type: {element}')

    def create_map(self, initial_html: str) -> Template:
        folium_head: str = re.search(r'<head>(.*)</head>', initial_html, re.DOTALL).group(1).strip()
        folium_body: str = re.search(r'<body>(.*)</body>', initial_html, re.DOTALL).group(1).strip()
        map_template: Template = self.get_template('map')
        map_template.globals.update(folium_head=folium_head, folium_body=folium_body)
        return map_template

    def create_archive(self) -> Template:
        return self.get_template('archive')

    def create_announcements(self) -> Template:
        return self.get_template('announcements')
