import 'dotenv/config';

export const env = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  databaseUrl: process.env.DATABASE_URL || '',
  corsOrigin: process.env.CORS_ORIGIN || '*',
  aiProvider: process.env.AI_PROVIDER || 'mock',
  aiServiceUrl: process.env.AI_SERVICE_URL || '',
});
