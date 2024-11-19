import csv
import folium
import os
from typing import Callable
import requests
import sys
import zipfile

update_ztm_stops = '--update' in sys.argv or '-u' in sys.argv
update_map = '--map' in sys.argv or '-m' in sys.argv


class Visit:
    def __init__(self, name: str, date: str):
        self.name: str = name
        self.date: str = date

    def __hash__(self):
        return hash(self.name) + hash(self.date)

    def __lt__(self, other):
        return self.date < other.date if self.date != other.date else self.name > other.name


def strip_diacritics(s: str) -> str:
    return (s
            .replace('ą', 'a').replace('Ą', 'A').replace('ć', 'c').replace('Ć', 'C')
            .replace('ę', 'e').replace('Ę', 'E').replace('ł', 'l').replace('Ł', 'L')
            .replace('ń', 'n').replace('Ń', 'N').replace('ó', 'o').replace('Ó', 'O')
            .replace('ś', 's').replace('Ś', 'S').replace('ź', 'z').replace('Ź', 'Z')
            .replace('ż', 'z').replace('Ż', 'Z').replace('ō', 'o').replace('Ō', 'O'))


class Stop:
    def __init__(self, short_name: str, full_name: str, latitude: str, longitude: str, zone: str):
        self.short_name: str = short_name
        self.full_name: str = full_name
        self.latitude: float = float(latitude)
        self.longitude: float = float(longitude)
        self.zone: str = zone
        self.visits: set[Visit] = set()
        self.regions: list[Region] = []

    def __hash__(self):
        return hash(self.short_name)

    def __eq__(self, other):
        return self.short_name == other.short_name

    def safe_full_name(self) -> str:
        return strip_diacritics(self.full_name)

    def in_one_of(self, towns: set[str]) -> bool:
        return '/' in self.full_name and self.full_name[:self.full_name.index('/')] in towns

    def visited_by(self, name: str, include_ev: bool = True) -> str | None:
        return next((visit.date for visit in self.visits
                     if name == visit.name and (visit.date != '2000-01-01' or include_ev)), None)

    def add_visit(self, visit: Visit):
        if self.visited_by(visit.name):
            raise ValueError(f'{visit.name} already visited {self.short_name}, '
                             f'remove the entry from {visit.date if visit.date != '2000-01-01' else 'her EV file'}')
        self.visits.add(visit)

    def marker(self) -> tuple[str, float, str | None]:
        number = int(self.short_name[-2:])
        if 0 < number < 20:
            return '●', 1.1, None
        elif 20 < number < 40:
            return '★', 1, None
        elif 40 < number < 70:
            return '■', 0.9, 'transform: rotate(45deg);'
        elif 70 < number < 90:
            return '■', 0.9, None
        else:
            return '▲', 0.8, None


class AchievementProgress:
    def __init__(self, name: str, visited: int, total: int, completed: str | None = None):
        self.name: str = name
        self.description: str = 'Collect all of the following: '
        self.visited: int = visited
        self.total: int = total
        self.completed: str | None = completed

    def percentage(self) -> int:
        return int(round(self.visited / self.total * 100))


class Achievements:
    def __init__(self):
        self.stop_groups: dict[str, set[Stop]] = {}

    def add_stop(self, s: Stop) -> None:
        if s.safe_full_name() not in self.stop_groups:
            self.stop_groups[s.safe_full_name()] = set()
        self.stop_groups[s.safe_full_name()].add(s)


class Vehicle:
    def __init__(self, vehicle_id: str, kind: str, brand: str, model: str):
        self.vehicle_id: str = vehicle_id
        self.kind: str = kind
        self.brand: str = brand
        self.model: str = model

    def __hash__(self):
        return hash(self.vehicle_id)

    def __eq__(self, other):
        return self.vehicle_id == other.vehicle_id


