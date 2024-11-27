import util
from data import *
from htmlBuilder.attributes import *
from htmlBuilder.attributes import Style as InlineStyle
from htmlBuilder.tags import *


class CustomHtmlTagAttribute(HtmlTagAttribute):
    def __init__(self, name: str, value: str | bool | None):
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        super().__init__(value)
        self._name = name


class DataAccessor:
    def __init__(self, players: list[Player], stops: dict[str, Stop], stop_groups: dict[str, set[str]],
                 regions: dict[str, Region], district: Region, progress: dict[str, dict[str, float]],
                 vehicles: dict[str, Vehicle]):
        self.players: list[Player] = players
        self.stops: dict[str, Stop] = stops
        self.stop_groups: dict[str, set[str]] = stop_groups
        self.regions: dict[str, Region] = regions
        self.district: Region = district
        self.progress: dict[str, dict[str, float]] = progress
        self.vehicles: dict[str, Vehicle] = vehicles
        self.__stars__: dict[tuple[int, int], int] = {(1, 1): 1, (2, 2): 2, (3, 4): 3, (5, 7): 4, (8, 100): 5}

    def get_stars_for_group(self, size: int):
        return next((stars for ((min_size, max_size), stars) in self.__stars__.items() if min_size <= size <= max_size), 0)


def create_control_section(db: DataAccessor) -> Div:
    players: list[Player] = db.players
    return Div(
        [Id('control')],
        [
            Div(
                [InlineStyle('display:table-cell;vertical-align:middle;')],
                [
                    Div(
                        [InlineStyle('margin:0;'), Class('hud-text')],
                        'Show unvisited',
                    ),
                    Div(
                        [],
                        Label(
                            [InlineStyle('margin:0;'), Class('toggle-switch'), Onclick('toggleUnvisited()')],
                            [
                                Input([Id('visited-switch'), Type('checkbox')]),
                                Span([Class('slider')]),
                            ],
                        ),
                    ),
                    Div(
                        [InlineStyle('margin:0;'), Class('hud-text')],
                        'Show ever visited',
                    ),
                    Div(
                        [],
                        Label(
                            [InlineStyle('margin:0;'), Class('toggle-switch'), Onclick('toggleEV()')],
                            [
                                Input([Id('ev-switch'), Type('checkbox')]),
                                Span([Class('slider')]),
                            ],
                        ),
                    ),
                ],
            ),
            Label(
                [Id('player-selection')],
                Select(
                    [Class('dropdown hud-text'), Onchange('selectPlayer()')],
                    [Option([Value(p.nickname)], p.nickname) for p in players],
                ),
            ),
        ],
    )


def create_region_exploration_section(db: DataAccessor) -> (P, Img):
    return (
        P(
            [Id('exploration'), Class('hud-text')],
            [
                Label(
                    [Id('region-selection')],
                    [
                        Select(
                            [Class('dropdown hud-text'), Onchange('selectRegion()')],
                            [Option([Value(r.short_name)], r.full_name)
                             for r in sorted(db.regions.values(), key=lambda r: r.number)]
                        ),
                    ],
                ),
                Br(),
                Span(
                    [Id('exploration-progress')],
                    [
                        'Exploration progress: ',
                        Span(
                            [
                                Id('exploration-percentage'),
                                *[
                                    CustomHtmlTagAttribute(f'data-{r.short_name.lower()}-{nick.lower()}',
                                                           f'{db.progress[r.short_name][nick]}')
                                    for nick in
                                    [p.nickname for p in db.players] + [f'ev-{p.nickname}' for p in db.players]
                                    for r in sorted(db.regions.values())
                                ]
                            ],
                            f'{db.progress[db.district.short_name][db.players[0].nickname]}',
                        ),
                        '%',
                    ],
                ),
            ],
        ),
        Img([Id('compass'), Src('assets/compass.png')])
    )


