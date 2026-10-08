import { createApp } from './app.js';
import { env } from './config/env.js';
import { Database } from './db/Database.js';
import { migrate } from './db/migrate.js';

if (Database.getInstance().isConfigured) {
  try {
    await migrate();
    console.log('Database schema ready');
  } catch (err) {
    console.error('Database migration failed:', err.message);
  }
}

createApp().listen(env.port, () => {
  console.log(`DecoraIA API listening on port ${env.port}`);
});
