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

const post = (body, headers = {}) =>
  fetch(`${base}/remodels/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body,
  });

test('sends security headers and hides the framework', async () => {
  const res = await fetch(`${base}/hello`);
  assert.equal(res.headers.get('x-powered-by'), null);
  assert.equal(res.headers.get('x-content-type-options'), 'nosniff');
  assert.ok(res.headers.get('content-security-policy'));
});

test('malformed JSON returns 400 instead of 500', async () => {
  const res = await post('{bad json');
  assert.equal(res.status, 400);
});

test('oversized bodies are rejected', async () => {
  const res = await post(JSON.stringify({ photoUrl: `https://a.com/${'x'.repeat(30_000)}` }));
  assert.equal(res.status, 413);
});

test('rate limit blocks too many writes', async () => {
  const body = JSON.stringify({ photoUrl: 'https://example.com/room.jpg' });
  const statuses = [];
  for (let i = 0; i < 25; i++) statuses.push((await post(body)).status);
  assert.ok(statuses.includes(429));
});