def create_achievement_row(achievement: AchievementProgress) -> Tr:
    return Tr(
        [],
        [
            Td(
                [],
                [
                    achievement.name,
                    Br(),
                    P([Class('achievement-description')], achievement.description),
                ],
            ),
            Td(
                [Class('achievement-progress')],
                [
                    Span([Class('smaller')], 'Completed'),
                    Br(),
                    achievement.completed if achievement.completed != '2000-01-01'
                    else Span([Class('smaller')], 'a long time ago'),
                ] if achievement.completed
                else f'{achievement.visited}/{achievement.total}'
            )
        ]
    )


def create_achievements_sidebar(db: DataAccessor) -> (Div, Button):
    return (
        Div(
            [Class('sidebar'), Id('achievements')],
            [
                Div(
                    [
                        Class('progress-list'),
                        CustomHtmlTagAttribute('data-player', player.nickname.lower()),
                        InlineStyle('display:none;' if player.nickname != db.players[0].nickname else ''),
                    ],
                    [
                        P(
                            [Class('center')],
                            [f'Achievements completed: {player.get_n_achievements(db.stops, db.stop_groups)}'],
                        ),
                        Table(
                            [],
                            [
                                Tbody(
                                    [],
                                    [
                                        create_achievement_row(achievement)
                                        for achievement in player.get_achievements(db.stops, db.stop_groups)
                                    ],
                                ),
                            ],
                        ),
                    ],
                )
                for player in db.players
            ],
        ),
        Button(
            [Class('toggle-sidebar'), Id('toggle-achievements'), Onclick('toggleSidebar("achievements")')],
            [Span([Class('sidebar-button-label')], 'Achievements')],
        ),
    )


def create_vehicle_row(vehicle: Vehicle, date: str) -> Tr:
    return Tr(
        [],
        [
            Td(
                [],
                Img([Class('vehicle-icon'), Src(f'assets/vehicles/{vehicle.model.kind}.webp')]),
            ),
            Td(
                [],
                Img([Class('brand-logo'),
                     Src(f'assets/brands/{vehicle.model.brand.lower()}.webp')]),
            ),
            Td(
                [],
                [
                    Span([Class('smaller')], vehicle.model.brand),
                    Br(),
                    Span([Class('smaller' if len(vehicle.model.model) >= 30 else '')], vehicle.model.model),
                    Br(),
                    Span([Class('larger')], f'#{vehicle.vehicle_id} '),
                    Span([Class('smaller')], f'({vehicle.carrier.short_name})'),
                ],
            ),
            Td(
                [Class('achievement-progress')],
                date,
            ),
        ],
    )


def create_vehicle_sidebar(db: DataAccessor) -> (Div, Button):
    return (
        Div(
            [Class('sidebar'), Id('vehicles')],
            [
                Div(
                    [
                        Class('progress-list'),
                        CustomHtmlTagAttribute('data-player', player.nickname.lower()),
                        InlineStyle('display:none;' if player.nickname != db.players[0].nickname else ''),
                    ],
                    [
                        P([Class('center')], [f'Vehicles discovered: {player.get_n_vehicles()}']),
                        Table(
                            [],
                            [
                                Tbody(
                                    [],
                                    [
                                        create_vehicle_row(vehicle, date)
                                        for vehicle, date in player.get_vehicles()
                                    ],
                                ),
                            ],
                        ),
                    ],
                )
                for player in db.players
            ],
        ),
        Button(
            [Class('toggle-sidebar'), Id('toggle-vehicles'), Onclick('toggleSidebar("vehicles")')],
            [Span([Class('sidebar-button-label')], 'Vehicles')],
        ),
    )


def create_archive_button() -> Button:
    return Button(
        [Class('toggle-sidebar'), Id('open-archive'), Onclick('window.location.href = "archive.html";')],
        [Span([Class('sidebar-button-label')], 'Archive')],
    )


