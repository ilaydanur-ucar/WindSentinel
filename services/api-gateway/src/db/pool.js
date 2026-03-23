// ─────────────────────────────────────────
// PostgreSQL Connection Pool
// Tek pool, tüm servis paylaşır
// ─────────────────────────────────────────

const { Pool } = require('pg');
const config = require('../config');

const pool = new Pool(config.db);

// Bağlantı başarılı mı kontrol et
pool.on('connect', () => {
  console.log('[DB] PostgreSQL bağlantısı kuruldu.');
});

pool.on('error', (err) => {
  console.error('[DB] PostgreSQL bağlantı hatası:', err.message);
});

/**
 * Parametreli query helper
 * SQL injection koruması - her zaman parametre kullan
 */
async function query(text, params) {
  const start = Date.now();
  try {
    const result = await pool.query(text, params);
    const duration = Date.now() - start;
    console.log(`[DB] Query executed in ${duration}ms | rows: ${result.rowCount}`);
    return result;
  } catch (err) {
    console.error(`[DB] Query error: ${err.message}`);
    throw err;
  }
}

/**
 * Health check - DB bağlantısı canlı mı?
 */
async function healthCheck() {
  try {
    await pool.query('SELECT 1');
    return true;
  } catch {
    return false;
  }
}

module.exports = { pool, query, healthCheck };
