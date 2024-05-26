let showUnvisited = false;
let activePlayer = 'Zorie';
let activeRegion = 'POZ';

let colors = {
    'Zorie': '#4caf50',
    'Sapphire': '#8566d9',
    'Camomile': '#ff9800',
};

function refreshMap() {

    document.querySelectorAll(`.marker.visited-${activePlayer.toLowerCase()}.region-${activeRegion}`).forEach(m => {
        m.style.color = colors[activePlayer];
        m.parentElement.style.display = null;
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
    percentage.innerHTML = percentage.getAttribute(`data-${activeRegion.toLowerCase()}-${activePlayer.toLowerCase()}`);
}

function toggleUnvisited() {
    showUnvisited = document.querySelector("#visited-switch").checked;
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

document.addEventListener('DOMContentLoaded', () => {
    activePlayer = localStorage.getItem('activePlayer') || 'Zorie';
    document.querySelector("#player-selection select").value = activePlayer;
    activeRegion = localStorage.getItem('activeRegion') || 'POZ';
    document.querySelector("#region-selection select").value = activeRegion;
    refreshMap();
});