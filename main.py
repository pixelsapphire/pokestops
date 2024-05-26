import csv
import folium
import os
from typing import Callable
import requests
import zipfile

update_ztm_stops = False
update_map = True


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
        self.region: Region | None = None

    def __hash__(self):
        return hash(self.short_name)

    def __eq__(self, other):
        return self.short_name == other.short_name

    def safe_full_name(self) -> str:
        return strip_diacritics(self.full_name)

    def visited_by(self, name: str) -> str | None:
        return next((visit.date for visit in self.visits if name in visit.name), None)

    def add_visit(self, visit: Visit):
        if self.visited_by(visit.name):
            raise ValueError(f'{visit.name} already visited {self.short_name}, remove the entry from {visit.date}')
        self.visits.add(visit)


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


class Player:
    def __init__(self, nickname: str, save_file: str):
        self.nickname: str = nickname
        self.save_file: str = save_file
        self.__achievements__: Achievements = Achievements()

    def add_stop(self, s: Stop) -> None:
        self.__achievements__.add_stop(s)

    def get_achievements(self) -> list[AchievementProgress]:
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


class Region:
    def __init__(self, number: int, short_name: str, full_name: str, predicate: Callable[[Stop], bool]):
        self.number: int = number
        self.short_name: str = short_name
        self.full_name: str = full_name
        self.predicate: Callable[[Stop], bool] = predicate
        self.stops: set[Stop] = set()

    def add_stop(self, s: Stop) -> None:
        self.stops.add(s)
        s.region = self

    def safe_full_name(self) -> str:
        return strip_diacritics(self.full_name)

    def __contains__(self, item):
        return self.predicate(item)


def stop_in(s: Stop, towns: set[str]) -> bool:
    return '/' in s.full_name and s.full_name[:s.full_name.index('/')] in towns


