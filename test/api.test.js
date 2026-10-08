import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';

let server;
let base;

before(async () => {
  server = createApp().listen(0);
  await new Promise((resolve) => server.once('listening', resolve));
  base = `http://127.0.0.1:${server.address().port}/api/v1`;
});

after(() => server.close());

test('GET /hello returns Hello World', async () => {
  const res = await fetch(`${base}/hello`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.match(body.message, /Hello World/);
});

test('POST /remodels/preview returns a mock remodel', async () => {
  const res = await fetch(`${base}/remodels/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ photoUrl: 'https://example.com/room.jpg', style: 'nordic' }),
  });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.provider, 'mock');
  assert.ok(body.suggestions.length > 0);
});

test('POST /remodels/preview rejects a missing photo', async () => {
  const res = await fetch(`${base}/remodels/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ style: 'modern' }),
  });
  assert.equal(res.status, 400);
});
