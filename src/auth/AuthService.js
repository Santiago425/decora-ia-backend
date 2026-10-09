import { hashPassword, verifyPassword } from './PasswordHasher.js';
import { signToken } from './TokenService.js';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const DUMMY_HASH = await hashPassword('timing-safe-placeholder');

export class AuthError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

const publicUser = ({ id, fullName, email, createdAt }) => ({ id, fullName, email, createdAt });

function validateCredentials(email, password) {
  if (typeof email !== 'string' || email.length > 160 || !EMAIL.test(email)) {
    throw new AuthError(400, 'Ingresa un correo válido');
  }
  if (typeof password !== 'string' || password.length < 8 || password.length > 128) {
    throw new AuthError(400, 'La contraseña debe tener entre 8 y 128 caracteres');
  }
}

export class AuthService {
  constructor(users) {
    this.users = users;
  }

  async register({ fullName, email, password }) {
    const name = typeof fullName === 'string' ? fullName.trim() : '';
    const normalized = typeof email === 'string' ? email.trim().toLowerCase() : email;
    if (name.length < 2 || name.length > 120) throw new AuthError(400, 'Ingresa tu nombre (2 a 120 caracteres)');
    validateCredentials(normalized, password);
    if (!/[a-zA-Z]/.test(password) || !/\d/.test(password)) {
      throw new AuthError(400, 'La contraseña debe tener al menos una letra y un número');
    }
    if (await this.users.findByEmail(normalized)) {
      throw new AuthError(409, 'Ya existe una cuenta con ese correo');
    }
    let user;
    try {
      user = await this.users.create({ fullName: name, email: normalized, passwordHash: await hashPassword(password) });
    } catch (err) {
      if (err.code === '23505') throw new AuthError(409, 'Ya existe una cuenta con ese correo');
      throw err;
    }
    return { token: signToken(user), user: publicUser(user) };
  }

  async login({ email, password }) {
    const normalized = typeof email === 'string' ? email.trim().toLowerCase() : email;
    validateCredentials(normalized, password);
    const user = await this.users.findByEmail(normalized);
    const valid = await verifyPassword(password, user?.passwordHash ?? DUMMY_HASH);
    if (!user || !valid) throw new AuthError(401, 'Correo o contraseña incorrectos');
    return { token: signToken(user), user: publicUser(user) };
  }

  async me(userId) {
    const user = await this.users.findById(userId);
    if (!user) throw new AuthError(401, 'Sesión no válida');
    return publicUser(user);
  }
}