regions: dict[str, Region] = {r.short_name: r for r in {
    Region(1, 'POZ', 'Poznań', lambda s: s.zone == 'A' or '/' not in s.full_name),
    Region(3, 'SAR', 'San Region', lambda s: stop_in(s, {
        'Annowo', 'Bolechowo', 'Bolechowo-Os.', 'Bolechówko', 'Czerwonak', 'Dębogóra', 'Kicin', 'Kliny', 'Koziegłowy',
        'Mielno', 'Miękowo', 'M. Goślina', 'Owińska', 'Potasze', 'Promnice', 'Przebędowo', 'Szlachęcin', 'Trzaskowo'
    })),
    Region(4, 'YOR', 'Yon Region', lambda s: stop_in(s, {
        'Biskupice', 'Bogucin', 'Bugaj', 'Bylin', 'Gortatowo', 'Gowarzewo', 'Garby Małe', 'Garby Wielkie', 'Gruszczyn',
        'Janikowo', 'Jankowo', 'Jasin', 'Jerzykowo', 'Karłowice', 'Kleszczewo', 'Kobylnica', 'Komorniki gm.Kleszczewo',
        'Krerowo', 'Kruszewnia', 'Krzyżowniki', 'Lipowiec', 'Łowęcin', 'Markowice', 'Nagradowice', 'Paczkowo',
        'Pobiedziska', 'Poklatki', 'Promno', 'Rabowice', 'Sarbinowo', 'Siekierki Wielkie', 'Sokolniki Gwiazdowskie',
        'Swarzędz', 'Szewce', 'Śródka', 'Tanibórz', 'Trzek', 'Tuczno', 'Tulce', 'Uzarzewo', 'Wierzenica', 'Wierzonka',
        'Zalasewo', 'Zimin'
    })),
    Region(5, 'GOR', 'Go Region', lambda s: stop_in(s, {
        'Babki', 'Biernatki', 'Błażejewko', 'Błażejewo', 'Borówiec', 'Czapury', 'Dachowa', 'Daszewice', 'Dziećmierowo',
        'Gądki', 'Jaryszki', 'Jeziory Małe', 'Jeziory Wielkie', 'Kamionki', 'Koninko', 'Kórnik', 'Łękno', 'Prusinowo',
        'Robakowo', 'Skrzynki', 'Szczodrzykowo', 'Szczytniki', 'Świątniczki', 'Wiórek', 'Zaniemyśl', 'Żerniki'
    })),
    Region(6, 'ROR', 'Roku Region', lambda s: stop_in(s, {
        'Luboń', 'Mosina', 'Puszczykowo'
    })),
    Region(7, 'SHR', 'Shichi Region', lambda s: stop_in(s, {
        'Chomęcice', 'Dąbrowa', 'Dąbrówka', 'Dopiewiec', 'Dopiewo', 'Fiałkowo', 'Głuchowo', 'Gołuski', 'Komorniki',
        'Konarzewo', 'Lisówki', 'Łęczyca', 'Palędzie', 'Plewiska', 'Pokrzywnica', 'Rosnowo', 'Rosnówko', 'Skórzewo',
        'Szreniawa', 'Trzcielin', 'Walerianowo', 'Więckowice', 'Wiry', 'Zakrzewo', 'Zborowo'
    })),
    Region(8, 'HAR', 'Hachi Region', lambda s: stop_in(s, {
        'Baranowo', 'Batorowo', 'Brzezno', 'Bytkowo', 'Bytyń', 'Ceradz Dolny', 'Ceradz Kościelny', 'Cerekwica', 'Chyby',
        'Dalekie', 'Gaj Wielki', 'Góra', 'Grzebienisko', 'Jankowice', 'Kaźmierz', 'Kiekrz', 'Kobylniki', 'Kokoszczyn',
        'Krzyszkowo', 'Lusowo', 'Lusówko', 'Młodasko', 'Mrowino', 'Napachanie', 'Otowo', 'Pawłowice', 'Piersko',
        'Pólko', 'Przecław', 'Przeźmierowo', 'Przybroda', 'Rogierówko', 'Rokietnica', 'Rostworowo', 'Rumianek', 'Sady',
        'Sierosław', 'Sobota', 'Starzyny', 'Swadzim', 'Tarnowo Pdg', 'Witkowice', 'Wysogotowo', 'Żydowo'
    })),
    Region(9, 'KYR', 'Kyuu Region', lambda s: stop_in(s, {
        'Biedrusko', 'Chludowo', 'Golęczewo', 'Jelonek', 'Suchy Las', 'Zielątkowo', 'Złotniki', 'Złotkowo'
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
            stops[row[1]] = stop
            if stop.safe_full_name() not in stop_groups:
                stop_groups[stop.safe_full_name()] = set()
            stop_groups[stop.safe_full_name()].add(stop.short_name)
    return stops, stop_groups


players = {
    Player('Zorie', 'caught_zorie.csv'),
    Player('Sapphire', 'caught_sapphire.csv'),
    Player('Camomile', 'caught_camomile.csv'),
}

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

visited_stops: set[Stop] = set()  # this is only needed to determine the center of the map
for player in players:
    with open(player.save_file, 'r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            if not row[0].lstrip().startswith('#'):
                stop = stops.get(row[0])
                if stop:
                    stop.add_visit(Visit(player.nickname, row[1]))
                    visited_stops.add(stop)
                    player.add_stop(stop)
                else:
                    print(f'Stop {row[0]} not found, remove {player.nickname}\'s entry from {row[1]}')
            else:
                if stops.get(row[0].replace('#', '').lstrip()):
                    print(f'Found a commented out {player.nickname}\'s {row[0]} entry, restore it')

if update_map:

    visible_stops = visited_stops if len(visited_stops) > 0 else stops.values()
    avg_lat = (min(float(s.latitude) for s in visible_stops) + max(float(s.latitude) for s in visible_stops)) / 2
    avg_lon = (min(float(s.longitude) for s in visible_stops) + max(float(s.longitude) for s in visible_stops)) / 2
    fmap: folium.Map = folium.Map(location=(avg_lat, avg_lon), zoom_start=12)

    for stop in stops.values():
        classes = ' '.join(
            [f'visited-{visit.name.lower()}' for visit in stop.visits] + [f'region-{stop.region.short_name}'])
        visited_label = '<br>'.join([f'visited by {visit.name} on {visit.date}' for visit in
                                     sorted(stop.visits)]) if stop.visits else 'not yet visited'
        icon = visited_icon_zorie = f'<div class="marker {classes}">●</div>'
        popup = folium.Popup(
            f'<span class="stop-popup stop-name"><b>{stop.safe_full_name()}</b> [{stop.short_name}]</span>'
            f'<br><span class="stop-popup stop-visitors">{visited_label}</span>')
        folium.Marker(location=(stop.latitude, stop.longitude), popup=popup,
                      icon=folium.DivIcon(html=icon)).add_to(fmap)
    fmap.save('index.html')

    with open('index.html', "r") as f:
        html_content = f.read()

    progress: dict[str, dict[str, float]] = {r.short_name: {
        p.nickname: round(len(list(filter(lambda s: s in r and s.visited_by(p.nickname), visited_stops))) /
                          len(list(filter(lambda s: s in r, stops.values()))) * 100, 1) for p in players
    } for r in regions.values()}
    with open('static.html', "r") as f:
        content = f.read()

        content += (
            '<p id="exploration" class="hud-text"><label id="region-selection">'
            '<select class="dropdown hud-text" onchange="selectRegion()">'
            f'{' '.join([f'<option value="{r.short_name}">{r.safe_full_name()}</option>'
                         for r in sorted(regions.values(), key=lambda r: r.number)])}</select></label>'
            f'<br><span id="exploration-progress">Exploration progress: <span id="exploration-percentage" '
            f'{' '.join([f'data-{r.short_name.lower()}-{p.nickname.lower()}={progress[r.short_name][p.nickname]}'
                         for p in players for r in regions.values()])}>'
            f'{progress['POZ']['Zorie']}</span>%</span></p>')

        content += '<div id="achievements">'
        for player in players:
            content += (f'<div class="progress-list" data-player="{player.nickname.lower()}"'
                        f'{'style="display:none;"' if player.nickname != 'Zorie' else ''}>'
                        f'<p class="center">Achievements completed: '
                        f'{len(list(filter(lambda s: s.visited == s.total, player.get_achievements())))}'
                        '</p><table><tbody>')
            for achievement in player.get_achievements():
                content += (
                    f'<tr><td>{achievement.name}<br><p class="achievement-description">{achievement.description}</p></td>'
                    f'<td class="achievement-progress">{f'<span class="smaller">Completed</span><br>{achievement.completed}' if achievement.completed else f'{achievement.visited}/{achievement.total}'}</td>')
            content += '</tbody></table></div>'
        content += '</div><button id="toggle-achievements" onclick="toggleAchievements()"></button>'

        closing_body_index = html_content.rfind("</body>")
        new_content = html_content[:closing_body_index] + content + html_content[closing_body_index:]
        with open('index.html', "w") as f:
            f.write(new_content)
