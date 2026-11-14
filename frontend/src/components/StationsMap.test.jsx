import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { StationsMap } from './StationsMap';

const mockNavigate = jest.fn();
const mockContainerProps = jest.fn();
const mockMap = { setView: jest.fn(), fitBounds: jest.fn(), panTo: jest.fn(), setZoom: jest.fn() };
// CRA's Jest 27 resolver cannot resolve the router's export-only package entry.
jest.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate }), { virtual: true });
jest.mock('../context/ThemeContext', () => ({ useTheme: () => ({ theme: 'light' }) }));
jest.mock('../lib/api', () => ({ inr: (value) => `₹${value}` }));
jest.mock('react-leaflet', () => ({
  MapContainer: ({ children, ...props }) => { mockContainerProps(props); return <div>{children}</div>; },
  Marker: ({ children, title }) => <div data-marker={title}>{children}</div>,
  Popup: ({ children }) => <div>{children}</div>,
  TileLayer: () => null, Circle: () => null, useMap: () => mockMap,
}));
const station = { charger_id: 'CHG-001', name: 'Sector 62', location: 'Noida', status: 'Available', lat: 28, lng: 77, price_per_kwh: 15, max_power_kw: 7.4, connector: 'Type 2' };
let container, root, success, failure;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: { getCurrentPosition: jest.fn((ok, fail) => { success = ok; failure = fail; }) } });
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });
const render = (stations = [station]) => act(() => root.render(<StationsMap stations={stations} />));
test('renders without location and preserves navigation', () => {
  render();
  expect(container.textContent).toContain('Sector 62');
  expect(container.textContent).toContain('Finding your location');
  expect(container.textContent).not.toContain('away');
  act(() => container.querySelector('button').click());
  expect(mockNavigate).toHaveBeenCalledWith('/app/charger/CHG-001');
  expect(mockMap.setView).not.toHaveBeenCalled();
});
test.each([[1, 'Location access is off'], [2, 'Unable to determine your location'], [3, 'timed out']])('location failure %s leaves stations usable', (code, message) => {
  render(); act(() => failure({ code }));
  expect(container.textContent).toContain(message);
  expect(mockContainerProps).toHaveBeenLastCalledWith(expect.objectContaining({ center: [22.9734, 78.6569], zoom: 5 }));
  expect(mockMap.setView).not.toHaveBeenCalled();
  expect(mockMap.fitBounds).not.toHaveBeenCalled();
  expect(container.querySelector('button').textContent).toBe('View charger');
  expect(container.textContent).not.toContain('away');
});
test('unsupported geolocation leaves map usable', () => {
  Object.defineProperty(navigator, 'geolocation', { value: undefined }); render();
  expect(container.textContent).toContain('not supported');
  expect(container.textContent).toContain('Sector 62');
});
test('delayed location centers once at zoom 13; updates preserve user viewport', () => {
  render(); act(() => success({ coords: { latitude: 28.01, longitude: 77, accuracy: 20 } }));
  expect(container.textContent).toContain('You are here');
  expect(container.textContent).toContain('Nearest available');
  expect(container.textContent).toContain('1.1 km away');
  expect(mockMap.setView).toHaveBeenCalledWith([28.01, 77], 13, { animate: false });
  act(() => { mockMap.panTo([19, 73]); mockMap.setZoom(10); });
  render([{ ...station, status: 'Charging' }]);
  expect(container.textContent).not.toContain('Nearest available');
  expect(container.querySelector('button').textContent).toBe('View charger');
  expect(mockMap.fitBounds).not.toHaveBeenCalled();
  render([{ ...station, lat: 19, lng: 73 }, { ...station, charger_id: 'new', lat: 12, lng: 77 }]);
  // Even another location value cannot turn the initial positioner into a follower.
  act(() => success({ coords: { latitude: 28.02, longitude: 77, accuracy: 10 } }));
  expect(mockMap.setView).toHaveBeenCalledTimes(1);
  expect(mockMap.fitBounds).not.toHaveBeenCalled();
  expect(navigator.geolocation.getCurrentPosition).toHaveBeenCalledTimes(1);
});
test('empty and invalid stations do not cause map fitting errors', () => {
  render([{ ...station, lat: null }]);
  expect(mockMap.setView).not.toHaveBeenCalled();
  expect(mockMap.fitBounds).not.toHaveBeenCalled();
});

