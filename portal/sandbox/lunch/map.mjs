const gpsUrl = 'https://raw.githubusercontent.com/pakchee0529/line-map-bot/main/GPS.json';
const radians = Math.PI / 180;
const earthRadius = 6371000;
let poleData;

async function poles() {
  if (!poleData) {
    poleData = fetch(gpsUrl, {signal: AbortSignal.timeout(20000)})
      .then(async response => {
        if (!response.ok) throw Error('電柱データを読み込めませんでした。');
        const points = [];
        for (const [name, coordinate] of Object.entries(await response.json())) {
          if (typeof coordinate !== 'string') continue;
          const [lat, lng] = coordinate.split(',').map(Number);
          if (Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
            points.push([name, lat, lng]);
          }
        }
        if (!points.length) throw Error('電柱データが空です。');
        return points;
      }).catch(error => {
        poleData = undefined;
        throw error;
      });
  }
  return poleData;
}

function nearest(points, lat, lng) {
  let best = Infinity, name = '';
  const cosLat = Math.cos(lat * radians);
  for (const [candidate, poleLat, poleLng] of points) {
    const north = Math.sin((poleLat - lat) * radians / 2) ** 2;
    if (north >= best) continue;
    const east = Math.sin((poleLng - lng) * radians / 2) ** 2;
    const distance = north + cosLat * Math.cos(poleLat * radians) * east;
    if (distance < best) {
      best = distance;
      name = candidate;
    }
  }
  return {pole: name, poleDistance: Math.round(2 * earthRadius * Math.asin(Math.sqrt(Math.min(best, 1))))};
}

export async function mountMap(element, onPick, onSelect) {
  const L = window.L;
  if (!L) throw Error('地図を読み込めませんでした。再読み込みしてください。');
  const map = L.map(element, {scrollWheelZoom: false}).setView([34.379692, 135.672989], 13);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);
  const markers = L.layerGroup().addTo(map);
  let choice, revision = 0, initial = true;

  async function choose(lat, lng) {
    const request = ++revision;
    initial = false;
    choice?.remove();
    choice = L.circleMarker([lat, lng], {
      radius: 9, color: '#fff', weight: 3, fillColor: '#db661d', fillOpacity: 1, interactive: false
    }).addTo(map).bindTooltip('最寄りの電柱を確認中…', {permanent: true}).openTooltip();
    let match = {pole: '', poleDistance: null};
    try { match = nearest(await poles(), lat, lng); } catch { /* The pin is usable without pole data. */ }
    if (revision !== request) return;
    const tooltip = document.createElement('span');
    tooltip.textContent = match.pole ? match.pole + '・約' + match.poleDistance + 'm' : '電柱データを確認できません';
    choice.setTooltipContent(tooltip);
    const selected = {lat, lng, ...match};
    onPick(selected);
    return selected;
  }
  map.on('click', event => choose(event.latlng.lat, event.latlng.lng));
  return {
    setSpots(spots) {
      markers.clearLayers();
      const positions = [];
      for (const spot of spots) {
        if (!Number.isFinite(spot.lat) || !Number.isFinite(spot.lng)) continue;
        const point = [spot.lat, spot.lng];
        positions.push(point);
        L.marker(point, {title: spot.name, alt: spot.name}).addTo(markers).on('click', () => {
          ++revision;
          choice?.remove();
          onSelect(spot.id);
        });
      }
      if (initial && positions.length) {
        map.fitBounds(positions, {padding: [30, 30], maxZoom: 15});
        initial = false;
      }
    },
    async locate() {
      if (!navigator.geolocation) throw Error('現在地を利用できません。地図をタップして選んでください。');
      const request = ++revision;
      const position = await new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve,
        () => reject(Error('現在地を取得できません。地図をタップして選んでください。')),
        {enableHighAccuracy: true, timeout: 12000, maximumAge: 30000}));
      if (revision !== request) return;
      const {latitude, longitude} = position.coords;
      map.setView([latitude, longitude], 17);
      return choose(latitude, longitude);
    }
  };
}
