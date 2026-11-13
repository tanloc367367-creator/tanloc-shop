const express = require('express');
const { createClient } = require('@libsql/client');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const cookieParser = require('cookie-parser');
const TelegramBot = require('node-telegram-bot-api');

const app = express();
const SECRET = 'tanloc_shop_secret_2024_doi_thanh_chuoi_that_dai';

// CẤU HÌNH TELEGRAM VÀ BANK (Bạn nhớ sửa lại thông tin của bạn)
const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN || 'DAN_TOKEN_BOT_CUA_BAN';
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID || 'DAN_CHAT_ID_CUA_BAN';

const BANK = {
  bankId: '970422', account: '0123456789', name: 'NGUYEN VAN A', bankName: 'MB Bank'
};

// KẾT NỐI TURSO DATABASE
const db = createClient({
  url: process.env.TURSO_DATABASE_URL,
  authToken: process.env.TURSO_AUTH_TOKEN,
});

app.use(express.json());
app.use(cookieParser());
app.use(express.static('public'));

// HÀM KHỞI TẠO DATABASE TỰ ĐỘNG
async function initDB() {
  await db.execute(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, email TEXT UNIQUE,
      password TEXT, role TEXT DEFAULT 'user', balance INTEGER DEFAULT 0, status TEXT DEFAULT 'active', created_at TEXT
    );
  `);
  await db.execute(`
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, price INTEGER, badge TEXT
    );
  `);
  await db.execute(`
    CREATE TABLE IF NOT EXISTS keys (
      id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, key_value TEXT UNIQUE, sold INTEGER DEFAULT 0, order_id INTEGER
    );
  `);
  await db.execute(`
    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, key_id INTEGER,
      amount INTEGER, payment_code TEXT UNIQUE, status TEXT DEFAULT 'pending', created_at TEXT, paid_at TEXT
    );
  `);

  // Tạo Admin mặc định
  const rs = await db.execute("SELECT id FROM users WHERE role='super'");
  if (rs.rows.length === 0) {
    const hash = bcrypt.hashSync('admin123', 10);
    await db.execute({
      sql: "INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
      args: ['admin', 'admin@tanlocshop.com', hash, 'super']
    });
    
    // Tạo sản phẩm mẫu
    await db.execute("INSERT INTO products (name,description,price,badge) VALUES ('Key 1H (Lẻ)', 'Key 1 giờ', 900, 'LẺ')");
    await db.execute("INSERT INTO products (name,description,price,badge) VALUES ('Key 1H (SLL)', 'Key số lượng lớn', 700, 'SLL')");
  }
}
initDB().catch(console.error);

// HÀM GỬI TELEGRAM
async function notifyAdmin(message) {
  try {
    const bot = new TelegramBot(TELEGRAM_TOKEN);
    await bot.sendMessage(TELEGRAM_CHAT_ID, message, { parse_mode: 'HTML' });
  } catch (e) { console.log('Lỗi gửi Telegram:', e.message); }
}

// MIDDLEWARE
async function auth(req, res, next) {
  const token = req.cookies.token;
  if (!token) return res.status(401).json({ error: 'Chưa đăng nhập' });
  try {
    req.user = jwt.verify(token, SECRET);
    const rs = await db.execute({ sql: "SELECT status FROM users WHERE id=?", args: [req.user.id] });
    if (rs.rows.length === 0 || rs.rows[0].status === 'banned') return res.status(403).json({ error: 'Tài khoản bị khóa' });
    next();
  } catch { res.status(401).json({ error: 'Lỗi xác thực' }); }
}

function adminOnly(req, res, next) {
  if (!['admin','super'].includes(req.user.role)) return res.status(403).json({ error: 'Cần quyền admin' });
  next();
}

// ================= API AUTH =================
app.post('/api/register', async (req, res) => {
  const { username, email, password } = req.body;
  if (!username || !email || !password) return res.status(400).json({ error: 'Nhập thiếu thông tin' });
  try {
    const hash = bcrypt.hashSync(password, 10);
    await db.execute({
      sql: "INSERT INTO users (username,email,password) VALUES (?,?,?)",
      args: [username.trim(), email.trim().toLowerCase(), hash]
    });
    res.json({ ok: true });
  } catch (e) { res.status(400).json({ error: 'Tên hoặc Email đã tồn tại' }); }
});

app.post('/api/login', async (req, res) => {
  const { username, email, password } = req.body;
  const rs = await db.execute({ sql: "SELECT * FROM users WHERE username=?", args: [username] });
  const user = rs.rows[0];
  if (!user || user.email !== email || !bcrypt.compareSync(password, user.password)) {
    return res.status(400).json({ error: 'Email hoặc mật khẩu sai!' });
  }
  if (user.status === 'banned') return res.status(403).json({ error: 'Tài khoản bị khóa' });
  
  const token = jwt.sign({ id: user.id, username: user.username, role: user.role }, SECRET, { expiresIn: '7d' });
  res.cookie('token', token, { httpOnly: true, maxAge: 7*24*3600*1000 });
  res.json({ ok: true, role: user.role });
});

app.post('/api/logout', (req, res) => { res.clearCookie('token'); res.json({ ok: true }); });
app.get('/api/me', auth, async (req, res) => {
  const rs = await db.execute({ sql: "SELECT id,username,email,role,balance,status FROM users WHERE id=?", args: [req.user.id] });
  res.json(rs.rows[0]);
});

// ================= API SẢN PHẨM =================
app.get('/api/products', async (req, res) => {
  const rs = await db.execute(`
    SELECT p.*, (SELECT COUNT(*) FROM keys k WHERE k.product_id=p.id AND k.sold=0) AS stock
    FROM products p ORDER BY p.id
  `);
  res.json(rs.rows);
});

// ================= API MUA HÀNG =================
app.post('/api/buy/:productId', auth, async (req, res) => {
  const productId = +req.params.productId;
  const rsP = await db.execute({ sql: "SELECT * FROM products WHERE id=?", args: [productId] });
  const product = rsP.rows[0];
  if (!product) return res.status(404).json({ error: 'Không có sản phẩm' });

  const payment_code = 'DH' + Date.now().toString().slice(-6) + Math.floor(Math.random()*90+10);
  const rsO = await db.execute({
    sql: "INSERT INTO orders (user_id, product_id, amount, payment_code, status) VALUES (?,?,?,?, 'pending')",
    args: [req.user.id, productId, product.price, payment_code]
  });

  notifyAdmin(`🛒 <b>ĐƠN MỚI #${rsO.lastInsertRowid}</b>\nMã CK: <code>${payment_code}</code>`);
  res.json({ ok: true, orderId: rsO.lastInsertRowid, payment_code, amount: product.price, productName: product.name });
});

