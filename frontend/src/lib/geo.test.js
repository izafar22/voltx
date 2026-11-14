import { calculateDistanceKm, formatDistance, isWithinIndiaBounds } from './geo';
import { getStatusGroup, isAvailable, findNearestAvailable } from './stationStatus';

test('Haversine handles known distances, zero, and antipodes', () => {
  expect(calculateDistanceKm(0, 0, 0, 1)).toBeCloseTo(111.195, 2);
  expect(calculateDistanceKm(28, 77, 28, 77)).toBe(0);
  expect(calculateDistanceKm(0, 0, 0, 180)).toBeCloseTo(Math.PI * 6371);
});
test.each([null, undefined, NaN, Infinity, '', '28', 91])('rejects invalid latitude %s', (lat) => {
  expect(calculateDistanceKm(lat, 0, 0, 0)).toBeNull();
});
test('rejects invalid longitude and formats distances', () => {
  expect(calculateDistanceKm(0, 181, 0, 0)).toBeNull();
  expect(formatDistance(.65)).toBe('650 m');
  expect(formatDistance(2.44)).toBe('2.4 km');
  expect(formatDistance(1)).toBe('1.0 km');
  expect(formatDistance(0)).toBe('0 m');
  [null, NaN, Infinity, -1].forEach((value) => expect(formatDistance(value)).toBeNull());
});
test.each([['Available', 'available'], ['Charging', 'in-use'], ['Preparing', 'in-use'], ['Finishing', 'in-use'], ['Fault', 'fault'], ['Offline', 'offline'], ['unknown', 'offline'], [null, 'offline']])('groups %s', (status, group) => {
  expect(getStatusGroup(status)).toBe(group);
  expect(isAvailable(status)).toBe(group === 'available');
});
test('nearest selection excludes occupied, faulty, offline and invalid stations', () => {
  const location = { latitude: 0, longitude: 0 };
  const stations = ['Charging', 'Preparing', 'Finishing', 'Fault', 'Offline'].map(status => ({ status, lat: 0, lng: 0 }));
  expect(findNearestAvailable(stations, location)).toBeNull();
  stations.push({ status: 'Available', lat: null, lng: 0 }, { status: 'Available', lat: 0, lng: 2, charger_id: 'far' }, { status: 'Available', lat: 0, lng: 1, charger_id: 'near' });
  expect(findNearestAvailable(stations, location).station.charger_id).toBe('near');
  expect(findNearestAvailable(stations, null)).toBeNull();
  expect(findNearestAvailable([], location)).toBeNull();
});

test.each([[28, 77], [22.9734, 78.6569], [6.5, 68], [37.5, 97.5]])('accepts India bounds coordinate %s, %s', (lat, lng) => {
  expect(isWithinIndiaBounds(lat, lng)).toBe(true);
});
test.each([[6.49, 78], [37.51, 78], [28, 67.99], [28, 97.51], [null, 77], [28, NaN], ['28', 77], [Infinity, 77]])('rejects outside or invalid India coordinate %s, %s', (lat, lng) => {
  expect(isWithinIndiaBounds(lat, lng)).toBe(false);
});