test('sets India center and strict pan bounds while rendering India stations', () => {
  render();
  expect(mockContainerProps).toHaveBeenLastCalledWith(expect.objectContaining({
    center: [22.9734, 78.6569], maxBounds: [[6.5, 68], [37.5, 97.5]], maxBoundsViscosity: 1, minZoom: 4,
  }));
  expect(container.querySelector('[data-marker="Sector 62 — Available"]')).not.toBeNull();
});
test('station datasets never auto-fit and outside customer location preserves fallback', () => {
  render([station, { ...station, charger_id: 'india-2', lat: 19, lng: 73 },
    { ...station, charger_id: 'outside', lat: 51.5, lng: -0.1 }]);
  expect(mockMap.fitBounds).not.toHaveBeenCalled();
  act(() => success({ coords: { latitude: 40.7, longitude: -74, accuracy: 20 } }));
  expect(mockMap.fitBounds).not.toHaveBeenCalled();
  expect(mockMap.setView).not.toHaveBeenCalled();
  expect(container.textContent).toContain('away');
});
test('outside-only coordinates leave default India view intact', () => {
  render([{ ...station, lat: 51.5, lng: -0.1 }]);
  act(() => success({ coords: { latitude: 40.7, longitude: -74, accuracy: 20 } }));
  expect(mockMap.fitBounds).not.toHaveBeenCalled();
  expect(mockMap.setView).not.toHaveBeenCalled();
});

test.each(['Available', 'Charging', 'Preparing', 'Finishing', 'Fault', 'Offline'])('offers coordinate navigation and preserves charger action for %s', (status) => {
  const open = jest.spyOn(window, 'open').mockImplementation(() => null);
  try {
    render([{ ...station, status, lat: 28.4595, lng: 77.0266 }]);
    const navigateButton = container.querySelector('[data-testid="map-navigate-CHG-001"]');
    expect(navigateButton.textContent).toBe('Navigate');
    act(() => navigateButton.click());
    expect(open).toHaveBeenCalledWith('https://www.google.com/maps/dir/?api=1&destination=28.4595,77.0266', '_blank', 'noopener,noreferrer');
    expect(mockNavigate).not.toHaveBeenCalled();
    const chargerButton = container.querySelector('[data-testid="map-view-CHG-001"]');
    expect(chargerButton.textContent).toBe(status === 'Available' ? 'View charger' : 'View charger');
    act(() => chargerButton.click());
    expect(mockNavigate).toHaveBeenCalledWith('/app/charger/CHG-001');
  } finally { open.mockRestore(); }
});
test.each([[null, 77], [28, undefined], [NaN, 77], [28, Infinity], [91, 77], [28, 181], ['28', 77]])('invalid coordinates %s, %s have no navigation action', (lat, lng) => {
  render([{ ...station, lat, lng }]);
  expect(container.querySelector('[data-testid="map-navigate-CHG-001"]')).toBeNull();
});

test('denied location can be retried explicitly without following later changes', () => {
  render(); act(() => failure({ code: 1 }));
  const retry = [...container.querySelectorAll('button')].find(button => button.textContent === 'Enable location');
  expect(retry).toBeDefined();
  act(() => retry.click());
  expect(navigator.geolocation.getCurrentPosition).toHaveBeenCalledTimes(2);
  act(() => success({ coords: { latitude: 28, longitude: 77, accuracy: 20 } }));
  expect(mockMap.setView).toHaveBeenCalledTimes(1);
});
test('nearby count excludes distant, invalid and occupied stations', () => {
  const count = jest.fn();
  act(() => root.render(<StationsMap onNearbyCount={count} stations={[station, { ...station, charger_id: 'far', lat: 19 }, { ...station, charger_id: 'busy', status: 'Preparing' }]} />));
  expect(count).toHaveBeenLastCalledWith(null);
  act(() => success({ coords: { latitude: 28, longitude: 77, accuracy: 20 } }));
  expect(count).toHaveBeenLastCalledWith(1);
});
