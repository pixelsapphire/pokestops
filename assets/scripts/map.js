let showUnvisitedStops = false;
let showEverVisitedStops = false;
let showUndiscoveredLines = false;
let activePlayer = 'Zorie';
let activeMode = 'pokestops';
let activeRegion = 'POZ';
let activeRaid = '202501';
let darkMode = true;
let raidRouteColor = '#ff61b1';
let raidMarkerColor = '#ba56f6';

const lightModeIcon = 'assets/images/light_mode.png';
const darkModeIcon = 'assets/images/dark_mode.png';

const compiledRearchResultTemplate = nunjucks.compile(searchResultTemplate);
let searchAbortController = null;

function injectThemeSwitcher() {
    let zoomControl = document.querySelector('.leaflet-control-zoom');
    let icon = document.createElement('img');
    icon.id = 'theme-icon';
    icon.src = darkMode ? lightModeIcon : darkModeIcon;
    let themeSwitch = zoomControl.firstChild.cloneNode(true);
    themeSwitch.setAttribute('class', 'leaflet-control-theme');
    themeSwitch.title = 'Toggle theme';
    themeSwitch.setAttribute('aria-label', 'Toggle theme');
    themeSwitch.firstChild.remove();
    themeSwitch.appendChild(icon);
    themeSwitch.addEventListener('click', () => {
        darkMode = !darkMode;
        localStorage.setItem('darkMode', darkMode);
        icon.src = darkMode ? lightModeIcon : darkModeIcon;
        refreshMap();
    });
    zoomControl.insertBefore(themeSwitch, zoomControl.firstChild);
}

function preparePokestops() {

    document.querySelectorAll('path.leaflet-interactive').forEach(l => {
        l.style.display = 'none';
    });

    document.querySelectorAll(`.marker.v-${activePlayer.toLowerCase()}.r-${activeRegion}:not(.ev-${activePlayer.toLowerCase()})`).forEach(m => {
        m.style.color = players[activePlayer].pc;
        m.parentElement.style.display = null;
    });
    const everVisitedMarkers = document.querySelectorAll(`.marker.ev-${activePlayer.toLowerCase()}.r-${activeRegion}`);
    if (showEverVisitedStops)
        everVisitedMarkers.forEach(m => {
            m.style.color = players[activePlayer].tc;
            m.parentElement.style.display = null;
        });
    else
        everVisitedMarkers.forEach(m => {
            m.style.color = 'red';
            m.parentElement.style.display = showUnvisitedStops ? null : 'none';
        });
    document.querySelectorAll(`.marker:not(.v-${activePlayer.toLowerCase()})`).forEach(m => {
        m.style.color = 'red';
        m.parentElement.style.display = showUnvisitedStops ? null : 'none';
    });
    document.querySelectorAll(`.marker:not(.r-${activeRegion})`).forEach(m => {
        m.parentElement.style.display = 'none';
    });
    document.querySelectorAll(`.marker.terminal`).forEach(m => {
        m.parentElement.style.display = 'none';
    });

    document.getElementById('exploration-progress').classList.remove('hidden');
    document.getElementById('raid-info').classList.add('hidden');
    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = `${percentage.getAttribute(`data-${activeRegion.toLowerCase()}-${showEverVisitedStops ? 'ev-' : ''}${activePlayer.toLowerCase()}`)} %`;
}

function preparePokelines() {

    document.querySelectorAll('.marker').forEach(m => m.parentElement.style.display = 'none');
    document.querySelectorAll('path.leaflet-interactive').forEach(l => l.style.display = 'none');
    Array.from(document.querySelectorAll('path.leaflet-interactive')).filter(l => !l.classList.contains('raid')).forEach(l => {
        if (l.classList.contains('disc') || l.classList.contains('compl') || showUndiscoveredLines) l.style.display = null;
        if (l.classList.contains(`d-${activePlayer.toLowerCase()}`)) l.setAttribute('stroke', players[activePlayer].tc);
        else if (l.classList.contains(`c-${activePlayer.toLowerCase()}`)) l.setAttribute('stroke', players[activePlayer].pc);
        else {
            if (showUndiscoveredLines) l.setAttribute('stroke', 'red');
            else l.style.display = 'none';
        }
    });

    document.getElementById('exploration-progress').classList.remove('hidden');
    document.getElementById('raid-info').classList.add('hidden');
    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = `${percentage.getAttribute(`data-lines-${activePlayer.toLowerCase()}`)} %`;
}

