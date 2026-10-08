import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { Database } from './Database.js';

export async function migrate() {
  const sql = await readFile(new URL('./schema.sql', import.meta.url), 'utf8');
  await Database.getInstance().query(sql);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    await migrate();
    console.log('Schema applied');
  } finally {
    await Database.getInstance().close();
  }
}
