import { verifyToken } from '../auth/TokenService.js';

export function requireAuth(req, res, next) {
  const [scheme, token] = (req.get('authorization') ?? '').split(' ');
  if (scheme !== 'Bearer' || !token) {
    return res.status(401).json({ error: 'Inicia sesión para continuar' });
  }
  try {
    req.user = { id: verifyToken(token).sub };
    next();
  } catch {
    res.status(401).json({ error: 'Tu sesión expiró, vuelve a iniciar sesión' });
  }
}