function prepareStellarVoyage() {

    document.querySelectorAll('path.leaflet-interactive').forEach(l => l.style.display = 'none');

    document.querySelectorAll(`.marker.terminal`).forEach(m => {
        if (m.classList.contains(`reached-${activePlayer.toLowerCase()}`)) m.style.color = players[activePlayer].pc;
        else m.style.color = 'red';
        m.parentElement.style.display = null;
    });
    document.querySelectorAll(`.marker.tp-${activePlayer.toLowerCase()}`).forEach(m => {
        m.parentElement.style.display = null;
        if (m.classList.contains(`v-${activePlayer.toLowerCase()}`)) m.style.color = players[activePlayer].tc;
        else m.style.color = 'red';
    });
    document.querySelectorAll(`.marker:not(.terminal):not(.tp-${activePlayer.toLowerCase()})`).forEach(m => {
        m.parentElement.style.display = 'none';
    });

    document.getElementById('exploration-progress').classList.remove('hidden');
    document.getElementById('raid-info').classList.add('hidden');
    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = `${percentage.getAttribute(`data-sv-${activePlayer.toLowerCase()}`)} %`;
}

function prepareCityRaiders() {

    document.querySelectorAll('path.leaflet-interactive').forEach(l => {
        if (l.classList.contains('raid') && l.classList.contains(`r-${activeRaid}`)) {
            l.style.display = null;
            l.setAttribute('stroke', raidRouteColor);
        } else l.style.display = 'none';
    });
    document.querySelectorAll('.marker').forEach(m => {
        if (m.classList.contains('raid') && m.classList.contains(`r-${activeRaid}`)) {
            m.parentElement.style.display = null;
            m.style.color = raidMarkerColor;
        } else m.parentElement.style.display = 'none';
    });

    document.getElementById('exploration-progress').classList.add('hidden');
    document.getElementById('raid-info').classList.remove('hidden');
    const length = document.getElementById('raid-length');
    length.innerHTML = `${length.getAttribute(`data-length-${activeRaid}`)}`;
}

function refreshMap() {

    document.body.classList.toggle('stellar-voyage', activeMode === 'stellar-voyage');

    document.querySelectorAll('.hud-controls').forEach(hud => {
        if (hud.id === `controls-${activeMode}`) hud.classList.remove('hidden');
        else hud.classList.add('hidden');
    });
    document.getElementById('region-selection').classList.toggle('hidden', activeMode !== 'pokestops');
    if (activeMode === 'pokestops') preparePokestops();
    else if (activeMode === 'pokelines') preparePokelines();
    else if (activeMode === 'stellar-voyage') prepareStellarVoyage();
    else if (activeMode === 'city-raiders') prepareCityRaiders();

    document.querySelectorAll('.progress-list')
        .forEach(list => list.style.display = list.getAttribute('data-player') === activePlayer.toLowerCase() ? null : 'none');

    document.querySelectorAll('.leaflet-layer,.leaflet-control-zoom-in,.leaflet-control-zoom-out,.leaflet-control-attribution,.leaflet-control-theme')
        .forEach(e => e.style.filter = darkMode ? 'invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%)' : null);
    // document.querySelectorAll('.folium-map,.marker,.sidebar,.toggle-sidebar').forEach(e => e.classList.toggle('dark', darkMode));
    document.body.classList.toggle('dark', darkMode);
}

function toggleUnvisited() {
    showUnvisitedStops = document.querySelector("#visited-switch").checked;
    refreshMap();
}

function toggleEV() {
    showEverVisitedStops = document.querySelector("#ev-switch").checked;
    refreshMap();
}

function toggleUndiscovered() {
    showUndiscoveredLines = document.querySelector("#discovered-switch").checked;
    refreshMap();
}

function selectPlayer() {
    activePlayer = document.querySelector("#player-selection select").value;
    localStorage.setItem('activePlayer', activePlayer);
    refreshMap();
}

