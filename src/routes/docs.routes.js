import { Router } from 'express';
import swaggerUi from 'swagger-ui-express';
import { openapi } from '../docs/openapi.js';

export const docsRouter = Router();

const docsCsp = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https:",
  "connect-src 'self'",
  "frame-ancestors 'none'",
].join('; ');

docsRouter.get('/openapi.json', (_req, res) => res.json(openapi));

docsRouter.use(
  '/docs',
  (_req, res, next) => {
    res.setHeader('Content-Security-Policy', docsCsp);
    next();
  },
  swaggerUi.serve,
  swaggerUi.setup(openapi, {
    customSiteTitle: 'DecoraIA · Documentación de la API',
    customCss: '.swagger-ui .topbar { display: none }',
    swaggerOptions: { persistAuthorization: true, displayRequestDuration: true },
  }),
);
