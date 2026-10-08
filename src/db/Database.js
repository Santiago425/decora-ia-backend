import pg from 'pg';
import { env } from '../config/env.js';

// Singleton: una sola conexión (pool) compartida por toda la aplicación.
export class Database {
  static #instance = null;
  #pool = null;

  constructor() {
    if (Database.#instance) {
      throw new Error('Use Database.getInstance()');
    }
  }

  static getInstance() {
    if (!Database.#instance) {
      Database.#instance = new Database();
    }
    return Database.#instance;
  }

  get isConfigured() {
    return Boolean(env.databaseUrl);
  }

  get pool() {
    if (!this.isConfigured) {
      throw new Error('DATABASE_URL is not configured');
    }
    if (!this.#pool) {
      this.#pool = new pg.Pool({
        connectionString: env.databaseUrl,
        ssl: env.databaseUrl.includes('localhost') ? false : { rejectUnauthorized: false },
        max: 5,
      });
    }
    return this.#pool;
  }

  query(text, params) {
    return this.pool.query(text, params);
  }

  async close() {
    await this.#pool?.end();
    this.#pool = null;
  }
}
