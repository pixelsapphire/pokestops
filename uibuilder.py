from data import *
from htmlBuilder.attributes import *
from htmlBuilder.attributes import Style as InlineStyle
from htmlBuilder.tags import *


class CustomHtmlTagAttribute(HtmlTagAttribute):
    def __init__(self, name: str, value: str):
        super().__init__(value)
        self._name = name


class DataAccessor:
    def __init__(self, players: list[Player], stops: dict[str, Stop], stop_groups: dict[str, set[str]],
                 regions: dict[str, Region], district: Region, progress: dict[str, dict[str, float]]):
        self.players: list[Player] = players
        self.stops: dict[str, Stop] = stops
        self.stop_groups: dict[str, set[str]] = stop_groups
        self.regions: dict[str, Region] = regions
        self.district: Region = district
        self.progress: dict[str, dict[str, float]] = progress


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
                            [InlineStyle('margin:0;'), Class('toggle-switch'),
                             Onclick('toggleUnvisited()')],
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
                                    for r in db.regions.values()
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
            [Class('toggle-sidebar'), Id('toggle-achievements'), Onclick('toggleAchievements()')],
            [Span([Class('sidebar-button-label')], 'Achievements')],
        ),
    )


def create_vehicle_row(vehicle: Vehicle, date: str) -> Tr:
    return Tr(
        [],
        [
            Td(
                [],
                Img([Class('vehicle-icon'), Src(f'assets/vehicles/{vehicle.kind}.webp')]),
            ),
            Td(
                [],
                Img([Class('brand-logo'),
                     Src(f'assets/brands/{vehicle.brand.lower()}.webp')]),
            ),
            Td(
                [],
                [
                    Span([Class('smaller')], vehicle.brand),
                    Br(),
                    Span([Class('smaller' if len(vehicle.model) >= 30 else '')],
                         vehicle.model),
                    Br(),
                    Span([Class('larger')], f'#{vehicle.vehicle_id} '),
                    Span([Class('smaller')], f'({vehicle.carrier.name})'),
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
            [Class('toggle-sidebar'), Id('toggle-vehicles'), Onclick('toggleVehicles()')],
            [Span([Class('sidebar-button-label')], 'Vehicles')],
        ),
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
                    Link([Rel('stylesheet'), Type('text/css'), Href('style.css')]),
                    Script([], f'let colors={{\n{",\n".join(f'\'{p.nickname}\':[\'{p.primary_color}\',\'{p.tint_color}\']'
                                                            for p in db.players)}}};'),
                    Script([Src('control.js')]),
                ],
            ),
            Body(
                [],
                [
                    (initial_html[initial_html.find('<body>') + 6:initial_html.find('</body>')]).strip(),
                    Script([Src('map.min.js')]),
                    create_control_section(db),
                    *create_region_exploration_section(db),
                    *create_achievements_sidebar(db),
                    *create_vehicle_sidebar(db),
                ],
            ),
        ],
    )