def create_application(initial_html: str, db: DataAccessor) -> Html:
    return Html(
        [Lang('en')],
        [
            Head(
                [],
                [
                    (initial_html[initial_html.find('<head>') + 6:initial_html.find('</head>')]).strip(),
                    Title([], 'Pokestops'),
                    Link([Rel('stylesheet'), Type('text/css'),
                          Href('https://fonts.googleapis.com/css2'
                               '?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0')]),
                    Link([Rel('stylesheet'), Type('text/css'), Href('style_common.css')]),
                    Link([Rel('stylesheet'), Type('text/css'), Href('style_map.css')]),
                    Script([], f'let colors={{\n{",\n".join(f'\'{p.nickname}\':[\'{p.primary_color}\',\'{p.tint_color}\']'
                                                            for p in db.players)}}};'),
                    Script([Src('control_map.js')]),
                ],
            ),
            Body(
                [],
                [
                    (initial_html[initial_html.find('<body>') + 6:initial_html.find('</body>')]).strip(),
                    create_control_section(db),
                    *create_region_exploration_section(db),
                    *create_achievements_sidebar(db),
                    *create_vehicle_sidebar(db),
                    create_archive_button(),
                    Script([Src('data/js/map.min.js')]),
                ],
            ),
        ],
    )


def create_title() -> Div:
    return Div(
        [Id('title-container')],
        [
            Div(
                [
                    Id('back-icon'),
                    Class('material-icon material-symbols-outlined'),
                    Onclick('window.location.href = "index.html";'),
                ],
                'arrow_back_ios'
            ),
            Div([Id('title-icon'), Class('material-icon material-symbols-outlined')], 'auto_stories'),
            Div([Id('title')], 'Pokestops Archive'),
        ],
    )


def create_navigation() -> Div:
    return Div(
        [
            Id('navigation'),
        ],
        [
            Div(
                [Class('navigation-tile selected'), Onclick('openTab(this, "stops")')],
                [
                    Span([Class('material-icon material-symbols-outlined')], 'pin_drop'),
                    Span([], ['Stops'])
                ],
            ),
            Div(
                [Class('navigation-tile'), Onclick('openTab(this, "vehicles")')],
                [
                    Span([Class('material-icon material-symbols-outlined')], 'tram'),
                    Span([], ['Vehicles'])
                ],
            ),
        ],
    )


def create_stop_group_view(db: DataAccessor, group: str, stop_names: set[str]) -> Div:
    stops: list[Stop] = list(sorted((db.stops[stop] for stop in stop_names), key=lambda s: s.short_name))
    region: Region = next(iter(set(db.stops[next(iter(stop_names))].regions) - {db.district}))
    return Div(
        [Class('stop-group-view')],
        [
            Div(
                [Class('stop-header')],
                [
                    Div([Class('roman-numeral')], [util.roman_numeral(region.number)]),
                    Div(
                        [Class('name-and-stars')],
                        [
                            Div([Class('stop-group-name')], group),
                            Div([Class('stars')], [db.get_stars_for_group(len(stops)) * '★']),
                        ],
                    ),
                    Div([Class('expand-icon material-symbols-outlined')], 'add'),
                ],
            ),
            Div(
                [Class('group-stops')],
                [
                    Div(
                        [Class('stop-preview'), CustomHtmlTagAttribute('data-stop-id', stop.short_name)],
                        [
                            Img([Class('marker'), Src(f'assets/markers/{stop.marker()[0]}.svg')]),
                            Span([Class('stop-id')], stop.short_name),
                        ],
                    )
                    for stop in stops
                ],
            ),
        ],
    )


