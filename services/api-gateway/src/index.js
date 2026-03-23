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
  cors: { origin: config.cors.origin },
});

// Socket.IO instance'ı app'e bağla (route'lardan erişim için)
app.set('io', io);

io.on('connection', (socket) => {
  console.log(`[WS] Client bağlandı: ${socket.id}`);

  socket.on('disconnect', () => {
    console.log(`[WS] Client ayrıldı: ${socket.id}`);
  });
});

// ── Global Middleware ──
app.use(helmet());
app.use(cors({ origin: config.cors.origin }));
app.use(express.json());

// Rate limiting - brute force koruması
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 dakika
  max: 20,
  message: { success: false, message: 'Çok fazla deneme. Lütfen bekleyin.' },
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
    message: `${req.method} ${req.path} bulunamadı.`,
  });
});

// ── Merkezi Error Handler ──
app.use(errorHandler);

// ── Server Başlat ──
server.listen(config.port, async () => {
  console.log('═══════════════════════════════════════');
  console.log(`  WindSentinel API Gateway`);
  console.log(`  Port: ${config.port}`);
  console.log(`  WebSocket: aktif`);
  console.log('═══════════════════════════════════════');

  // RabbitMQ alert consumer başlat (WebSocket push için)
  await startAlertConsumer(io);
});

module.exports = { app, server, io };
