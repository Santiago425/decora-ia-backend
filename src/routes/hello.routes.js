import { Router } from 'express';

export const helloRouter = Router();

helloRouter.get('/hello', (_req, res) => {
  res.json({
    message: 'Hello World desde DecoraIA',
    service: 'decora-ia-backend',
    timestamp: new Date().toISOString(),
  });
});