class Player:
    def __init__(self, nickname: str, stops_file: str, ev_file: str, vehicles_file: str):
        self.nickname: str = nickname
        self.stops_file: str = stops_file
        self.ev_file: str = ev_file
        self.vehicles_file: str = vehicles_file
        self.__achievements__: Achievements = Achievements()
        self.__vehicles__: list[(Vehicle, str)] = []

    def add_stop(self, s: Stop) -> None:
        self.__achievements__.add_stop(s)

    def add_vehicle(self, v: Vehicle, date: str) -> None:
        self.__vehicles__.append((v, date))

    def get_achievements(self, stops: dict[str, Stop], stop_groups: dict[str, set[str]]) -> list[AchievementProgress]:
        prog = []
        for group in self.__achievements__.stop_groups:
            visited = len(self.__achievements__.stop_groups[group])
            total = len(stop_groups[group])
            if visited == total:
                date = max(s.visited_by(self.nickname) for s in self.__achievements__.stop_groups[group])
                prog.append(AchievementProgress(group, visited, total, date))
            else:
                prog.append(AchievementProgress(group, visited, total))
            prog[-1].description += ', '.join(
                sorted(s.short_name for s in stops.values() if s.safe_full_name() == group))
        return sorted(prog, key=lambda p: (p.percentage(), p.completed), reverse=True)

    @staticmethod
    def init_file(path: str, initial_content: str = '') -> None:
        if not os.path.exists(path):
            with open(path, 'x') as new_file:
                new_file.write(initial_content)

    def init_files(self) -> None:
        self.init_file(self.stops_file, 'stop_id,date_visited\n')
        self.init_file(self.ev_file)
        self.init_file(self.vehicles_file, 'vehicle_id,date_discovered\n')


class Region:
    def __init__(self, number: int, short_name: str, full_name: str, predicate: Callable[[Stop], bool]):
        self.number: int = number
        self.short_name: str = short_name
        self.full_name: str = full_name
        self.predicate: Callable[[Stop], bool] = predicate
        self.stops: set[Stop] = set()

    def add_stop(self, s: Stop) -> None:
        self.stops.add(s)
        s.regions.append(self)

    def safe_full_name(self) -> str:
        return strip_diacritics(self.full_name)

    def __contains__(self, item):
        return self.predicate(item)


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


