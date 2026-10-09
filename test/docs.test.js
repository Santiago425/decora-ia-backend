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

test('GET /openapi.json documents every route', async () => {
  const res = await fetch(`${base}/openapi.json`);
  assert.equal(res.status, 200);
  const spec = await res.json();
  assert.equal(spec.openapi, '3.0.3');
  for (const path of ['/hello', '/health', '/auth/register', '/auth/login', '/auth/me', '/styles', '/room-types', '/remodels/preview']) {
    assert.ok(spec.paths[path], `missing ${path}`);
  }
});

test('GET /docs/ serves Swagger UI', async () => {
  const res = await fetch(`${base}/docs/`);
  assert.equal(res.status, 200);
  assert.match(await res.text(), /swagger-ui/);
  assert.match(res.headers.get('content-security-policy'), /script-src 'self'/);
});
