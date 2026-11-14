import { api } from './api';

// Preserve existing list consumers while fetching bounded server pages.
export async function listRepairs(scope) {
  const rows = [], seen = new Set();
  let cursor;
  do {
    const response = await api.get('/repairs', { params: { scope, ...(cursor ? { cursor } : {}) } });
    rows.push(...response.data);
    cursor = response.headers?.['x-next-cursor'];
    if (cursor && seen.has(cursor)) throw new Error('Repeated repair page cursor');
    seen.add(cursor);
  } while (cursor);
  return rows;
}
