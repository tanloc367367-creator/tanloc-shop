// Ép Node.js dùng DNS của Google để sửa lỗi querySrv ENOTFOUND trên Render
const dns = require('dns');
dns.setServers(['8.8.8.8', '8.8.4.4']);

const express = require('express');
const { MongoClient, ObjectId } = require('mongodb');

const app = express();
app.use(express.json());
app.use(express.static('public'));

// ĐIỀN LINK MONGODB CỦA BẠN VÀO ĐÂY
const MONGO_URI = 'mongodb://tanloc367367_db_user:tuaYwBONHrrunVef@ac-huokco0-shard-00-00.oomiabj.mongodb.net:27017,ac-huokco0-shard-00-01.oomiabj.mongodb.net:27017,ac-huokco0-shard-00-02.oomiabj.mongodb.net:27017/?ssl=true&replicaSet=atlas-sin0iu-shard-0&authSource=admin'; 

const client = new MongoClient(MONGO_URI);
let db;

// Kết nối Database
async function connectDB() {
  try {
    await client.connect();
    db = client.db('tanloc_shop');
    console.log('✅ Đã kết nối MongoDB thành công');
  } catch (e) { 
    console.error('❌ LỖI KẾT NỐI MONGODB:', e.message); 
  }
}
connectDB();

// ================= API KHÁCH HÀNG =================
app.get('/api/products', async (req, res) => {
  if (!db) return res.status(500).json({ error: 'Database chưa kết nối' });
  try {
    const products = await db.collection('products').find().toArray();
    const result = await Promise.all(products.map(async (p) => {
      const stock = await db.collection('keys').countDocuments({ productId: p._id.toString(), sold: false });
      return { ...p, id: p._id.toString(), stock };
    }));
    res.json(result);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/buy/:productId', async (req, res) => {
  if (!db) return res.status(500).json({ error: 'Database chưa kết nối' });
  try {
    const product = await db.collection('products').findOne({ _id: new ObjectId(req.params.productId) });
    if (!product) return res.status(404).json({ error: 'Không có sản phẩm' });

    const payment_code = 'DH' + Date.now().toString().slice(-6);
    await db.collection('orders').insertOne({ 
      productId: product._id.toString(), 
      amount: product.price, 
      payment_code, 
      status: 'pending', 
      createdAt: new Date() 
    });
    res.json({ ok: true, payment_code, amount: product.price, productName: product.name });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ================= API ADMIN =================
app.get('/api/admin/orders', async (req, res) => {
  if (!db) return res.status(500).json({ error: 'Database chưa kết nối' });
  try {
    const orders = await db.collection('orders').find().sort({_id:-1}).limit(100).toArray();
    const result = await Promise.all(orders.map(async (o) => {
      const prod = await db.collection('products').findOne({ _id: new ObjectId(o.productId) });
      let keyVal = '-';
      if (o.keyId) {
        const k = await db.collection('keys').findOne({ _id: new ObjectId(o.keyId) });
        if (k) keyVal = k.keyValue;
      }
      return { ...o, product_name: prod ? prod.name : 'N/A', key_value: keyVal };
    }));
    res.json(result);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/orders/:id/approve', async (req, res) => {
  if (!db) return res.status(500).json({ error: 'Database chưa kết nối' });
  try {
    const orderId = req.params.id;
    const order = await db.collection('orders').findOne({ _id: new ObjectId(orderId) });
    if (!order || order.status === 'paid') return res.status(400).json({ error: 'Đơn không hợp lệ' });

    const key = await db.collection('keys').findOne({ productId: order.productId, sold: false });
    if (!key) return res.status(400).json({ error: 'Hết key!' });

    await db.collection('keys').updateOne({ _id: key._id }, { $set: { sold: true, orderId: orderId } });
    await db.collection('orders').updateOne({ _id: new ObjectId(orderId) }, { $set: { status: 'paid', keyId: key._id.toString() } });
    
    res.json({ ok: true, key: key.keyValue });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/products', async (req, res) => {
  if (!db) return res.status(500).json({ error: 'Database chưa kết nối' });
  try {
    await db.collection('products').insertOne({ name: req.body.name, price: req.body.price, desc: req.body.desc || '' });
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/keys', async (req, res) => {
  if (!db) return res.status(500).json({ error: 'Database chưa kết nối' });
  try {
    await db.collection('keys').insertOne({ productId: req.body.product_id, keyValue: req.body.key_value, sold: false });
    res.json({ ok: true });
  } catch (e) { res.status(400).json({ error: 'Lỗi thêm key' }); }
});

// ================= CHẠY SERVER =================
const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server đang chạy trên cổng ${PORT}`);
});
server.keepAliveTimeout = 120000;
server.headersTimeout = 120000;
