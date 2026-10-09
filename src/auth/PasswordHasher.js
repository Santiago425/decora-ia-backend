import { randomBytes, scrypt, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';

const scryptAsync = promisify(scrypt);
const KEY_LENGTH = 64;
const COST = 16384;

export async function hashPassword(password) {
  const salt = randomBytes(16).toString('hex');
  const key = await scryptAsync(password, salt, KEY_LENGTH, { N: COST });
  return `scrypt$${COST}$${salt}$${key.toString('hex')}`;
}

export async function verifyPassword(password, stored) {
  const [algorithm, cost, salt, hash] = String(stored).split('$');
  if (algorithm !== 'scrypt' || !salt || !hash) return false;
  const expected = Buffer.from(hash, 'hex');
  const key = await scryptAsync(password, salt, expected.length, { N: Number(cost) });
  return timingSafeEqual(key, expected);
}
