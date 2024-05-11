let showUnvisited = false;
let activePlayer = 'Zorie';

function refreshMarkers() {
    document.querySelectorAll(`.marker.visited-${activePlayer.toLowerCase()}`).forEach(m => {
        m.style.color = activePlayer === 'Zorie' ? '#4caf50' : '#8566d9';
        m.style.display = null;
    });
    document.querySelectorAll(`.marker:not(.visited-${activePlayer.toLowerCase()})`).forEach(m => {
        m.style.color = 'red';
        m.style.display = showUnvisited ? null : 'none';
    });
}

function toggleUnvisited() {
    showUnvisited = document.querySelector("#visited-switch").checked;
    refreshMarkers();
}

function togglePlayer() {
    activePlayer = document.querySelector("#player-switch").checked ? 'Zorie' : 'Sapphire';
    document.querySelector('#nickname').innerHTML = activePlayer;
    const percentage = document.querySelector('#exploration-percentage');
    percentage.innerHTML = percentage.getAttribute(`data-${activePlayer.toLowerCase()}`);
    refreshMarkers();
}