import { randomUUID } from 'node:crypto';
import { Database } from '../db/Database.js';

const toUser = (row) =>
  row && { id: row.id, fullName: row.full_name, email: row.email, passwordHash: row.password_hash, createdAt: row.created_at };

export class PostgresUserRepository {
  constructor(db = Database.getInstance()) {
    this.db = db;
  }

  async findByEmail(email) {
    const { rows } = await this.db.query('SELECT * FROM users WHERE email = $1', [email]);
    return toUser(rows[0]);
  }

  async findById(id) {
    const { rows } = await this.db.query('SELECT * FROM users WHERE id = $1', [id]);
    return toUser(rows[0]);
  }

  async create({ fullName, email, passwordHash }) {
    const { rows } = await this.db.query(
      'INSERT INTO users (full_name, email, password_hash) VALUES ($1, $2, $3) RETURNING *',
      [fullName, email, passwordHash],
    );
    return toUser(rows[0]);
  }
}

// Para desarrollo local y tests cuando no hay DATABASE_URL.
export class InMemoryUserRepository {
  #users = new Map();

  async findByEmail(email) {
    return [...this.#users.values()].find((u) => u.email === email);
  }

  async findById(id) {
    return this.#users.get(id);
  }

  async create({ fullName, email, passwordHash }) {
    const user = { id: randomUUID(), fullName, email, passwordHash, createdAt: new Date() };
    this.#users.set(user.id, user);
    return user;
  }
}

export function createUserRepository() {
  return Database.getInstance().isConfigured ? new PostgresUserRepository() : new InMemoryUserRepository();
}
