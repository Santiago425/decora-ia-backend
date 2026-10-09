import helmet from 'helmet';
import cors from 'cors';
import { rateLimit } from 'express-rate-limit';
import { env } from '../config/env.js';

export function securityHeaders() {
  return helmet({
    contentSecurityPolicy: { directives: { defaultSrc: ["'none'"], frameAncestors: ["'none'"] } },
    crossOriginResourcePolicy: { policy: 'cross-origin' },
  });
}

export function corsPolicy() {
  const allowAll = env.corsOrigins.includes('*');
  return cors({
    origin: allowAll ? '*' : env.corsOrigins,
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    maxAge: 600,
  });
}

export function writeLimiter() {
  return rateLimit({
    windowMs: 60 * 1000,
    limit: env.rateLimitPerMinute,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: 'Demasiadas solicitudes, intenta de nuevo en un minuto' },
  });
}

export function notFound(_req, res) {
  res.status(404).json({ error: 'Not found' });
}

export function errorHandler(err, _req, res, _next) {
  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({ error: 'Invalid JSON body' });
  }
  if (err.type === 'entity.too.large') {
    return res.status(413).json({ error: 'Request body too large' });
  }
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
}
