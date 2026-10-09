import express from 'express';
import { helloRouter } from './routes/hello.routes.js';
import { healthRouter } from './routes/health.routes.js';
import { remodelRouter } from './routes/remodel.routes.js';
import { corsPolicy, errorHandler, notFound, securityHeaders, writeLimiter } from './middleware/security.js';

export function createApp() {
  const app = express();
  app.disable('x-powered-by');
  app.set('trust proxy', 1);

  app.use(securityHeaders());
  app.use(corsPolicy());
  app.use(express.json({ limit: '20kb' }));
  app.post('/api/v1/*path', writeLimiter());

  app.get('/', (_req, res) => res.redirect('/api/v1/hello'));
  app.use('/api/v1', helloRouter, healthRouter, remodelRouter);

  app.use(notFound);
  app.use(errorHandler);

  return app;
}
