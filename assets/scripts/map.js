let showUnvisited = false;
let showEverVisited = false;
let stellarVoyage = false;
let activePlayer = 'Zorie';
let activeRegion = 'POZ';
let darkMode = true;

const lightModeIcon = 'assets/images/light_mode.png';
const darkModeIcon = 'assets/images/dark_mode.png';

const primary = 0;
const tint = 1;

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

function refreshMap() {

    const percentage = document.querySelector('#exploration-percentage');
    document.body.classList.toggle('stellar-voyage', stellarVoyage);

    if (!stellarVoyage) {

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
        document.querySelectorAll(`.marker.terminal`).forEach(m => {
            m.parentElement.style.display = 'none';
        });

        percentage.innerHTML = `${percentage.getAttribute(`data-${activeRegion.toLowerCase()}-${showEverVisited ? 'ev-' : ''}${activePlayer.toLowerCase()}`)} %`;

    } else {
        document.querySelectorAll(`.marker.terminal`).forEach(m => {
            if (m.classList.contains(`reached-${activePlayer.toLowerCase()}`)) m.style.color = colors[activePlayer][primary];
            else m.style.color = 'red';
            m.parentElement.style.display = null;
        });
        document.querySelectorAll(`.marker.tp-${activePlayer.toLowerCase()}`).forEach(m => {
            m.parentElement.style.display = null;
            if (m.classList.contains(`visited-${activePlayer.toLowerCase()}`)) m.style.color = colors[activePlayer][tint];
            else m.style.color = 'red';
        });
        document.querySelectorAll(`.marker:not(.terminal):not(.tp-${activePlayer.toLowerCase()})`).forEach(m => {
            m.parentElement.style.display = 'none';
        });

        percentage.innerHTML = `${percentage.getAttribute(`data-sv-${activePlayer.toLowerCase()}`)} %`;
    }

    document.querySelectorAll('.progress-list').forEach(
        list => list.style.display = list.getAttribute('data-player') === activePlayer.toLowerCase() ? null : 'none');

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

function toggleSV() {
    stellarVoyage = document.querySelector("#sv-switch").checked;
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

function toggleSidebar(sidebar) {
    document.querySelector(`#${sidebar}`).classList.toggle('expanded');
    document.querySelector(`#toggle-${sidebar}`).classList.toggle('expanded');
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
