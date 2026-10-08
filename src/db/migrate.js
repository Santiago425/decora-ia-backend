import { readFile } from 'node:fs/promises';
import { Database } from './Database.js';

const db = Database.getInstance();
const sql = await readFile(new URL('./schema.sql', import.meta.url), 'utf8');

try {
  await db.query(sql);
  console.log('Schema applied');
} finally {
  await db.close();
}
