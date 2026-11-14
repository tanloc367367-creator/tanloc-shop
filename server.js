const express = require('express');
const { createClient } = require('@libsql/client');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const cookieParser = require('cookie-parser');

const app = express();
const SECRET = 'tanloc_shop_secret_2024';

// ĐIỀN THÔNG TIN TURSO CỦA BẠN VÀO ĐÂY
const TURSO_URL = 'libsql://tanlocshop-tanloc.aws-eu-north-1.turso.io';
const TURSO_TOKEN = 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQ2NzA4NTgsImlkIjoiMDFhMWQ5MGEtNDAwMS03N2YwLTg4NjgtNTUxOWRjNzhjYTAwIiwia2lkIjoiY3NTWmk3MUZXdFY5cWZuNHhYWERrOGNoVGxXUW8yN18wTnNqTU55Sjg2TSIsInJpZCI6ImIyZDNiZjVkLThhY2MtNDk0Yi1hNjdlLTJlMTcwOTc2MmViZSJ9.OlkFFwsTFvffweIgfORAflymm1MyALkDXq_C7nYbSTRPXKC8bseEbqS3yVaK11jfGX8XsT48Y0NuttfNhCAIDg'; 

const db = createClient({ url: TURSO_URL, authToken: TURSO_TOKEN });

app.use(express.json());
app.use(cookieParser());
app.use(express.static('public'));

async function initDB() {
  try {
    await db.execute(`CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, email TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user', status TEXT DEFAULT 'active', created_at TEXT);`);
    await db.execute(`CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, price INTEGER, badge TEXT);`);
    await db.execute(`CREATE TABLE IF NOT EXISTS keys (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, key_value TEXT UNIQUE, sold INTEGER DEFAULT 0, order_id INTEGER);`);
    await db.execute(`CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, key_id INTEGER, amount INTEGER, payment_code TEXT UNIQUE, status TEXT DEFAULT 'pending', created_at TEXT);`);
    
    const rs = await db.execute("SELECT id FROM users WHERE role='super'");
    if (rs.rows.length === 0) {
      const hash = bcrypt.hashSync('admin123', 10);
      await db.execute({ sql: "INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)", args: ['admin', 'admin@tanlocshop.com', hash, 'super'] });
    }
  } catch (e) { console.error("LỖI DB:", e.message); }
}
initDB();

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

app.post('/api/register', async (req, res) => {
  try {
    const { username, email, password } = req.body;
    const hash = bcrypt.hashSync(password, 10);
    await db.execute({ sql: "INSERT INTO users (username,email,password) VALUES (?,?,?)", args: [username.trim(), email.trim().toLowerCase(), hash] });
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: 'Lỗi: ' + e.message }); }
});

app.post('/api/login', async (req, res) => {
  try {
    const { username, email, password } = req.body;
    const rs = await db.execute({ sql: "SELECT * FROM users WHERE username=?", args: [username.trim()] });
    const user = rs.rows[0];
    if (!user || user.email !== email || !bcrypt.compareSync(password, user.password)) return res.status(400).json({ error: 'Sai tài khoản hoặc mật khẩu!' });
    if (user.status === 'banned') return res.status(403).json({ error: 'Tài khoản bị khóa' });
    const token = jwt.sign({ id: user.id, username: user.username, role: user.role }, SECRET, { expiresIn: '7d' });
    res.cookie('token', token, { httpOnly: true, maxAge: 7*24*3600*1000 });
    res.json({ ok: true, role: user.role });
  } catch (e) { res.status(500).json({ error: 'Lỗi: ' + e.message }); }
});

app.post('/api/logout', (req, res) => { res.clearCookie('token'); res.json({ ok: true }); });
app.get('/api/me', auth, async (req, res) => {
  const rs = await db.execute({ sql: "SELECT id,username,email,role,status FROM users WHERE id=?", args: [req.user.id] });
  res.json(rs.rows[0]);
});

app.get('/api/products', async (req, res) => {
  const rs = await db.execute(`SELECT p.*, (SELECT COUNT(*) FROM keys k WHERE k.product_id=p.id AND k.sold=0) AS stock FROM products p ORDER BY p.id`);
  res.json(rs.rows);
});

