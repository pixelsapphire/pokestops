import ref
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


def create_switch_row(label: str, switch_id: str, onclick: str, label_new: bool = False) -> Tr:
    return Tr(
        [],
        [
            Td([], Div([Class('label-new')] if label_new else [], label)),
            Td(
                [],
                Div(
                    [],
                    Label(
                        [Class('toggle-switch'), Onclick(onclick)],
                        [
                            Input([Id(switch_id), Type('checkbox')]),
                            Span([Class('slider')]),
                        ],
                    ),
                ),
            ),
        ],
    )


def create_control_section(db: Database) -> Div:
    players: list[Player] = db.players
    return Div(
        [Id('control'), Class('hud')],
        [
            Table(
                [],
                Tbody(
                    [],
                    [
                        create_switch_row('Show unvisited', 'visited-switch', 'toggleUnvisited()'),
                        create_switch_row('Show ever visited', 'ev-switch', 'toggleEV()'),
                        create_switch_row('Stellar Voyage', 'sv-switch', 'toggleSV()', label_new=True),
                    ],
                ),
            ),
            Label(
                [Id('player-selection')],
                Select(
                    [Class('dropdown hud'), Onchange('selectPlayer()')],
                    [Option([Value(p.nickname)], p.nickname) for p in players],
                ),
            ),
        ],
    )


def create_region_exploration_section(db: Database) -> (P, Img):
    return (
        P(
            [Id('exploration'), Class('hud')],
            [
                Label(
                    [Id('region-selection')],
                    [
                        Select(
                            [Class('dropdown hud'), Onchange('selectRegion()')],
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
                                *([
                                      CustomHtmlTagAttribute(f'data-{r.short_name.lower()}-{nick.lower()}',
                                                             f'{db.progress[r.short_name][nick]}')
                                      for nick in
                                      [p.nickname for p in db.players] + [f'ev-{p.nickname}' for p in db.players]
                                      for r in sorted(db.regions.values())
                                  ] + [
                                      CustomHtmlTagAttribute(f'data-sv-{p.nickname.lower()}',
                                                             f'{db.progress['SV'][p.nickname]}')
                                      for p in db.players
                                  ]
                                  )
                            ],
                            f'{db.progress[db.district.short_name][db.players[0].nickname]}',
                        ),
                    ],
                ),
            ],
        ),
        Img([Id('compass'), Src(ref.asset_img_compass)])
    )


def create_achievement_row(achievement: AchievementProgress) -> Tr:
    return Tr(
        [],
        [
            Td(
                [Class('achievement-stars')],
                Database.get_stars_for_group(achievement.total) * '★',
            ),
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
                    achievement.completion_date if achievement.completion_date_known()
                    else Span([Class('smaller')], 'a long time ago'),
                ] if achievement.is_completed()
                else f'{achievement.visited}/{achievement.total}'
            )
        ]
    )


def create_achievements_sidebar(db: Database) -> (Div, Button):
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
    model: VehicleModel = vehicle.model
    if model is None:
        print('Vehicle without specified model marked as found:', vehicle.vehicle_id)
        model = VehicleModel('?', 'bus', '?', '?', '?', 0, '')
    return Tr(
        [],
        [
            Td(
                [],
                Img([Class('vehicle-icon'), Src(f'{ref.asset_path_vehicles}/{model.kind}.webp')]),
            ),
            Td(
                [],
                Img([Class('brand-logo'),
                     Src(f'{ref.asset_path_brands}/{model.brand.lower()}.webp')]) if model.brand != '?' else '',
            ),
            Td(
                [],
                [
                    Span([Class('smaller')], model.brand),
                    Br(),
                    Span([Class('smaller' if len(model.model) >= 30 else '')], model.model),
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


def create_vehicle_sidebar(db: Database) -> (Div, Button):
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
                                        create_vehicle_row(discovery.item, discovery.date)
                                        for discovery in player.get_vehicles()
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


def create_application(initial_html: str, db: Database) -> Html:
    return Html(
        [Lang('en')],
        [
            Head(
                [],
                [
                    (initial_html[initial_html.find('<head>') + 6:initial_html.find('</head>')]).strip(),
                    Title([], 'Pokestops'),
                    Link([Rel('stylesheet'), Type('text/css'), Href(ref.url_material_icons)]),
                    Link([Rel('stylesheet'), Type('text/css'), Href(ref.stylesheet_common)]),
                    Link([Rel('stylesheet'), Type('text/css'), Href(ref.stylesheet_map)]),
                    Script([], f'let colors={{\n{",\n".join(f'\'{p.nickname}\':[\'{p.primary_color}\',\'{p.tint_color}\']'
                                                            for p in db.players)}}};'),
                    Script([Src(ref.compileddata_players)]),
                    Script([Src(ref.compileddata_stops)]),
                    Script([Src(ref.controller_map)]),
                ],
            ),
            Body(
                [],
                [
                    (initial_html[initial_html.find('<body>') + 6: initial_html.find('</body>')]).strip(),
                    create_control_section(db),
                    create_region_exploration_section(db),
                    create_achievements_sidebar(db),
                    create_vehicle_sidebar(db),
                    create_archive_button(),
                    Script([Src(ref.compileddata_map)]),
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
                [Class('navigation-tile'), Onclick('openTab(this, "lines")')],
                [
                    Span([Class('material-icon material-symbols-outlined')], 'route'),
                    Span([], ['Lines'])
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


def create_stop_group_view(db: Database, group: str, stop_names: set[str]) -> Div:
    stops: list[Stop] = list(sorted((db.stops[stop] for stop in stop_names), key=lambda s: s.short_name))
    region: Region = db.region_of(db.stops.get(next(iter(stop_names), None)))
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
                            Div([Class('stars')], [Database.get_stars_for_group(len(stops)) * '★']),
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
                            # Img([Class('marker'), Src(f'{ref.asset_path_markers}/{stop.marker()[0]}.svg')]),
                            Div([Class('marker')], stop.marker()),
                            Span([Class('stop-id')], stop.short_name),
                        ],
                    )
                    for stop in stops
                ],
            ),
        ],
    )


