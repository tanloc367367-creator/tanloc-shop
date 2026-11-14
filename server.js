const express = require('express');
const { createClient } = require('@supabase/supabase-js');

const app = express();
app.use(express.json());
app.use(express.static('public'));

const SUPABASE_URL = 'https://gapwuzvjwtprhlbnejos.supabase.co';
const SUPABASE_KEY = 'sb_publishable_pu1h_zZ-PEAzyGgYkgT1bg_Q8Qw3rn4';
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

// ================= API KHÁCH HÀNG =================
app.get('/api/products', async (req, res) => {
  try {
    const { data, error } = await supabase.from('products').select('*');
    if (error) throw error;
    res.json(data || []);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/get-balance/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    let { data, error } = await supabase.from('users').select('balance').eq('device_id', deviceId).single();
    if (error && error.code === 'PGRST116') {
      await supabase.from('users').insert([{ device_id: deviceId, balance: 0 }]);
      return res.json({ balance: 0 });
    }
    if (error) throw error;
    res.json({ balance: data.balance });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Gửi yêu cầu nạp thẻ (Chờ duyệt)
app.post('/api/nap-the', async (req, res) => {
  try {
    const { deviceId, amount, type, serial, pin } = req.body;
    // Lưu vào bảng cards với trạng thái pending
    const { error } = await supabase.from('cards').insert([{ 
      device_id: deviceId, 
      amount: Number(amount), 
      type, 
      serial, 
      pin, 
      status: 'pending' 
    }]);
    if (error) throw error;
    res.json({ ok: true, message: 'Đã gửi yêu cầu nạp thẻ, vui lòng chờ Admin duyệt!' });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/buy-wallet/:productId', async (req, res) => {
  try {
    const { deviceId } = req.body;
    const { productId } = req.params;
    const { data: product } = await supabase.from('products').select('*').eq('id', productId).single();
    const { data: user } = await supabase.from('users').select('balance').eq('device_id', deviceId).single();
    if (!product || !user) return res.status(404).json({ error: 'Không tìm thấy' });
    if (user.balance < product.price) return res.status(400).json({ error: 'Số dư không đủ!' });
    const newBalance = user.balance - product.price;
    await supabase.from('users').update({ balance: newBalance }).eq('device_id', deviceId);
    await supabase.from('orders').insert([{ device_id: deviceId, product_id: productId, amount: product.price, status: 'waiting', payment_code: 'VIP' }]);
    res.json({ ok: true, balance: newBalance });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/buy-qr/:productId', async (req, res) => {
  try {
    const { productId } = req.params;
    const { data: product } = await supabase.from('products').select('*').eq('id', productId).single();
    const payment_code = 'DH' + Date.now().toString().slice(-6);
    await supabase.from('orders').insert([{ product_id: productId, amount: product.price, status: 'pending', payment_code }]);
    res.json({ ok: true, payment_code, amount: product.price, productName: product.name });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/my-history/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const { data: orders, error } = await supabase
      .from('orders')
      .select('*, products(name)')
      .eq('device_id', deviceId)
      .order('id', { ascending: false });
    if (error) throw error;
    res.json(orders);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ================= API ADMIN =================
app.get('/api/admin/orders', async (req, res) => {
  try {
    const { data, error } = await supabase.from('orders').select('*').order('id', { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/orders/:id/approve', async (req, res) => {
  try {
    const { id } = req.params;
    const keyValue = 'KEY-' + Math.random().toString(36).substring(2, 10).toUpperCase();
    await supabase.from('orders').update({ status: 'paid', key_value: keyValue }).eq('id', id);
    res.json({ ok: true, key: keyValue });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Admin lấy danh sách thẻ chờ duyệt
app.get('/api/admin/cards', async (req, res) => {
  try {
    const { data, error } = await supabase.from('cards').select('*').eq('status', 'pending').order('id', { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Admin duyệt thẻ
app.post('/api/admin/cards/:id/approve', async (req, res) => {
  try {
    const { id } = req.params;
    // Lấy thông tin thẻ
    const { data: card } = await supabase.from('cards').select('*').eq('id', id).single();
    if (!card) return res.status(404).json({ error: 'Không tìm thấy thẻ' });

    // Cộng tiền cho user
    const { data: user } = await supabase.from('users').select('balance').eq('device_id', card.device_id).single();
    const newBalance = (user?.balance || 0) + card.amount;
    
    if (user) {
      await supabase.from('users').update({ balance: newBalance }).eq('device_id', card.device_id);
    } else {
      await supabase.from('users').insert([{ device_id: card.device_id, balance: newBalance }]);
    }

    // Đổi trạng thái thẻ thành đã duyệt
    await supabase.from('cards').update({ status: 'approved' }).eq('id', id);
    res.json({ ok: true, message: 'Đã duyệt thẻ và cộng tiền!' });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/products', async (req, res) => {
  try {
    const { name, price, description } = req.body;
    await supabase.from('products').insert([{ name, price, description }]);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, "0.0.0.0", () => console.log(`🚀 Server chạy cổng ${PORT}`));
server.keepAliveTimeout = 120000;
server.headersTimeout = 120000;
