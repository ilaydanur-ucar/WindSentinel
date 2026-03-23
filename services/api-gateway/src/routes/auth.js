// ─────────────────────────────────────────
// Auth Routes - Register & Login
// Public endpoints, auth middleware yok
// ─────────────────────────────────────────

const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const config = require('../config');
const db = require('../db/pool');
const { validateRegister, validateLogin } = require('../middleware/validate');

const router = express.Router();

// ── POST /auth/register ──
router.post('/register', validateRegister, async (req, res, next) => {
  try {
    const { email, password, name } = req.body;

    // Email zaten kayıtlı mı?
    const existing = await db.query(
      'SELECT id FROM users WHERE email = $1',
      [email]
    );

    if (existing.rows.length > 0) {
      return res.status(409).json({
        success: false,
        message: 'Bu email adresi zaten kayıtlı.',
      });
    }

    // Şifreyi hashle (bcrypt)
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    // Kullanıcıyı oluştur
    const result = await db.query(
      'INSERT INTO users (email, password, name) VALUES ($1, $2, $3) RETURNING id, email, name, created_at',
      [email, hashedPassword, name]
    );

    const user = result.rows[0];

    // JWT token üret (minimal payload: id, email)
    const token = jwt.sign(
      { id: user.id, email: user.email },
      config.jwt.secret,
      { expiresIn: config.jwt.expiresIn }
    );

    console.log(`[AUTH] Yeni kullanıcı kayıt: ${user.email}`);

    res.status(201).json({
      success: true,
      data: {
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
        },
        token,
      },
    });
  } catch (err) {
    next(err);
  }
});

// ── POST /auth/login ──
router.post('/login', validateLogin, async (req, res, next) => {
  try {
    const { email, password } = req.body;

    // Kullanıcıyı bul
    const result = await db.query(
      'SELECT id, email, name, password FROM users WHERE email = $1',
      [email]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({
        success: false,
        message: 'Email veya şifre hatalı.',
      });
    }

    const user = result.rows[0];

    // Şifre doğrulama
    const isValid = await bcrypt.compare(password, user.password);
    if (!isValid) {
      return res.status(401).json({
        success: false,
        message: 'Email veya şifre hatalı.',
      });
    }

    // JWT token üret
    const token = jwt.sign(
      { id: user.id, email: user.email },
      config.jwt.secret,
      { expiresIn: config.jwt.expiresIn }
    );

    console.log(`[AUTH] Giriş başarılı: ${user.email}`);

    res.status(200).json({
      success: true,
      data: {
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
        },
        token,
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
