import { Router } from 'express';
import { Database } from '../db/Database.js';

export const healthRouter = Router();

healthRouter.get('/health', async (_req, res) => {
  const db = Database.getInstance();
  if (!db.isConfigured) {
    return res.status(503).json({ api: 'up', database: 'not configured' });
  }
  try {
    const { rows } = await db.query('SELECT now() AS server_time, count(*)::int AS styles FROM design_styles');
    res.json({ api: 'up', database: 'up', ...rows[0] });
  } catch (err) {
    console.error('Health check failed:', err.message);
    res.status(503).json({ api: 'up', database: 'down' });
  }
});
