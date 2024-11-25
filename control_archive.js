function openTab(tile, tab) {
    document.querySelectorAll('.navigation-tile, .content-container').forEach(e => e.classList.remove('selected'));
    tile.classList.add('selected');
    document.querySelector(`#container-${tab}`).classList.add('selected');
}

function make_address(address) {
    let road = address.road ? `${address.road}` : '';
    const suburb = address.suburb ? `${address.suburb}, ` : '';
    const town = address.city || address.town || address.village;
    if (address.house_number) return `${road} ${address.house_number}, ${address.postcode}, ${town}`;
    if (address.road) road += ', ';
    return `${road}${suburb}${address.postcode} ${town}`;
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.stop-header').forEach(header => header.addEventListener('click', () => {
        let groupView = header.parentElement;
        let expandIcon = groupView.querySelector('.expand-icon');
        groupView.classList.toggle('expanded');
        expandIcon.innerHTML = groupView.classList.contains('expanded') ? 'remove' : 'add';
    }));
    let stopView = document.querySelector('#stop-view');
    let stopDetails = stopView.querySelector('#stop-details');
    let stopNameLabel = stopView.querySelector('#stop-name');
    let stopLinesField = stopView.querySelector('#stop-lines');
    let stopAddressLabel = stopView.querySelector('#stop-address');
    let stopCoordinatesLabel = stopView.querySelector('#stop-coordinates');
    let stopLocationViewButton = stopView.querySelector('#street-view-link');
    document.querySelectorAll('.stop-preview').forEach(preview => preview.addEventListener('click', () => {
        stopDetails.classList.remove('hidden');
        const stopId = preview.getAttribute('data-stop-id');
        const stop = stops[stopId];
        stopNameLabel.innerHTML = `${stop.n} [${stopId}]`;
        stopLinesField.innerHTML = '';
        stops[stopId].l.forEach(line => {
            const [number, destination] = line;
            stopLinesField.innerHTML += `<div class="line-view"><span class="line-number">${number}</span><span class="line-destination">${destination}</span></div>`;
        });
        const coordinates = `${stop.lt},${stop.ln}`;
        const streetViewLink = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${coordinates}`
        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${stop.lt}&lon=${stop.ln}&zoom=18&addressdetails=1`)
            .then(response => response.json())
            .then(data => stopAddressLabel.innerHTML = make_address(data.address));
        stopCoordinatesLabel.innerHTML = `(${coordinates})`;
        stopLocationViewButton.href = streetViewLink;
    }));
});
