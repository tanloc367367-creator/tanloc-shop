const express = require('express');
const { createClient } = require('@supabase/supabase-js');

const app = express();
app.use(express.json());
app.use(express.static('public'));

const SUPABASE_URL = 'https://gapwuzvjwtprhlbnejos.supabase.co';
const SUPABASE_KEY = 'sb_publishable_pu1h_zZ-PEAzyGgYkgT1bg_Q8Qw3rn4';
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

// API lấy sản phẩm
app.get('/api/products', async (req, res) => {
  const { data, error } = await supabase.from('products').select('*');
  if (error) return res.status(500).json({ error: error.message });
  
  // Đếm số key còn lại
  const productsWithStock = await Promise.all(data.map(async (p) => {
    const { count } = await supabase.from('orders').select('*', { count: 'exact', head: true }).eq('product_id', p.id).eq('status', 'pending');
    return { ...p, stock: 999 }; // Tạm thời để 999, quản lý kho sau
  }));
  res.json(productsWithStock);
});

// API lấy số dư ví
app.get('/api/get-balance/:deviceId', async (req, res) => {
  const { deviceId } = req.params;
  let { data, error } = await supabase.from('users').select('balance').eq('device_id', deviceId).single();
  
  if (error && error.code === 'PGRST116') { // Chưa có user
    await supabase.from('users').insert([{ device_id: deviceId, balance: 0 }]);
    return res.json({ balance: 0 });
  }
  if (error) return res.status(500).json({ error: error.message });
  res.json({ balance: data.balance });
});

// API nạp thẻ (Mô phỏng)
app.post('/api/nap-the', async (req, res) => {
  const { deviceId, amount } = req.body;
  let { data } = await supabase.from('users').select('balance').eq('device_id', deviceId).single();
  const newBalance = (data?.balance || 0) + Number(amount);
  await supabase.from('users').update({ balance: newBalance }).eq('device_id', deviceId);
  res.json({ ok: true, balance: newBalance });
});

// API mua hàng bằng ví
app.post('/api/buy-wallet/:productId', async (req, res) => {
  const { deviceId } = req.body;
  const { productId } = req.params;

  const { data: product } = await supabase.from('products').select('*').eq('id', productId).single();
  const { data: user } = await supabase.from('users').select('balance').eq('device_id', deviceId).single();

  if (!product || !user) return res.status(404).json({ error: 'Không tìm thấy' });
  if (user.balance < product.price) return res.status(400).json({ error: 'Số dư không đủ!' });

  // Trừ tiền
  const newBalance = user.balance - product.price;
  await supabase.from('users').update({ balance: newBalance }).eq('device_id', deviceId);

  // Tạo đơn hàng chờ duyệt
  await supabase.from('orders').insert([{ device_id: deviceId, product_id: productId, amount: product.price, status: 'waiting', payment_code: 'VIP' }]);

  res.json({ ok: true, balance: newBalance });
});

// API tạo đơn QR
app.post('/api/buy-qr/:productId', async (req, res) => {
  const { productId } = req.params;
  const { data: product } = await supabase.from('products').select('*').eq('id', productId).single();
  const payment_code = 'DH' + Date.now().toString().slice(-6);
  await supabase.from('orders').insert([{ product_id: productId, amount: product.price, status: 'pending', payment_code }]);
  res.json({ ok: true, payment_code, amount: product.price, productName: product.name });
});

// ================= API ADMIN =================
app.get('/api/admin/orders', async (req, res) => {
  const { data, error } = await supabase.from('orders').select('*');
  if (error) return res.status(500).json({ error: error.message });
  res.json(data);
});

app.post('/api/admin/orders/:id/approve', async (req, res) => {
  const { id } = req.params;
  const { data: order } = await supabase.from('orders').select('*').eq('id', id).single();
  
  // Tìm key trong kho (nếu có) hoặc trả về key mẫu
  const keyValue = 'KEY-' + Math.random().toString(36).substring(2, 10).toUpperCase();
  
  await supabase.from('orders').update({ status: 'paid', key_value: keyValue }).eq('id', id);
  res.json({ ok: true, key: keyValue });
});

app.post('/api/admin/products', async (req, res) => {
  const { name, price, description } = req.body;
  await supabase.from('products').insert([{ name, price, description }]);
  res.json({ ok: true });
});

app.post('/api/admin/keys', async (req, res) => {
  // Tạm thời chưa dùng
  res.json({ ok: true });
});

// Khởi chạy
const PORT = process.env.PORT || 3000;
app.listen(PORT, "0.0.0.0", () => console.log(`🚀 Server chạy cổng ${PORT}`));
