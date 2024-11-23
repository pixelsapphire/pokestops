let showUnvisited = false;
let showEverVisited = false;
let activePlayer = 'Zorie';
let activeRegion = 'POZ';
let darkMode = true;

const primary = 0;
const tint = 1;

function injectThemeSwitcher() {
    let zoomControl = document.querySelector('.leaflet-control-zoom');
    let icon = document.createElement('img');
    icon.id = 'theme-icon';
    icon.src = darkMode ? 'assets/light_mode.png' : 'assets/dark_mode.png';
    let themeSwitch = zoomControl.firstChild.cloneNode(true);
    themeSwitch.setAttribute('class', 'leaflet-control-theme');
    themeSwitch.title = 'Toggle theme';
    themeSwitch.setAttribute('aria-label', 'Toggle theme');
    themeSwitch.firstChild.remove();
    themeSwitch.appendChild(icon);
    themeSwitch.addEventListener('click', () => {
        darkMode = !darkMode;
        localStorage.setItem('darkMode', darkMode);
        icon.src = darkMode ? 'assets/light_mode.png' : 'assets/dark_mode.png';
        refreshMap();
    });
    zoomControl.insertBefore(themeSwitch, zoomControl.firstChild);
}

function refreshMap() {

    document.querySelectorAll(`.marker.visited-${activePlayer.toLowerCase()}.region-${activeRegion}:not(.ever-visited-${activePlayer.toLowerCase()})`).forEach(m => {
        m.style.color = colors[activePlayer][primary];
        m.parentElement.style.display = null;
    });
    const everVisitedMarkers = document.querySelectorAll(`.marker.ever-visited-${activePlayer.toLowerCase()}.region-${activeRegion}`);
    if (showEverVisited)
        everVisitedMarkers.forEach(m => {
            m.style.color = colors[activePlayer][tint];
            m.parentElement.style.display = null;
        });
    else
        everVisitedMarkers.forEach(m => {
            m.style.color = 'red';
            m.parentElement.style.display = showUnvisited ? null : 'none';
        });
    document.querySelectorAll(`.marker:not(.visited-${activePlayer.toLowerCase()})`).forEach(m => {
        m.style.color = 'red';
        m.parentElement.style.display = showUnvisited ? null : 'none';
    });
    document.querySelectorAll(`.marker:not(.region-${activeRegion})`).forEach(m => {
        m.parentElement.style.display = 'none';
    });

    document.querySelectorAll('.progress-list').forEach(
        list => list.style.display = list.getAttribute('data-player') === activePlayer.toLowerCase() ? null : 'none');
    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = percentage.getAttribute(`data-${activeRegion.toLowerCase()}-${showEverVisited ? 'ev-' : ''}${activePlayer.toLowerCase()}`);

    document.querySelectorAll('.leaflet-layer,.leaflet-control-zoom-in,.leaflet-control-zoom-out,.leaflet-control-attribution,.leaflet-control-theme')
        .forEach(e => e.style.filter = darkMode ? 'invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%)' : null);
    document.querySelectorAll('.folium-map,.marker,.sidebar,.toggle-sidebar').forEach(e => e.classList.toggle('dark', darkMode));
}

function toggleUnvisited() {
    showUnvisited = document.querySelector("#visited-switch").checked;
    refreshMap();
}

function toggleEV() {
    showEverVisited = document.querySelector("#ev-switch").checked;
    refreshMap();
}

function selectPlayer() {
    activePlayer = document.querySelector("#player-selection select").value;
    localStorage.setItem('activePlayer', activePlayer);
    refreshMap();
}

function selectRegion() {
    activeRegion = document.querySelector("#region-selection select").value;
    localStorage.setItem('activeRegion', activeRegion);
    refreshMap();
}

function toggleAchievements() {
    document.querySelector('#achievements').classList.toggle('expanded');
    document.querySelector('#toggle-achievements').classList.toggle('expanded');
}

function toggleVehicles() {
    document.querySelector('#vehicles').classList.toggle('expanded');
    document.querySelector('#toggle-vehicles').classList.toggle('expanded');
}

document.addEventListener('DOMContentLoaded', () => {
    activePlayer = localStorage.getItem('activePlayer') || 'Zorie';
    document.querySelector("#player-selection select").value = activePlayer;
    activeRegion = localStorage.getItem('activeRegion') || 'POZ';
    document.querySelector("#region-selection select").value = activeRegion;
    darkMode = localStorage.getItem('darkMode') !== 'false';
    injectThemeSwitcher();
    refreshMap();
});
