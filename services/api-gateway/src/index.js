// ─────────────────────────────────────────
// WindSentinel API Gateway
// Tek giriş noktası: REST + JWT + WebSocket
// ─────────────────────────────────────────

require('dotenv').config();

const express = require('express');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const { Server } = require('socket.io');
const rateLimit = require('express-rate-limit');

const config = require('./config');
const { healthCheck } = require('./db/pool');
const authMiddleware = require('./middleware/auth');
const errorHandler = require('./middleware/errorHandler');
const { startAlertConsumer } = require('./services/alertConsumer');

// Route imports
const authRoutes = require('./routes/auth');
const turbineRoutes = require('./routes/turbines');
const alertRoutes = require('./routes/alerts');

// ── Express App ──
const app = express();
const server = http.createServer(app);

// ── Socket.IO ──
const io = new Server(server, {
  cors: {
    origin: config.cors.origin,
    methods: ['GET', 'POST'],
  },
});

app.set('io', io);

io.on('connection', (socket) => {
  console.log(`[WS] Client connected: ${socket.id}`);
  socket.on('disconnect', () => {
    console.log(`[WS] Client disconnected: ${socket.id}`);
  });
});

// ── Global Middleware ──
app.use(helmet());
app.use(cors({ origin: config.cors.origin }));
app.use(express.json({ limit: '10kb' }));

// Request logging
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const ms = Date.now() - start;
    if (req.path !== '/health') {
      console.log(`[HTTP] ${req.method} ${req.path} ${res.statusCode} ${ms}ms`);
    }
  });
  next();
});

// Rate limiting
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 20,
  message: { success: false, message: 'Too many requests. Please wait.' },
});

// ── Health Check ──
app.get('/health', async (req, res) => {
  const dbHealthy = await healthCheck();
  const status = dbHealthy ? 200 : 503;
  res.status(status).json({
    status: dbHealthy ? 'ok' : 'degraded',
    service: 'api-gateway',
    db: dbHealthy ? 'connected' : 'disconnected',
    uptime: process.uptime(),
  });
});

// ── Public Routes ──
app.use('/auth', authLimiter, authRoutes);

// ── Protected Routes ──
app.use('/api/turbines', authMiddleware, turbineRoutes);
app.use('/api/alerts', authMiddleware, alertRoutes);

// ── 404 Handler ──
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: `${req.method} ${req.path} not found.`,
  });
});

// ── Error Handler ──
app.use(errorHandler);

// ── Server Start ──
server.listen(config.port, async () => {
  console.log('═══════════════════════════════════════');
  console.log('  WindSentinel API Gateway');
  console.log(`  Port: ${config.port}`);
  console.log('  WebSocket: active');
  console.log('═══════════════════════════════════════');

  await startAlertConsumer(io);
});

// ── Graceful Shutdown ──
function shutdown(signal) {
  console.log(`[SHUTDOWN] ${signal} received. Closing server...`);
  server.close(() => {
    console.log('[SHUTDOWN] HTTP server closed.');
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10000);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

module.exports = { app, server, io };
