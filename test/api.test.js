import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';

let server;
let base;
let token;

const json = (path, body, headers = {}) =>
  fetch(`${base}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });

before(async () => {
  server = createApp().listen(0);
  await new Promise((resolve) => server.once('listening', resolve));
  base = `http://127.0.0.1:${server.address().port}/api/v1`;
  const res = await json('/auth/register', { fullName: 'Ana Pérez', email: 'ana@example.com', password: 'secreta123' });
  token = (await res.json()).token;
});

after(() => server.close());

test('GET /hello returns Hello World', async () => {
  const res = await fetch(`${base}/hello`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.match(body.message, /Hello World/);
});

test('POST /remodels/preview requires a session', async () => {
  const res = await json('/remodels/preview', { photoUrl: 'https://example.com/room.jpg' });
  assert.equal(res.status, 401);
});

test('POST /remodels/preview returns a mock remodel', async () => {
  const res = await json(
    '/remodels/preview',
    { photoUrl: 'https://example.com/room.jpg', style: 'nordic' },
    { Authorization: `Bearer ${token}` },
  );
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.provider, 'mock');
  assert.ok(body.suggestions.length > 0);
});

test('POST /remodels/preview rejects a missing photo', async () => {
  const res = await json('/remodels/preview', { style: 'modern' }, { Authorization: `Bearer ${token}` });
  assert.equal(res.status, 400);
});