def read_stops() -> (dict[str, Stop], dict[str, set[str]]):
    stops: dict[str, Stop] = {}
    stop_groups: dict[str, set[str]] = {}
    with open('stops.csv', 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            stop = Stop(row[1], row[2], row[3], row[4], row[5])
            region = next((r for r in regions.values() if stop in r), None)
            if not region:
                raise ValueError(f'Stop {stop.full_name} [{stop.short_name}] not in any region')
            region.add_stop(stop)
            district.add_stop(stop)
            stops[row[1]] = stop
            if stop.safe_full_name() not in stop_groups:
                stop_groups[stop.safe_full_name()] = set()
            stop_groups[stop.safe_full_name()].add(stop.short_name)
    return stops, stop_groups


def read_vehicles() -> dict[str, Vehicle]:
    vehicles: dict[str, Vehicle] = {}
    with open('vehicles.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            vehicles[row[0]] = Vehicle(*row)
    return vehicles


def main() -> None:
    players: list[Player] = []
    with open('players.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            players.append(Player(*row))

    old_stops = {}
    first_update = not os.path.exists('stops.csv')
    if update_ztm_stops:
        if not first_update:
            old_stops, _ = read_stops()
        response: requests.Response = requests.get('https://www.ztm.poznan.pl/pl/dla-deweloperow/getGTFSFile')
        with open('gtfs.zip', 'wb') as file:
            file.write(response.content)
        with zipfile.ZipFile('gtfs.zip', 'r') as zip_ref:
            zip_ref.extract('stops.txt')
            os.rename('stops.txt', 'stops.csv')
        os.remove('gtfs.zip')
    elif not os.path.exists('stops.csv'):
        raise FileNotFoundError('stops.csv not found. Run the script with update_ztm_stops set to True')

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

    vehicles: dict[str, Vehicle] = read_vehicles()

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
                        combined: str | None = next(v for v in vehicles.keys()
                                                    if v.startswith(f'{vehicle_id}+') or v.endswith(f'+{vehicle_id}'))
                        if combined:
                            print(f'Vehicle #{vehicle_id} not found, but there is vehicle #{combined},'
                                  f' modify {player.nickname}\'s entry in her vehicles file')
                        else:
                            print(f'Vehicle #{vehicle_id} not found, remove {player.nickname}\'s entry from her vehicles file')
                else:
                    vehicle_id = row[0].replace('#', '').lstrip()
                    if vehicles.get(vehicle_id):
                        print(f'Found a commented out {player.nickname}\'s {vehicle_id} vehicles file entry, restore it')

    if update_map:

        visible_stops = documented_visited_stops if len(documented_visited_stops) > 0 else stops.values()
        avg_lat = (min(float(s.latitude) for s in visible_stops) + max(float(s.latitude) for s in visible_stops)) / 2
        avg_lon = (min(float(s.longitude) for s in visible_stops) + max(float(s.longitude) for s in visible_stops)) / 2
        fmap: folium.Map = folium.Map(location=(avg_lat, avg_lon), zoom_start=12)

        for stop in stops.values():
            classes = ' '.join(
                [f'visited-{visit.name.lower()}' for visit in stop.visits] +
                [f'ever-visited-{visit.name.lower()}' for visit in stop.visits if visit.date == '2000-01-01'] +
                [f'region-{region.short_name}' for region in stop.regions])
            visited_label = '<br>'.join(
                [f'visited by {visit.name} {f'on {visit.date}' if visit.date != '2000-01-01' else 'a long time ago'}'
                 for visit in sorted(stop.visits)]) if stop.visits else 'not yet visited'
            icon, scale, style = stop.marker()
            marker = f'<div class="marker {classes}" style="font-size: {scale}em; {style}">{icon}</div>'
            popup = folium.Popup(
                f'<span class="stop-popup stop-name"><b>{stop.safe_full_name()}</b> [{stop.short_name}]</span>'
                f'<br><span class="stop-popup stop-visitors">{visited_label}</span>')
            folium.Marker(location=(stop.latitude, stop.longitude), popup=popup,
                          icon=folium.DivIcon(html=marker)).add_to(fmap)
        fmap.save('index.html')

        with open('index.html', "r") as f:
            html_content = f.read()

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
        with open('static.html', "r") as static:
            content = static.read()

            content += (
                '<p id="exploration" class="hud-text"><label id="region-selection">'
                '<select class="dropdown hud-text" onchange="selectRegion()">'
                f'{' '.join([f'<option value="{r.short_name}">{r.safe_full_name()}</option>'
                             for r in sorted(regions.values(), key=lambda r: r.number)])}</select></label>'
                f'<br><span id="exploration-progress">Exploration progress: <span id="exploration-percentage" '
                f'{' '.join([f'data-{r.short_name.lower()}-{nick.lower()}={progress[r.short_name][nick]}'
                             for nick in [p.nickname for p in players] + [f'ev-{p.nickname}' for p in players]
                             for r in regions.values()])}>'
                f'{progress['POZ']['Zorie']}</span>%</span></p>')

            content += '<div class="sidebar" id="achievements">'
            for player in players:
                content += (f'<div class="progress-list" data-player="{player.nickname.lower()}"'
                            f'{'style="display:none;"' if player.nickname != 'Zorie' else ''}>'
                            f'<p class="center">Achievements completed: '
                            f'{len(list(filter(lambda s: s.visited == s.total, player.get_achievements(stops, stop_groups))))}'
                            '</p><table><tbody>')
                for achievement in player.get_achievements(stops, stop_groups):
                    time = achievement.completed if achievement.completed != '2000-01-01' \
                        else '<span class="smaller">a long time ago</span>'
                    achievement_progress = f'<span class="smaller">Completed</span><br>{time}' \
                        if achievement.completed else f'{achievement.visited}/{achievement.total}'
                    content += (f'<tr><td>{achievement.name}<br>'
                                f'<p class="achievement-description">{achievement.description}</p></td>'
                                f'<td class="achievement-progress">{achievement_progress}</td>')
                content += '</tbody></table></div>'
            content += ('</div><button class="toggle-sidebar" id="toggle-achievements" onclick="toggleAchievements()">'
                        '<span class="sidebar-button-label">Achievements</span></button>')

            content += '<div class="sidebar" id="vehicles">'
            for player in players:
                content += (f'<div class="progress-list" data-player="{player.nickname.lower()}"'
                            f'{'style="display:none;"' if player.nickname != 'Zorie' else ''}>'
                            f'<p class="center">Vehicles discovered: {len(player.__vehicles__)}</p><table><tbody>')
                for vehicle, date in player.__vehicles__:
                    content += (f'<tr><td><img class="vehicle-icon" src="assets/vehicles/{vehicle.kind}.webp"></img></td>'
                                f'<td><img class="brand-logo" src="assets/brands/{vehicle.brand.lower()}.webp"></img></td>'
                                f'<td><span class="smaller">{vehicle.brand}</span><br>{vehicle.model}<br>'
                                f'<span class="larger"><b>#{vehicle.vehicle_id}</b></span></td>'
                                f'<td class="achievement-progress">{date}</td>')
                content += '</tbody></table></div>'
            content += ('</div><button class="toggle-sidebar" id="toggle-vehicles" onclick="toggleVehicles()">'
                        '<span class="sidebar-button-label">Vehicles</span></button>')

            closing_body_index = html_content.rfind("</body>")
            new_content = html_content[:closing_body_index] + content + html_content[closing_body_index:]

            closing_head_index = new_content.rfind("</head>")
            title = '<title>Pokestops</title>'
            new_content = new_content[:closing_head_index] + title + new_content[closing_head_index:]

            with open('index.html', "w") as output:
                output.write(new_content)


if __name__ == '__main__':
    main()
