import { createApp } from './app.js';
import { env } from './config/env.js';

createApp().listen(env.port, () => {
  console.log(`DecoraIA API listening on port ${env.port}`);
});
