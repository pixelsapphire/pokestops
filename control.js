let showUnvisited = false;
let activePlayer = 'Zorie';

let colors = {
    'Zorie': '#4caf50',
    'Sapphire': '#8566d9',
    'Camomile': '#ff9800',
};

function refreshMap() {
    document.querySelectorAll(`.marker.visited-${activePlayer.toLowerCase()}`).forEach(m => {
        m.style.color = colors[activePlayer];
        m.style.display = null;
    });
    document.querySelectorAll(`.marker:not(.visited-${activePlayer.toLowerCase()})`).forEach(m => {
        m.style.color = 'red';
        m.style.display = showUnvisited ? null : 'none';
    });
    document.querySelectorAll('.progress-list').forEach(
        list => list.style.display = list.getAttribute('data-player') === activePlayer.toLowerCase() ? null : 'none');
    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = percentage.getAttribute(`data-${activePlayer.toLowerCase()}`);
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

function toggleAchievements() {
    document.querySelector('#achievements').classList.toggle('expanded');
    document.querySelector('#toggle-achievements').classList.toggle('expanded');
}

document.addEventListener('DOMContentLoaded', () => {
    activePlayer = localStorage.getItem('activePlayer') || 'Zorie';
    document.querySelector("#player-selection select").value = activePlayer;
    refreshMap();
});