app.post('/api/order/:orderId/confirm', auth, async (req, res) => {
  await db.execute({ sql: "UPDATE orders SET status='waiting' WHERE id=? AND user_id=?", args: [req.params.orderId, req.user.id] });
  notifyAdmin(`💰 <b>KHÁCH ĐÃ XÁC NHẬN CK ĐƠN #${req.params.orderId}</b>\n👉 Vào Admin duyệt!`);
  res.json({ ok: true });
});

app.get('/api/my-orders', auth, async (req, res) => {
  const rs = await db.execute({
    sql: `SELECT o.id, o.amount, o.status, o.created_at, o.payment_code, p.name AS product_name, k.key_value
          FROM orders o JOIN products p ON p.id=o.product_id LEFT JOIN keys k ON k.id=o.key_id
          WHERE o.user_id=? ORDER BY o.id DESC`,
    args: [req.user.id]
  });
  res.json(rs.rows);
});

// ================= API ADMIN =================
app.get('/api/admin/stats', auth, adminOnly, async (req, res) => {
  const u = await db.execute("SELECT COUNT(*) c FROM users WHERE role='user'");
  const p = await db.execute("SELECT COUNT(*) c FROM products");
  const kA = await db.execute("SELECT COUNT(*) c FROM keys WHERE sold=0");
  const o = await db.execute("SELECT COUNT(*) c FROM orders");
  const r = await db.execute("SELECT COALESCE(SUM(amount),0) s FROM orders WHERE status='paid'");
  res.json({ users: u.rows[0].c, products: p.rows[0].c, keysAvailable: kA.rows[0].c, orders: o.rows[0].c, revenue: r.rows[0].s });
});

