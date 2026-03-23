// ─────────────────────────────────────────
// Merkezi Error Handler Middleware
// Tüm hataları yakalar, tutarlı format döner
// ─────────────────────────────────────────

function errorHandler(err, req, res, _next) {
  console.error(`[ERROR] ${req.method} ${req.path} →`, err.message);

  // Bilinen hata tipleri
  if (err.status) {
    return res.status(err.status).json({
      success: false,
      message: err.message,
    });
  }

  // PostgreSQL unique violation
  if (err.code === '23505') {
    return res.status(409).json({
      success: false,
      message: 'Bu kayıt zaten mevcut.',
    });
  }

  // PostgreSQL foreign key violation
  if (err.code === '23503') {
    return res.status(400).json({
      success: false,
      message: 'İlişkili kayıt bulunamadı.',
    });
  }

  // Genel sunucu hatası - detay kullanıcıya gitmez
  res.status(500).json({
    success: false,
    message: 'Sunucu hatası oluştu.',
  });
}

module.exports = errorHandler;
