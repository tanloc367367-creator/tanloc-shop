const TelegramBot = require('node-telegram-bot-api');
const { createClient } = require('@libsql/client');

const db = createClient({
  url: process.env.TURSO_DATABASE_URL,
  authToken: process.env.TURSO_AUTH_TOKEN,
});

const bot = new TelegramBot(process.env.TELEGRAM_TOKEN);

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405 };
  
  try {
    const update = JSON.parse(event.body);
    const msg = update.message;
    
    if (msg && msg.text) {
      const chatId = msg.chat.id.toString();
      const text = msg.text.trim().toLowerCase();
      const args = text.split(/\s+/);
      const cmd = args[0];
      const param = args[1];

      if (chatId !== process.env.TELEGRAM_CHAT_ID) return { statusCode: 200 };

      if (cmd === 'don' || cmd === 'ds') {
        const rs = await db.execute("SELECT o.id, o.payment_code, o.amount, u.username FROM orders o JOIN users u ON u.id=o.user_id WHERE o.status='waiting'");
        if (rs.rows.length === 0) {
          await bot.sendMessage(chatId, '📭 Không có đơn chờ duyệt.');
        } else {
          const list = rs.rows.map(o => `#${o.id} - ${o.amount}đ - ${o.username} (${o.payment_code})`).join('\n');
          await bot.sendMessage(chatId, `🔄 ĐƠN CHỜ DUYỆT:\n\n${list}\n\n👉 duyet <id> để duyệt`);
        }
      } 
      else if (cmd === 'duyet' && param) {
        const orderId = parseInt(param);
        const rsO = await db.execute({ sql: "SELECT * FROM orders WHERE id=?", args: [orderId] });
        const order = rsO.rows[0];
        
        if (order && order.status !== 'paid') {
          const rsK = await db.execute({ sql: "SELECT * FROM keys WHERE product_id=? AND sold=0 LIMIT 1", args: [order.product_id] });
          const key = rsK.rows[0];
          if (key) {
            await db.execute({ sql: "UPDATE keys SET sold=1, order_id=? WHERE id=?", args: [orderId, key.id] });
            await db.execute({ sql: "UPDATE orders SET status='paid', key_id=?, paid_at=CURRENT_TIMESTAMP WHERE id=?", args: [key.id, orderId] });
            await bot.sendMessage(chatId, `✅ Đã duyệt đơn #${orderId}. Key: ${key.key_value}`);
          } else {
            await bot.sendMessage(chatId, `❌ Hết key trong kho!`);
          }
        } else {
          await bot.sendMessage(chatId, `⚠️ Đơn không hợp lệ hoặc đã duyệt.`);
        }
      }
    }
  } catch (e) {
    console.error(e);
  }
  
  return { statusCode: 200, body: 'OK' };
};