def create_stops_page(db: Database) -> Div:
    lexmap: dict[str, float] = util.create_lexicographic_mapping(util.file_to_string(ref.lexmap_polish))
    return Div(
        [Class('content-container selected'), Id('container-stops')],
        [
            Div(
                [Class('content-section'), Id('stops-index')],
                [create_stop_group_view(db, group, stops)
                 for group, stops in sorted(db.stop_groups.items(),
                                            key=lambda group: util.lexicographic_sequence(group[0], lexmap))],
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
                    Div([Id('stop-discoveries'), Class('discoveries-label')]),
                ],
            ),
        ],
    )


def create_line_preview(line: Line) -> Div:
    return Div(
        [Class('line-preview'), CustomHtmlTagAttribute('data-line-number', line.number)],
        [
            Div([Class('line-path-container')], Img([Class('line-path'), Src(f'{ref.mapdata_path}/{line.number}/1.svg')])),
            Div(
                [
                    Class('line-number'),
                    InlineStyle(f'background-color: #{line.background_color}; color: #{line.text_color};'),
                ],
                line.number,
            ),
        ],
    )


def create_lines_page(db: Database) -> Div:
    return Div(
        [Class('content-container'), Id('container-lines')],
        [
            Div(
                [Class('content-section'), Id('lines-index')],
                [create_line_preview(line) for line in sorted(db.lines.values())],
            ),
            Div(
                [Class('content-section object-view'), Id('line-view')],
                [
                    Div(
                        [Class('line-view hidden')],
                        [
                            Span([Id('line-number'), Class('line-number')]),
                            Span([Id('line-terminals'), Class('line-destination')]),
                        ],
                    ),
                    Table(
                        [Id('line-details'), Class('details-table hidden')],
                        [
                            Tr([], [Td([], 'type:'), Td([Id('line-kind')])]),
                            Tr([], [Td([], 'route:'), Td([Id('line-route')])]),
                        ],
                    ),
                    Div([Id('line-routes')]),
                ],
            ),
        ],
    )


def create_vehicle_preview(vehicle: Vehicle) -> Div:
    return Div(
        [Class('vehicle-preview'), CustomHtmlTagAttribute('data-vehicle-id', vehicle.vehicle_id)],
        [
            Img([Class('vehicle-icon'),
                 Src(f'{ref.asset_path_vehicles}/{vehicle.model.kind if vehicle.model else 'bus'}.webp')]),
            Img([Class('vehicle-brand'),
                 Src(f'{ref.asset_path_brands}/{vehicle.model.brand.lower()}.webp')]) if vehicle.model else '',
            Div([Class('vehicle-id')], f'#{vehicle.vehicle_id}'),
        ],
    )


def create_vehicles_page(db: Database) -> Div:
    return Div(
        [Class('content-container'), Id('container-vehicles')],
        [
            Div(
                [Class('content-section'), Id('vehicles-index')],
                [create_vehicle_preview(vehicle) for vehicle in sorted(db.vehicles.values())],
            ),
            Div(
                [Class('content-section object-view'), Id('vehicle-view')],
                [
                    Div([Id('vehicle-name'), Class('name-label')]),
                    Div([Id('vehicle-license-plate')]),
                    Div([Id('vehicle-image')]),
                    Table(
                        [Id('vehicle-details'), Class('details-table hidden')],
                        [
                            Tr([], [Td([], 'carrier:'), Td([Id('vehicle-carrier')])]),
                            Tr([], [Td([], 'type:'), Td([Id('vehicle-kind')])]),
                            Tr([], [Td([], 'brand:'), Td([Id('vehicle-brand')])]),
                            Tr([], [Td([], 'model:'), Td([Id('vehicle-model')])]),
                            Tr([], [Td([], 'seats:'), Td([Id('vehicle-seats')])]),
                        ],
                    ),
                    Div([Id('vehicle-lore'), Class('lore-label')]),
                    Div([Id('vehicle-discoveries'), Class('discoveries-label')]),
                ],
            ),
        ],
    )


def create_archive(db: Database) -> Html:
    return Html(
        [Lang('en')],
        [
            Head(
                [],
                [
                    Title([], 'Pokestops Archive'),
                    Link([Rel('stylesheet'), Type('text/css'), Href(ref.url_material_icons)]),
                    Link([Rel('stylesheet'), Type('text/css'), Href(ref.stylesheet_common)]),
                    Link([Rel('stylesheet'), Type('text/css'), Href(ref.stylesheet_archive)]),
                    Script([Src(ref.compileddata_stops)]),
                    Script([Src(ref.compileddata_vehicles)]),
                    Script([Src(ref.compileddata_lines)]),
                    Script([Src(ref.compileddata_players)]),
                    Script([Src(ref.controller_archive)]),
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
                            create_lines_page(db),
                            create_vehicles_page(db),
                        ],
                    ),
                ],
            ),
        ],
    )
