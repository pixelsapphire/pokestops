function toggle() {
    const toggled = document.querySelector("#visited-switch").checked;
    document.querySelectorAll(".unvisited").forEach(m => toggled ? m.classList.remove('hidden') : m.classList.add('hidden'));
}