function selectRaid(preview) {
    document.querySelectorAll('.raid-log').forEach((log) => log.classList.remove('selected'));
    const raidId = preview.getAttribute('data-raid-id');
    document.getElementById(raidId).classList.add('selected');
    cropSVG(document.querySelector(`.raid-timeline[data-raid-id="${raidId}"]`), 8);
    window.location.hash = raidId;
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.raid-preview').forEach((preview) => preview.addEventListener('click', () => selectRaid(preview)));
    const hash = window.location.hash;
    if (hash) {
        const preview = document.querySelector('#raids-index>.raid-preview[data-raid-id="' + hash.substring(1) + '"]');
        if (preview) preview.click() && scrollToPreview(preview);
    }
});