def create_stops_page(db: DataAccessor) -> Div:
    return Div(
        [Class('content-container selected'), Id('container-stops')],
        [
            Div(
                [Class('content-section'), Id('stops-index')],
                [create_stop_group_view(db, group, stops) for group, stops in sorted(db.stop_groups.items())],
            ),
            Div(
                [Class('content-section object-view'), Id('stop-view')],
                [
                    Div([Id('stop-name'), Class('name-label')]),
                    Table(
                        [Id('stop-details'), Class('details-table hidden')],
                        [
                            Tr(
                                [],
                                [
                                    Td([Class('nowrap')], 'served by:'),
                                    Td([Id('stop-lines')]),
                                ],
                            ),
                            Tr(
                                [],
                                [
                                    Td([Class('nowrap')], 'location:'),
                                    Td(
                                        [Id('stop-location')],
                                        [
                                            Span([Id('stop-address')]),
                                            Br(),
                                            Span([Id('stop-coordinates')]),
                                            Br(),
                                            A(
                                                [Id('street-view-link'), Href('#'), Target('_blank')],
                                                [
                                                    Span([], 'view the location'),
                                                    Span([Class('material-icon material-symbols-outlined')],
                                                         'arrow_forward_ios'),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                    Div([Id('street-view-pane'), Class('hidden')]),
                ],
            ),
        ],
    )


def create_vehicle_preview(vehicle: Vehicle) -> Div:
    return Div(
        [Class('vehicle-preview'), CustomHtmlTagAttribute('data-vehicle-id', vehicle.vehicle_id)],
        [
            Img([Class('vehicle-icon'), Src(f'assets/vehicles/{vehicle.model.kind}.webp')]),
            Img([Class('vehicle-brand'), Src(f'assets/brands/{vehicle.model.brand.lower()}.webp')]),
            Div([Class('vehicle-id')], f'#{vehicle.vehicle_id}'),
        ],
    )


def create_vehicles_page(db: DataAccessor) -> Div:
    return Div(
        [
            Class('content-container'),
            Id('container-vehicles'),
        ],
        [
            Div(
                [Class('content-section'), Id('vehicles-index')],
                [create_vehicle_preview(vehicle) for vehicle in sorted(db.vehicles.values())],
            ),
            Div(
                [Class('content-section object-view'), Id('vehicle-view')],
                [
                    Div([Id('vehicle-name'), Class('name-label')]),
                    Table(
                        [Id('vehicle-details'), Class('details-table hidden')],
                        [
                            Tr([], [Td([Class('nowrap')], 'carrier:'), Td([Id('vehicle-carrier')])]),
                            Tr([], [Td([Class('nowrap')], 'type:'), Td([Id('vehicle-kind')])]),
                            Tr([], [Td([Class('nowrap')], 'brand:'), Td([Id('vehicle-brand')])]),
                            Tr([], [Td([Class('nowrap')], 'model:'), Td([Id('vehicle-model')])]),
                            Tr([], [Td([Class('nowrap')], 'seats:'), Td([Id('vehicle-seats')])]),
                        ],
                    ),
                    Div([Id('vehicle-lore'), Class('lore-label')]),
                ],
            ),
        ],
    )


def create_archive(db: DataAccessor) -> Html:
    return Html(
        [Lang('en')],
        [
            Head(
                [],
                [
                    Title([], 'Pokestops Archive'),
                    Link([Rel('stylesheet'), Type('text/css'),
                          Href('https://fonts.googleapis.com/css2'
                               '?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0')]),
                    Link([Rel('stylesheet'), Type('text/css'), Href('style_common.css')]),
                    Link([Rel('stylesheet'), Type('text/css'), Href('style_archive.css')]),
                    Script([Src('data/js/stops_data.min.js')]),
                    Script([Src('data/js/vehicles_data.min.js')]),
                    Script([Src('data/js/players_data.min.js')]),
                    Script([Src('control_archive.js')]),
                ],
            ),
            Body(
                [],
                [
                    create_title(),
                    Div(
                        [Id('container')],
                        [
                            create_navigation(),
                            create_stops_page(db),
                            create_vehicles_page(db),
                        ],
                    ),
                ],
            ),
        ],
    )
