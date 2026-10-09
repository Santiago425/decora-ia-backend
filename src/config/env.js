import 'dotenv/config';

const list = (value) => value.split(',').map((s) => s.trim()).filter(Boolean);

export const env = Object.freeze({
  nodeEnv: process.env.NODE_ENV || 'development',
  port: Number(process.env.PORT) || 3000,
  databaseUrl: process.env.DATABASE_URL || '',
  corsOrigins: list(process.env.CORS_ORIGIN || '*'),
  rateLimitPerMinute: Number(process.env.RATE_LIMIT_PER_MINUTE) || 20,
  aiProvider: process.env.AI_PROVIDER || 'mock',
  aiServiceUrl: process.env.AI_SERVICE_URL || '',
  aiTimeoutMs: Number(process.env.AI_TIMEOUT_MS) || 30000,
});
