function selectRaid(preview) {
    document.querySelectorAll('.raid-log').forEach((log) => log.classList.remove('selected'));
    document.getElementById(preview.getAttribute('data-raid-id')).classList.add('selected');
    cropSVG(document.querySelector('.raid-timeline'), 8);
    window.location.hash = preview.getAttribute('data-raid-id');
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.raid-preview').forEach((preview) => preview.addEventListener('click', () => selectRaid(preview)));
    const hash = window.location.hash;
    if (hash) {
        const preview = document.querySelector('#raids-index>.raid-preview[data-raid-id="' + hash.substring(1) + '"]');
        if (preview) preview.click() && scrollToPreview(preview);
    }
});