// ─────────────────────────────────────────
// Turbine Routes - Protected
// GET /turbines, GET /turbines/:id
// ─────────────────────────────────────────

const express = require('express');
const db = require('../db/pool');

const router = express.Router();

// ── GET /api/turbines ──
// Tüm türbinleri listele
router.get('/', async (req, res, next) => {
  try {
    const result = await db.query(
      `SELECT t.id, t.turbine_id, t.asset_id, t.farm_name, t.status,
              COUNT(a.id) FILTER (WHERE a.status = 'active') AS active_alerts
       FROM turbines t
       LEFT JOIN alerts a ON t.turbine_id = a.turbine_id
       GROUP BY t.id
       ORDER BY t.asset_id`
    );

    res.status(200).json({
      success: true,
      data: result.rows,
    });
  } catch (err) {
    next(err);
  }
});

// ── GET /api/turbines/:turbineId ──
// Türbin detay + son alertler
router.get('/:turbineId', async (req, res, next) => {
  try {
    const { turbineId } = req.params;

    // Türbin bilgisi
    const turbineResult = await db.query(
      'SELECT id, turbine_id, asset_id, farm_name, status FROM turbines WHERE turbine_id = $1',
      [turbineId]
    );

    if (turbineResult.rows.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'Türbin bulunamadı.',
      });
    }

    const turbine = turbineResult.rows[0];

    // Son 10 alert (ağır veri dönmemek için limit)
    const alertsResult = await db.query(
      `SELECT id, anomaly_type, anomaly_score, confidence, status, created_at, resolved_at
       FROM alerts
       WHERE turbine_id = $1
       ORDER BY created_at DESC
       LIMIT 10`,
      [turbineId]
    );

    // Özet istatistikler
    const statsResult = await db.query(
      `SELECT
         COUNT(*) FILTER (WHERE status = 'active') AS active_count,
         COUNT(*) FILTER (WHERE status = 'resolved') AS resolved_count,
         COUNT(*) AS total_count
       FROM alerts
       WHERE turbine_id = $1`,
      [turbineId]
    );

    res.status(200).json({
      success: true,
      data: {
        turbine,
        alerts: alertsResult.rows,
        stats: statsResult.rows[0],
      },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
