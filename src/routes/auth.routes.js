import { Router } from 'express';
import { AuthError, AuthService } from '../auth/AuthService.js';
import { createUserRepository } from '../users/UserRepository.js';
import { requireAuth } from '../middleware/auth.js';
import { authLimiter } from '../middleware/security.js';

export function createAuthRouter(service = new AuthService(createUserRepository())) {
  const router = Router();
  const limiter = authLimiter();

  const handle = (action) => async (req, res, next) => {
    try {
      await action(req, res);
    } catch (err) {
      if (err instanceof AuthError) return res.status(err.status).json({ error: err.message });
      next(err);
    }
  };

  router.post('/auth/register', limiter, handle(async (req, res) => {
    res.status(201).json(await service.register(req.body ?? {}));
  }));

  router.post('/auth/login', limiter, handle(async (req, res) => {
    res.json(await service.login(req.body ?? {}));
  }));

  router.get('/auth/me', requireAuth, handle(async (req, res) => {
    res.json({ user: await service.me(req.user.id) });
  }));

  return router;
}
