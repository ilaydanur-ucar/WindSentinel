// ─────────────────────────────────────────
// RabbitMQ Alert Consumer
// Notification Service'den gelen alert event'lerini
// Socket.IO ile client'lara push eder
// ─────────────────────────────────────────

const amqplib = require('amqplib');
const config = require('../config');

const EXCHANGE = 'wind.events';
const ROUTING_KEY = 'alert.notify';
const QUEUE = 'alert.notify';

/**
 * RabbitMQ'dan alert bildirimleri dinleyip Socket.IO'ya push eden consumer.
 * Retry mantığı ile bağlantı koparsa tekrar dener.
 */
async function startAlertConsumer(io) {
  const connect = async () => {
    try {
      const connection = await amqplib.connect(config.rabbitmq.url);
      const channel = await connection.createChannel();

      // Exchange ve queue (definitions.json'da tanımlı, TTL parametreleri eşleşmeli)
      await channel.assertExchange(EXCHANGE, 'topic', { durable: true });
      await channel.assertQueue(QUEUE, {
        durable: true,
        arguments: { 'x-message-ttl': 86400000 },
      });
      await channel.bindQueue(QUEUE, EXCHANGE, ROUTING_KEY);

      await channel.prefetch(10);

      console.log(`[WS-CONSUMER] alert.notify kuyruğu dinleniyor...`);

      channel.consume(QUEUE, (msg) => {
        if (!msg) return;

        try {
          const alert = JSON.parse(msg.content.toString());

          // Socket.IO ile tüm bağlı client'lara push
          io.emit('new_alert', alert);

          console.log(`[WS-CONSUMER] Alert #${alert.id} → WebSocket push yapıldı (${alert.turbine_id})`);

          channel.ack(msg);
        } catch (err) {
          console.error('[WS-CONSUMER] Mesaj işleme hatası:', err.message);
          channel.nack(msg, false, false);
        }
      });

      // Bağlantı kapanırsa tekrar bağlan
      connection.on('close', () => {
        console.warn('[WS-CONSUMER] RabbitMQ bağlantısı kapandı, 5sn sonra tekrar denenecek...');
        setTimeout(connect, 5000);
      });

      connection.on('error', (err) => {
        console.error('[WS-CONSUMER] RabbitMQ bağlantı hatası:', err.message);
      });

    } catch (err) {
      console.error('[WS-CONSUMER] RabbitMQ bağlantı kurulamadı, 5sn sonra tekrar denenecek:', err.message);
      setTimeout(connect, 5000);
    }
  };

  await connect();
}

module.exports = { startAlertConsumer };
