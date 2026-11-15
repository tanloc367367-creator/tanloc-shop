const express = require('express');
const { createClient } = require('@supabase/supabase-js');

const app = express();
app.use(express.json());
app.use(express.static('public'));

// CẤU HÌNH SUPABASE CỦA BẠN
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

app.post('/api/nap-the', async (req, res) => {
  try {
    const { deviceId, amount, type, serial, pin } = req.body;
    const { error } = await supabase.from('cards').insert([{ 
      device_id: deviceId, amount: Number(amount), type, serial, pin, status: 'pending' 
    }]);
    if (error) throw error;
    res.json({ ok: true, message: 'Đã gửi yêu cầu nạp thẻ!' });
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
      .from('orders').select('*, products(name)').eq('device_id', deviceId).order('id', { ascending: false });
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
    const { data: order } = await supabase.from('orders').select('product_id').eq('id', id).single();
    let { data: keys } = await supabase.from('keys').select('*').eq('product_id', order.product_id).eq('sold', false).limit(1);
    let keyValue = keys && keys.length > 0 ? keys[0].key_value : 'KEY-' + Math.random().toString(36).substring(2, 10).toUpperCase();
    
    if (keys && keys.length > 0) await supabase.from('keys').update({ sold: true }).eq('id', keys[0].id);
    await supabase.from('orders').update({ status: 'paid', key_value: keyValue }).eq('id', id);
    res.json({ ok: true, key: keyValue });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/admin/cards', async (req, res) => {
  try {
    const { data, error } = await supabase.from('cards').select('*').eq('status', 'pending').order('id', { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/cards/:id/approve', async (req, res) => {
  try {
    const { id } = req.params;
    const { data: card } = await supabase.from('cards').select('*').eq('id', id).single();
    if (!card || card.status === 'approved') return res.status(400).json({ error: 'Thẻ không hợp lệ' });

    const { data: user } = await supabase.from('users').select('balance').eq('device_id', card.device_id).single();
    const newBalance = (user ? Number(user.balance) : 0) + Number(card.amount);
    
    if (user) await supabase.from('users').update({ balance: newBalance }).eq('device_id', card.device_id);
    else await supabase.from('users').insert([{ device_id: card.device_id, balance: newBalance }]);
    
    await supabase.from('cards').update({ status: 'approved' }).eq('id', id);
    res.json({ ok: true, message: 'Đã duyệt thẻ!' });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// API Cộng tiền thủ công
app.post('/api/admin/add-balance', async (req, res) => {
  try {
    const { deviceId, amount } = req.body;
    const { data: user } = await supabase.from('users').select('balance').eq('device_id', deviceId).single();
    const newBalance = (user ? Number(user.balance) : 0) + Number(amount);
    
    if (user) await supabase.from('users').update({ balance: newBalance }).eq('device_id', deviceId);
    else await supabase.from('users').insert([{ device_id: deviceId, balance: newBalance }]);
    
    res.json({ ok: true, message: 'Đã cộng tiền!' });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/products', async (req, res) => {
  try {
    const { name, price, description } = req.body;
    await supabase.from('products').insert([{ name, price, description }]);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/admin/keys', async (req, res) => {
  try {
    const { product_id, key_value, quantity } = req.body;
    const qty = Number(quantity) || 1;
    const keysToInsert = [];
    for (let i = 0; i < qty; i++) {
      keysToInsert.push({ product_id: product_id, key_value: qty > 1 ? `${key_value}-${i + 1}` : key_value, sold: false });
    }
    const { error } = await supabase.from('keys').insert(keysToInsert);
    if (error) throw error;
    res.json({ ok: true, message: `Đã thêm ${qty} key!` });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/admin/keys/:productId', async (req, res) => {
  try {
    const { data, error } = await supabase.from('keys').select('*').eq('product_id', req.params.productId).order('id', { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, "0.0.0.0", () => console.log(`🚀 Server chạy cổng ${PORT}`));
