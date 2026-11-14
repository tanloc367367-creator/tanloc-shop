const express = require('express');
const { createClient } = require('@libsql/client');

const app = express();
const SECRET = 'tanloc_shop_secret_2024';

// ĐIỀN THÔNG TIN TURSO CỦA BẠN VÀO ĐÂY
const TURSO_URL = 'libsql://tanlocshop-tanloc.aws-eu-north-1.turso.io';
const TURSO_TOKEN = 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQ2ODM0NDEsImlkIjoiMDFhMWQ5MGEtNDAwMS03N2YwLTg4NjgtNTUxOWRjNzhjYTAwIiwia2lkIjoiY3NTWmk3MUZXdFY5cWZuNHhYWERrOGNoVGxXUW8yN18wTnNqTU55Sjg2TSIsInJpZCI6ImIyZDNiZjVkLThhY2MtNDk0Yi1hNjdlLTJlMTcwOTc2MmViZSJ9.HT2GfKduxxyqbUIgia2pdjP9HsCIXRam8d2rLO6s1zovh6dTYliFnT8OyHBiY62J3HMB2Xc_NaS88QlOSug2CQ'; 

const db = createClient({ 
  url: TURSO_URL, 
  authToken: TURSO_TOKEN,
  syncUrl: TURSO_URL 
});

app.use(express.json());
app.use(express.static('public'));

async function initDB() {
  try {
    await db.execute(`CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, price INTEGER, badge TEXT);`);
    await db.execute(`CREATE TABLE IF NOT EXISTS keys (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, key_value TEXT UNIQUE, sold INTEGER DEFAULT 0, order_id INTEGER);`);
    await db.execute(`CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, amount INTEGER, payment_code TEXT UNIQUE, status TEXT DEFAULT 'pending', created_at TEXT);`);
  } catch (e) { console.error("LỖI DB:", e.message); }
}

db.sync().then(() => initDB()).catch(err => console.error("LỖI SYNC:", err.message));

// ================= API CHO KHÁCH HÀNG =================
app.get('/api/products', async (req, res) => {
  try {
    const rs = await db.execute(`SELECT p.*, (SELECT COUNT(*) FROM keys k WHERE k.product_id=p.id AND k.sold=0) AS stock FROM products p ORDER BY p.id`);
    res.json(rs.rows);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/buy/:productId', async (req, res) => {
  try {
    const productId = +req.params.productId;
    const rsP = await db.execute({ sql: "SELECT * FROM products WHERE id=?", args: [productId] });
    const product = rsP.rows[0];
    if (!product) return res.status(404).json({ error: 'Không có sản phẩm' });

    const payment_code = 'DH' + Date.now().toString().slice(-6);
    const rsO = await db.execute({ sql: "INSERT INTO orders (product_id, amount, payment_code) VALUES (?,?,?)", args: [productId, product.price, payment_code] });
    
    res.json({ ok: true, orderId: rsO.lastInsertRowid, payment_code, amount: product.price, productName: product.name });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ================= API CHO ADMIN =================
app.get('/api/admin/stats', async (req, res) => {
  try {
    const p = await db.execute("SELECT COUNT(*) c FROM products");
    const kA = await db.execute("SELECT COUNT(*) c FROM keys WHERE sold=0");
    const r = await db.execute("SELECT COALESCE(SUM(amount),0) s FROM orders WHERE status='paid'");
    res.json({ products: p.rows[0].c, keysAvailable: kA.rows[0].c, revenue: r.rows[0].s });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/admin/orders', async (req, res) => {
  try {
    const rs = await db.execute(`SELECT o.*, p.name AS product_name, k.key_value FROM orders o JOIN products p ON p.id=o.product_id LEFT JOIN keys k ON k.id=o.key_id ORDER BY o.id DESC LIMIT 100`);
    res.json(rs.rows);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/orders/:id/approve', async (req, res) => {
  try {
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
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/products', async (req, res) => {
  try {
    await db.execute({ sql: "INSERT INTO products (name, description, price, badge) VALUES (?,?,?,?)", args: [req.body.name, req.body.description, req.body.price, req.body.badge] });
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/keys', async (req, res) => {
  try {
    await db.execute({ sql: "INSERT INTO keys (product_id, key_value) VALUES (?,?)", args: [req.body.product_id, req.body.key_value] });
    res.json({ ok: true });
  } catch (e) { res.status(400).json({ error: 'Key đã tồn tại' }); }
});

// ================= CẤU HÌNH CHẠY TRÊN RENDER =================
const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server đang chạy trên cổng ${PORT}`);
});
server.keepAliveTimeout = 120000;
server.headersTimeout = 120000;

module.exports = app;
