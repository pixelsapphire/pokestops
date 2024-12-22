let showUnvisitedStops = false;
let showEverVisitedStops = false;
let showUndiscoveredLines = false;
let activePlayer = 'Zorie';
let activeMode = 'pokestops';
let activeRegion = 'POZ';
let darkMode = true;

const lightModeIcon = 'assets/images/light_mode.png';
const darkModeIcon = 'assets/images/dark_mode.png';

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

    document.getElementById('region-selection').style.display = null;
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

    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = `${percentage.getAttribute(`data-${activeRegion.toLowerCase()}-${showEverVisitedStops ? 'ev-' : ''}${activePlayer.toLowerCase()}`)} %`;
}

function preparePokelines() {

    document.getElementById('region-selection').style.display = 'none';
    document.querySelectorAll('.marker').forEach(m => {
        m.parentElement.style.display = 'none';
    });
    document.querySelectorAll('path.leaflet-interactive').forEach(l => {
        if (l.classList.contains('disc') || l.classList.contains('compl') || showUndiscoveredLines) l.style.display = null;
        if (l.classList.contains(`d-${activePlayer.toLowerCase()}`)) l.setAttribute('stroke', players[activePlayer].tc);
        else if (l.classList.contains(`c-${activePlayer.toLowerCase()}`)) l.setAttribute('stroke', players[activePlayer].pc);
        else {
            if (showUndiscoveredLines) l.setAttribute('stroke', 'red');
            else l.style.display = 'none';
        }
    });

    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = `${percentage.getAttribute(`data-lines-${activePlayer.toLowerCase()}`)} %`;
}

function prepareStellarVoyage() {

    document.getElementById('region-selection').style.display = 'none';
    document.querySelectorAll('path.leaflet-interactive').forEach(l => {
        l.style.display = 'none';
    });

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

    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = `${percentage.getAttribute(`data-sv-${activePlayer.toLowerCase()}`)} %`;
}

function refreshMap() {

    document.body.classList.toggle('stellar-voyage', activeMode === 'stellar-voyage');

    document.querySelectorAll('.hud-controls').forEach(hud => {
        if (hud.id === `controls-${activeMode}`) hud.style.display = null;
        else hud.style.display = 'none';
    });
    if (activeMode === 'pokestops') preparePokestops();
    else if (activeMode === 'pokelines') preparePokelines();
    else if (activeMode === 'stellar-voyage') prepareStellarVoyage();

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

function selectRegion() {
    activeRegion = document.querySelector("#region-selection select").value;
    localStorage.setItem('activeRegion', activeRegion);
    refreshMap();
}

function toggleSidebar(sidebar) {
    document.querySelector(`#${sidebar}`).classList.toggle('expanded');
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
