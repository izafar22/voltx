import { listRepairs } from './repairApi';
import { api } from './api';
jest.mock('./api', () => ({ api: { get: jest.fn() } }));
beforeEach(() => api.get.mockReset());
test('loads all pages without changing list shape', async () => {
  api.get.mockResolvedValueOnce({ data: [{ id: 'one' }], headers: { 'x-next-cursor': 'next' } })
    .mockResolvedValueOnce({ data: [{ id: 'two' }], headers: {} });
  expect(await listRepairs('mine')).toEqual([{ id: 'one' }, { id: 'two' }]);
  expect(api.get).toHaveBeenLastCalledWith('/repairs', { params: { scope: 'mine', cursor: 'next' } });
});
test('repeated cursor fails instead of looping', async () => {
  api.get.mockResolvedValue({ data: [], headers: { 'x-next-cursor': 'same' } });
  await expect(listRepairs('all')).rejects.toThrow('Repeated repair page cursor');
});
