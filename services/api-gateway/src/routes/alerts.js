// ─────────────────────────────────────────
// Alert Routes - Protected
// GET /alerts, GET /alerts/stats, GET /alerts/:id, PATCH /alerts/:id/resolve
// ─────────────────────────────────────────

const express = require('express');
const db = require('../db/pool');

const router = express.Router();

// ── GET /api/alerts ──
// Alertleri listele (filtre + pagination destekli)
router.get('/', async (req, res, next) => {
  try {
    const {
      status,
      turbine_id,
      limit = 20,
      offset = 0,
      sort = 'created_at_desc',
    } = req.query;

    // Güvenli limit (max 100)
    const safeLimit = Math.min(parseInt(limit, 10) || 20, 100);
    const safeOffset = parseInt(offset, 10) || 0;

    // Dinamik WHERE koşulları (parametreli query)
    const conditions = [];
    const params = [];
    let paramIndex = 1;

    if (status) {
      conditions.push(`a.status = $${paramIndex++}`);
      params.push(status);
    }

    if (turbine_id) {
      conditions.push(`a.turbine_id = $${paramIndex++}`);
      params.push(turbine_id);
    }

    const whereClause = conditions.length > 0
      ? `WHERE ${conditions.join(' AND ')}`
      : '';

    // Sort (güvenli whitelist)
    const sortMap = {
      created_at_desc: 'a.created_at DESC',
      created_at_asc: 'a.created_at ASC',
      anomaly_score_desc: 'a.anomaly_score DESC',
      anomaly_score_asc: 'a.anomaly_score ASC',
    };
    const orderBy = sortMap[sort] || 'a.created_at DESC';

    // Ana sorgu
    const result = await db.query(
      `SELECT a.id, a.turbine_id, a.asset_id, a.anomaly_type, a.anomaly_score,
              a.confidence, a.status, a.created_at, a.resolved_at
       FROM alerts a
       ${whereClause}
       ORDER BY ${orderBy}
       LIMIT $${paramIndex++} OFFSET $${paramIndex++}`,
      [...params, safeLimit, safeOffset]
    );

    // Toplam kayıt sayısı (pagination için)
    const countResult = await db.query(
      `SELECT COUNT(*) AS total FROM alerts a ${whereClause}`,
      params
    );

    res.status(200).json({
      success: true,
      data: result.rows,
      pagination: {
        total: parseInt(countResult.rows[0].total, 10),
        limit: safeLimit,
        offset: safeOffset,
      },
    });
  } catch (err) {
    next(err);
  }
});

// ── GET /api/alerts/stats ──
// Dashboard istatistikleri
router.get('/stats', async (req, res, next) => {
  try {
    const result = await db.query(`
      SELECT
        COUNT(*) FILTER (WHERE status = 'active') AS active_alerts,
        COUNT(*) FILTER (WHERE status = 'resolved') AS resolved_alerts,
        COUNT(*) AS total_alerts,
        COUNT(DISTINCT turbine_id) FILTER (WHERE status = 'active') AS affected_turbines
      FROM alerts
    `);

    res.status(200).json({
      success: true,
      data: result.rows[0],
    });
  } catch (err) {
    next(err);
  }
});

// ── GET /api/alerts/:id ──
// Tek alert detayı
router.get('/:id', async (req, res, next) => {
  try {
    const { id } = req.params;

    const result = await db.query(
      `SELECT a.id, a.turbine_id, a.asset_id, a.anomaly_type, a.anomaly_score,
              a.confidence, a.status, a.created_at, a.resolved_at
       FROM alerts a
       WHERE a.id = $1`,
      [id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'Alert bulunamadı.',
      });
    }

    res.status(200).json({
      success: true,
      data: result.rows[0],
    });
  } catch (err) {
    next(err);
  }
});

// ── PATCH /api/alerts/:id/resolve ──
// Alert'i çözüldü olarak işaretle (idempotent)
router.patch('/:id/resolve', async (req, res, next) => {
  try {
    const { id } = req.params;

    // Önce alert var mı ve durumu ne?
    const existing = await db.query(
      'SELECT id, status FROM alerts WHERE id = $1',
      [id]
    );

    if (existing.rows.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'Alert bulunamadı.',
      });
    }

    // Zaten resolved ise açık mesajla bildir
    if (existing.rows[0].status === 'resolved') {
      return res.status(409).json({
        success: false,
        message: 'Bu alert zaten çözülmüş.',
      });
    }

    // Resolve et (resolved_by: JWT'den gelen kullanıcı id'si)
    const result = await db.query(
      `UPDATE alerts
       SET status = 'resolved', resolved_at = NOW(), resolved_by = $2
       WHERE id = $1
       RETURNING id, turbine_id, asset_id, anomaly_type, anomaly_score, confidence, status, created_at, resolved_at, resolved_by`,
      [id, req.user.id]
    );

    const resolvedAlert = result.rows[0];

    console.log(`[ALERT] Resolved: #${id} (${resolvedAlert.turbine_id})`);

    // WebSocket event - Socket.IO instance varsa yayınla
    const io = req.app.get('io');
    if (io) {
      io.emit('alert_resolved', {
        id: resolvedAlert.id,
        turbine_id: resolvedAlert.turbine_id,
        status: resolvedAlert.status,
        resolved_at: resolvedAlert.resolved_at,
      });
    }

    res.status(200).json({
      success: true,
      data: resolvedAlert,
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