function selectMode() {
    activeMode = document.querySelector("#mode-selection select").value;
    localStorage.setItem('activeMode', activeMode);
    refreshMap();
}

function selectRaid() {
    activeRaid = document.querySelector("#raid-selection select").value;
    localStorage.setItem('activeRaid', activeRaid);
    refreshMap();
}

function selectRegion() {
    activeRegion = document.querySelector("#region-selection select").value;
    localStorage.setItem('activeRegion', activeRegion);
    refreshMap();
}

function toggleSidebar(sidebar) {
    document.querySelector(`#${sidebar}`).classList.toggle('expanded');
}

Array.prototype.any = function (predicate) {
    return this.filter(predicate).length > 0;
};
Array.prototype.all = function (predicate) {
    return this.filter(predicate).length === this.length;
}

async function searchObject() {

    if (searchAbortController) searchAbortController.abort();
    searchAbortController = new AbortController();
    const {signal} = searchAbortController;

    let searchQuery = document.querySelector('#search-input').value.toLowerCase();
    let resultsView = document.getElementById('search-results');
    resultsView.innerHTML = '';
    if (searchQuery.length === 0) return;

    let resultsEqualTo = [];
    let resultsStartingWith = [];
    let resultsContaining = [];
    let resultsContainingDetail = [];
    const searchDictionary = (dictionary, type, unlockedGetter, searchKeyExtractor, searchDetailExtractor = null) => {
        for (let key in dictionary) {
            const searchKeys = searchKeyExtractor(key);
            const details = searchDetailExtractor ? searchDetailExtractor(key) : '';
            const unlocked = unlockedGetter(key) === true;
            let resultsList = null;
            if (searchKeys.any((k) => k.toLowerCase() === searchQuery)) resultsList = resultsEqualTo;
            else if (searchKeys.any((k) => k.toLowerCase().startsWith(searchQuery))) resultsList = resultsStartingWith;
            else if (searchKeys.any((k) => k.toLowerCase().includes(searchQuery))) resultsList = resultsContaining;
            else if (searchDetailExtractor && details.toLowerCase().includes(searchQuery)) resultsList = resultsContainingDetail;
            if (resultsList) resultsList.push({
                type: type,
                key: key,
                object: dictionary[key],
                details: details,
                unlocked: unlocked
            });
        }
    };
    searchDictionary(stops, 'stop', (key) => stops[key].v && stops[key].v.any((v) => v[0] === activePlayer),
        (key) => [key, stops[key].n]);
    searchDictionary(lines, 'line', (key) => lines[key].d && lines[key].d.any((d) => d[0] === activePlayer),
        (key) => [key], (key) => lines[key].t);
    searchDictionary(vehicles, 'vehicle', (key) => vehicles[key].d && vehicles[key].d.any((d) => d[0] === activePlayer),
        (key) => [key].concat(key.includes('+') ? key.split('+') : []), (key) => {
            if (!vehicles[key].m) return '';
            const model = vehicle_models[vehicles[key].m];
            return `${model.b} ${model.m}`;
        });

    if ([resultsEqualTo, resultsStartingWith, resultsContaining, resultsContainingDetail].all((r) => r.length === 0)) {
        resultsView.innerHTML = '<div class="list-title center">No results found</div>';
        return;
    }
    resultsView.innerHTML = '';

    const postResult = (result) => resultsView.innerHTML += compiledRearchResultTemplate.render({result: result});
    const allResults = [...resultsEqualTo, ...resultsStartingWith, ...resultsContaining, ...resultsContainingDetail];
    for (let i = 0; i < allResults.length; i++) {
        if (signal.aborted) return;
        postResult(allResults[i]);
        await new Promise(resolve => setTimeout(resolve, 0));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    activePlayer = localStorage.getItem('activePlayer') || activePlayer;
    document.querySelector("#player-selection select").value = activePlayer;
    activeRegion = localStorage.getItem('activeRegion') || activeRegion;
    document.querySelector("#region-selection select").value = activeRegion;
    darkMode = localStorage.getItem('darkMode') !== 'false';
    injectThemeSwitcher();
    activeMode = localStorage.getItem('activeMode') || activeMode;
    document.querySelector("#mode-selection select").value = activeMode;
    refreshMap();
});