app.get('/api/admin/orders', auth, adminOnly, async (req, res) => {
  const rs = await db.execute(`
    SELECT o.*, u.username, u.email, p.name AS product_name, k.key_value
    FROM orders o JOIN users u ON u.id=o.user_id JOIN products p ON p.id=o.product_id LEFT JOIN keys k ON k.id=o.key_id
    ORDER BY CASE o.status WHEN 'waiting' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, o.id DESC LIMIT 100
  `);
  res.json(rs.rows);
});

app.post('/api/admin/orders/:id/approve', auth, adminOnly, async (req, res) => {
  const orderId = +req.params.id;
  const rsO = await db.execute({ sql: "SELECT * FROM orders WHERE id=?", args: [orderId] });
  const order = rsO.rows[0];
  if (!order || order.status === 'paid') return res.status(400).json({ error: 'Đơn không hợp lệ' });

  const rsK = await db.execute({ sql: "SELECT * FROM keys WHERE product_id=? AND sold=0 LIMIT 1", args: [order.product_id] });
  const key = rsK.rows[0];
  if (!key) return res.status(400).json({ error: 'Hết key trong kho!' });

  await db.execute({ sql: "UPDATE keys SET sold=1, order_id=? WHERE id=?", args: [orderId, key.id] });
  await db.execute({ sql: "UPDATE orders SET status='paid', key_id=?, paid_at=CURRENT_TIMESTAMP WHERE id=?", args: [key.id, orderId] });

  res.json({ ok: true, key: key.key_value });
});

app.post('/api/admin/orders/:id/cancel', auth, adminOnly, async (req, res) => {
  await db.execute({ sql: "UPDATE orders SET status='cancelled' WHERE id=?", args: [req.params.id] });
  res.json({ ok: true });
});

app.get('/api/admin/users', auth, adminOnly, async (req, res) => {
  const rs = await db.execute("SELECT id, username, email, role, status, created_at FROM users ORDER BY id");
  res.json(rs.rows);
});

app.post('/api/admin/grant/:id', auth, adminOnly, async (req, res) => {
  if (req.user.role !== 'super') return res.status(403).json({ error: 'Chỉ Admin tổng' });
  await db.execute({ sql: "UPDATE users SET role=? WHERE id=?", args: [req.body.role, req.params.id] });
  res.json({ ok: true });
});

app.post('/api/admin/ban/:id', auth, adminOnly, async (req, res) => {
  const rs = await db.execute({ sql: "SELECT role, status FROM users WHERE id=?", args: [req.params.id] });
  const u = rs.rows[0];
  if (u.role === 'super') return res.status(400).json({ error: 'Không thể khóa Admin tổng' });
  const newStatus = u.status === 'banned' ? 'active' : 'banned';
  await db.execute({ sql: "UPDATE users SET status=? WHERE id=?", args: [newStatus, req.params.id] });
  res.json({ ok: true });
});

app.post('/api/admin/keys', auth, adminOnly, async (req, res) => {
  const { product_id, key_value } = req.body;
  try {
    await db.execute({ sql: "INSERT INTO keys (product_id, key_value) VALUES (?,?)", args: [product_id, key_value] });
    res.json({ ok: true });
  } catch { res.status(400).json({ error: 'Key đã tồn tại' }); }
});

module.exports = app;
