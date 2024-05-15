let showUnvisited = false;
let activePlayer = 'Zorie';

function refreshMarkersAndAchievements() {
    document.querySelectorAll(`.marker.visited-${activePlayer.toLowerCase()}`).forEach(m => {
        m.style.color = activePlayer === 'Zorie' ? '#4caf50' : '#8566d9';
        m.style.display = null;
    });
    document.querySelectorAll(`.marker:not(.visited-${activePlayer.toLowerCase()})`).forEach(m => {
        m.style.color = 'red';
        m.style.display = showUnvisited ? null : 'none';
    });
    document.querySelectorAll('.progress-list').forEach(
        list => list.style.display = list.getAttribute('data-player') === activePlayer.toLowerCase() ? null : 'none');
}

function toggleUnvisited() {
    showUnvisited = document.querySelector("#visited-switch").checked;
    refreshMarkersAndAchievements();
}

function togglePlayer() {
    activePlayer = document.querySelector("#player-switch").checked ? 'Zorie' : 'Sapphire';
    document.querySelector('#nickname').innerHTML = activePlayer;
    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = percentage.getAttribute(`data-${activePlayer.toLowerCase()}`);
    refreshMarkersAndAchievements();
}

function toggleAchievements() {
    document.querySelector('#achievements').classList.toggle('expanded');
    document.querySelector('#toggle-achievements').classList.toggle('expanded');
}