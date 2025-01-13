function scrollToPreview(vehicleElement) {
    vehicleElement.scrollIntoView();
    window.scrollTo(0, 0);
}

function cropSVG(svgImage, margin) {
    const bbox = svgImage.getBBox();
    svgImage.setAttribute("viewBox", `${bbox.x - margin} ${bbox.y - margin} ${bbox.width + 2 * margin} ${bbox.height + 2 * margin}`);
    svgImage.setAttribute("width", bbox.width + 2 * margin);
    svgImage.setAttribute("height", bbox.height + 2 * margin);
}