app.post('/api/buy/:productId', auth, async (req, res) => {
  const productId = +req.params.productId;
  const rsP = await db.execute({ sql: "SELECT * FROM products WHERE id=?", args: [productId] });
  const product = rsP.rows[0];
  if (!product) return res.status(404).json({ error: 'Không có sản phẩm' });
  
  const payment_code = 'DH' + Date.now().toString().slice(-6);
  const rsO = await db.execute({ sql: "INSERT INTO orders (user_id, product_id, amount, payment_code, status) VALUES (?,?,?,?, 'pending')", args: [req.user.id, productId, product.price, payment_code] });
  res.json({ ok: true, orderId: rsO.lastInsertRowid, payment_code, amount: product.price, productName: product.name });
});

app.post('/api/order/:orderId/confirm', auth, async (req, res) => {
  await db.execute({ sql: "UPDATE orders SET status='waiting' WHERE id=? AND user_id=?", args: [req.params.orderId, req.user.id] });
  res.json({ ok: true });
});

app.get('/api/admin/stats', auth, adminOnly, async (req, res) => {
  const u = await db.execute("SELECT COUNT(*) c FROM users WHERE role='user'");
  const p = await db.execute("SELECT COUNT(*) c FROM products");
  const kA = await db.execute("SELECT COUNT(*) c FROM keys WHERE sold=0");
  const r = await db.execute("SELECT COALESCE(SUM(amount),0) s FROM orders WHERE status='paid'");
  res.json({ users: u.rows[0].c, products: p.rows[0].c, keysAvailable: kA.rows[0].c, revenue: r.rows[0].s });
});

app.get('/api/admin/orders', auth, adminOnly, async (req, res) => {
  const rs = await db.execute(`SELECT o.*, u.username, p.name AS product_name, k.key_value FROM orders o JOIN users u ON u.id=o.user_id JOIN products p ON p.id=o.product_id LEFT JOIN keys k ON k.id=o.key_id ORDER BY CASE o.status WHEN 'waiting' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, o.id DESC LIMIT 100`);
  res.json(rs.rows);
});

app.post('/api/admin/orders/:id/approve', auth, adminOnly, async (req, res) => {
  const orderId = +req.params.id;
  const rsO = await db.execute({ sql: "SELECT * FROM orders WHERE id=?", args: [orderId] });
  const order = rsO.rows[0];
  if (!order || order.status === 'paid') return res.status(400).json({ error: 'Đơn không hợp lệ' });
  const rsK = await db.execute({ sql: "SELECT * FROM keys WHERE product_id=? AND sold=0 LIMIT 1", args: [order.product_id] });
  const key = rsK.rows[0];
  if (!key) return res.status(400).json({ error: 'Hết key!' });
  await db.execute({ sql: "UPDATE keys SET sold=1, order_id=? WHERE id=?", args: [orderId, key.id] });
  await db.execute({ sql: "UPDATE orders SET status='paid', key_id=? WHERE id=?", args: [key.id, orderId] });
  res.json({ ok: true, key: key.key_value });
});

app.get('/api/admin/users', auth, adminOnly, async (req, res) => {
  const rs = await db.execute("SELECT id, username, email, role, status FROM users ORDER BY id");
  res.json(rs.rows);
});

app.post('/api/admin/grant/:id', auth, adminOnly, async (req, res) => {
  if (req.user.role !== 'super') return res.status(403).json({ error: 'Chỉ Admin tổng' });
  await db.execute({ sql: "UPDATE users SET role=? WHERE id=?", args: [req.body.role, req.params.id] });
  res.json({ ok: true });
});

app.post('/api/admin/keys', auth, adminOnly, async (req, res) => {
  try {
    await db.execute({ sql: "INSERT INTO keys (product_id, key_value) VALUES (?,?)", args: [req.body.product_id, req.body.key_value] });
    res.json({ ok: true });
  } catch { res.status(400).json({ error: 'Key đã tồn tại' }); }
});

app.post('/api/admin/products', auth, adminOnly, async (req, res) => {
  await db.execute({ sql: "INSERT INTO products (name, description, price, badge) VALUES (?,?,?,?)", args: [req.body.name, req.body.description, req.body.price, req.body.badge] });
  res.json({ ok: true });
});

app.get('/api/admin/keys/:productId', auth, adminOnly, async (req, res) => {
  const rs = await db.execute({ sql: "SELECT * FROM keys WHERE product_id=? ORDER BY sold, id DESC", args: [req.params.productId] });
  res.json(rs.rows);
});

module.exports = app;
