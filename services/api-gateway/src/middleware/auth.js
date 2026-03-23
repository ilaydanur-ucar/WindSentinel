// ─────────────────────────────────────────
// JWT Authentication Middleware
// Protected route'lara uygulanır
// ─────────────────────────────────────────

const jwt = require('jsonwebtoken');
const config = require('../config');

function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      success: false,
      message: 'Token gerekli. Authorization: Bearer <token>',
    });
  }

  const token = authHeader.split(' ')[1];

  try {
    const decoded = jwt.verify(token, config.jwt.secret);
    req.user = {
      id: decoded.id,
      email: decoded.email,
    };
    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({
        success: false,
        message: 'Token süresi dolmuş.',
      });
    }
    return res.status(401).json({
      success: false,
      message: 'Geçersiz token.',
    });
  }
}

module.exports = authMiddleware;
