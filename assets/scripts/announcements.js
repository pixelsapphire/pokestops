document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.announcement-preview').forEach((preview) => {
        preview.addEventListener('click', () => {
            document.querySelectorAll('.announcement-article').forEach((article) => {
                article.classList.remove('selected');
            });
            document.getElementById(preview.getAttribute('data-article-id')).classList.add('selected');
            window.location.hash = preview.getAttribute('data-article-id');
        });
    });
    document.querySelectorAll('.announcement-article img').forEach((image) => {
        image.removeAttribute('width');
        image.removeAttribute('height');
        image.removeAttribute('sizes');
        image.parentElement.parentElement.style.maxWidth = '100%';
        image.parentElement.parentElement.style.textAlign = 'center';
        image.style.maxWidth = '100%';
        image.style.maxHeight = '66.67dvh';
    });

    const hash = window.location.hash;
    if (hash) {
        const preview = document.querySelector('#announcements-index>.announcement-preview[data-article-id="' + hash.substring(1) + '"]');
        if (preview) preview.click() && scrollToPreview(preview);
    }
});