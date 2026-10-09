import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';
import { hashPassword, verifyPassword } from '../src/auth/PasswordHasher.js';

let server;
let base;

const post = (path, body) =>
  fetch(`${base}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

before(async () => {
  server = createApp().listen(0);
  await new Promise((resolve) => server.once('listening', resolve));
  base = `http://127.0.0.1:${server.address().port}/api/v1`;
});

after(() => server.close());

test('passwords are hashed with a random salt', async () => {
  const a = await hashPassword('secreta123');
  const b = await hashPassword('secreta123');
  assert.notEqual(a, b);
  assert.ok(!a.includes('secreta123'));
  assert.ok(await verifyPassword('secreta123', a));
  assert.ok(!(await verifyPassword('otra12345', a)));
});

test('register, login and me', async () => {
  const reg = await post('/auth/register', { fullName: 'Luis', email: 'Luis@Example.com', password: 'clave1234' });
  assert.equal(reg.status, 201);
  const { user } = await reg.json();
  assert.equal(user.email, 'luis@example.com');
  assert.equal(user.passwordHash, undefined);

  const login = await post('/auth/login', { email: 'luis@example.com', password: 'clave1234' });
  assert.equal(login.status, 200);
  const { token } = await login.json();

  const me = await fetch(`${base}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
  assert.equal(me.status, 200);
  assert.equal((await me.json()).user.fullName, 'Luis');
});

test('rejects duplicates, weak passwords and wrong credentials', async () => {
  await post('/auth/register', { fullName: 'Eva', email: 'eva@example.com', password: 'clave1234' });
  assert.equal((await post('/auth/register', { fullName: 'Eva', email: 'eva@example.com', password: 'clave1234' })).status, 409);
  assert.equal((await post('/auth/register', { fullName: 'Eva', email: 'eva2@example.com', password: 'corta' })).status, 400);
  assert.equal((await post('/auth/register', { fullName: 'Eva', email: 'eva3@example.com', password: 'soloLetras' })).status, 400);
  const wrong = await post('/auth/login', { email: 'eva@example.com', password: 'incorrecta1' });
  assert.equal(wrong.status, 401);
  const missing = await post('/auth/login', { email: 'nadie@example.com', password: 'incorrecta1' });
  assert.equal(missing.status, 401);
  assert.deepEqual(await wrong.json(), await missing.json());
});

test('rejects forged or missing tokens', async () => {
  assert.equal((await fetch(`${base}/auth/me`)).status, 401);
  const forged = await fetch(`${base}/auth/me`, { headers: { Authorization: 'Bearer abc.def.ghi' } });
  assert.equal(forged.status, 401);
});
