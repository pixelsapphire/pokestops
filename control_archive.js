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

function select_stop(stopPreview, ctrl) {
    ctrl.stopDetails.classList.remove('hidden');
    const stopId = stopPreview.getAttribute('data-stop-id');
    const stop = stops[stopId];
    ctrl.stopNameLabel.innerHTML = `${stop.n} [${stopId}]`;
    ctrl.stopLinesField.innerHTML = '';
    stops[stopId].l.forEach(line => {
        const [number, destination] = line;
        ctrl.stopLinesField.innerHTML += `<div class="line-view"><span class="line-number">${number}</span><span class="line-destination">${destination}</span></div>`;
    });
    const coordinates = `${stop.lt},${stop.ln}`;
    const streetViewLink = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${coordinates}`
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${stop.lt}&lon=${stop.ln}&zoom=18&addressdetails=1`)
        .then(response => response.json())
        .then(data => ctrl.stopAddressLabel.innerHTML = make_address(data.address));
    ctrl.stopCoordinatesLabel.innerHTML = `(${coordinates})`;
    ctrl.stopLocationViewButton.href = streetViewLink;
}

function select_vehicle(vehiclePreview, ctrl) {
    ctrl.vehicleDetails.classList.remove('hidden');
    const vehicleId = vehiclePreview.getAttribute('data-vehicle-id');
    const vehicle = vehicles[vehicleId];
    const model = vehicle.m ? vehicle_models[vehicle.m] : {k: 'bus', b: '?', m: '?'};
    const carrier = carriers[vehicle.c];
    ctrl.vehicleNameLabel.innerHTML = `#${vehicleId}`;
    ctrl.vehicleCarrierLabel.innerHTML = carrier.n;
    ctrl.vehicleKindLabel.innerHTML = model.k;
    ctrl.vehicleBrandLabel.innerHTML = model.b;
    ctrl.vehicleModelLabel.innerHTML = model.m;
    ctrl.vehicleSeatsLabel.innerHTML = model.s ? `${model.s}` : '?';
    ctrl.vehicleLoreLabel.innerHTML = ''
    if (model.l) ctrl.vehicleLoreLabel.innerHTML += `<p>${model.l}</p>`;
    if (vehicle.l) ctrl.vehicleLoreLabel.innerHTML += `<p>${vehicle.l}</p>`;
    if (vehicle.i) {
        ctrl.vehicleImage.innerHTML = `<img src="${vehicle.i}" alt="${model.b} ${model.m} #${vehicleId}">`;
        ctrl.vehicleImage.firstChild.addEventListener('click', () => window.open(vehicle.i, '_blank'));
    } else ctrl.vehicleImage.innerHTML = '';
}

Array.prototype.containsBS = function (target) {
    let left = 0;
    let right = this.length - 1;
    while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        if (this[mid] === target) return true;
        if (this[mid] < target) left = mid + 1;
        else right = mid - 1;
    }
    return false;
}

document.addEventListener('DOMContentLoaded', () => {

    document.querySelectorAll('.stop-header').forEach(header => header.addEventListener('click', () => {
        let groupView = header.parentElement;
        let expandIcon = groupView.querySelector('.expand-icon');
        groupView.classList.toggle('expanded');
        expandIcon.innerHTML = groupView.classList.contains('expanded') ? 'remove' : 'add';
    }));

    let stopView = document.querySelector('#stop-view');
    let stopViewControls = {
        stopDetails: stopView.querySelector('#stop-details'),
        stopNameLabel: stopView.querySelector('#stop-name'),
        stopLinesField: stopView.querySelector('#stop-lines'),
        stopAddressLabel: stopView.querySelector('#stop-address'),
        stopCoordinatesLabel: stopView.querySelector('#stop-coordinates'),
        stopLocationViewButton: stopView.querySelector('#street-view-link'),
    };
    document.querySelectorAll('.stop-preview').forEach(preview => preview.addEventListener('click', () => select_stop(preview, stopViewControls)));

    let vehicleView = document.querySelector('#vehicle-view');
    let vehicleViewControls = {
        vehicleDetails: vehicleView.querySelector('#vehicle-details'),
        vehicleNameLabel: vehicleView.querySelector('#vehicle-name'),
        vehicleKindLabel: vehicleView.querySelector('#vehicle-kind'),
        vehicleBrandLabel: vehicleView.querySelector('#vehicle-brand'),
        vehicleModelLabel: vehicleView.querySelector('#vehicle-model'),
        vehicleCarrierLabel: vehicleView.querySelector('#vehicle-carrier'),
        vehicleSeatsLabel: vehicleView.querySelector('#vehicle-seats'),
        vehicleLoreLabel: vehicleView.querySelector('#vehicle-lore'),
        vehicleImage: vehicleView.querySelector('#vehicle-image'),
    };
    document.querySelectorAll('.vehicle-preview').forEach(preview => preview.addEventListener('click', () => select_vehicle(preview, vehicleViewControls)));

    const activePlayer = players[localStorage.getItem('activePlayer') || 'Zorie'];
    document.querySelectorAll('.stop-group-view').forEach(group => {
        let groupDiscovered = false;
        group.querySelectorAll('.stop-preview').forEach(stop => {
            const id = stop.querySelector('.stop-id').innerHTML;
            if (activePlayer.s.containsBS(id)) groupDiscovered = true;
            else stop.classList.add('undiscovered');
        });
        if (!groupDiscovered) group.classList.add('undiscovered');
    });
    document.querySelectorAll('.vehicle-preview').forEach(preview => {
        const id = preview.getAttribute('data-vehicle-id');
        if (!activePlayer.v.containsBS(id)) preview.classList.add('undiscovered');
    });
});
