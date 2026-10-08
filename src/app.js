import express from 'express';
import cors from 'cors';
import { env } from './config/env.js';
import { helloRouter } from './routes/hello.routes.js';
import { healthRouter } from './routes/health.routes.js';
import { remodelRouter } from './routes/remodel.routes.js';

export function createApp() {
  const app = express();
  app.use(cors({ origin: env.corsOrigin }));
  app.use(express.json({ limit: '1mb' }));

  app.get('/', (_req, res) => res.redirect('/api/v1/hello'));
  app.use('/api/v1', helloRouter, healthRouter, remodelRouter);

  app.use((_req, res) => res.status(404).json({ error: 'Not found' }));
  app.use((err, _req, res, _next) => {
    console.error(err);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
