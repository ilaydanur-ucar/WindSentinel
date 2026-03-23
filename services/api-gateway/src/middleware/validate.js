// ─────────────────────────────────────────
// Input Validation Helpers
// Route başında çağrılır, hatalı veri DB'ye gitmez
// ─────────────────────────────────────────

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 6;

function validateRegister(req, res, next) {
  const { email, password, name } = req.body;

  if (!email || !password || !name) {
    return res.status(400).json({
      success: false,
      message: 'email, password ve name alanları zorunludur.',
    });
  }

  if (typeof email !== 'string' || !EMAIL_REGEX.test(email)) {
    return res.status(400).json({
      success: false,
      message: 'Geçerli bir email adresi giriniz.',
    });
  }

  if (typeof password !== 'string' || password.length < MIN_PASSWORD_LENGTH) {
    return res.status(400).json({
      success: false,
      message: `Şifre en az ${MIN_PASSWORD_LENGTH} karakter olmalıdır.`,
    });
  }

  if (typeof name !== 'string' || name.trim().length === 0) {
    return res.status(400).json({
      success: false,
      message: 'Geçerli bir isim giriniz.',
    });
  }

  next();
}

function validateLogin(req, res, next) {
  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({
      success: false,
      message: 'email ve password alanları zorunludur.',
    });
  }

  next();
}

module.exports = { validateRegister, validateLogin };
