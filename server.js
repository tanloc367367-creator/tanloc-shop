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

// Lấy danh sách sản phẩm
app.get('/api/products', async (req, res) => {
  try {
    const { data, error } = await supabase.from('products').select('*');
    if (error) throw error;
    res.json(data || []);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Lấy số dư ví
app.get('/api/get-balance/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    let { data, error } = await supabase.from('users').select('balance').eq('device_id', deviceId).single();
    if (error && error.code === 'PGRST116') {
      await supabase.from('users').insert([{ device_id: deviceId, balance: 0, is_vip: false }]);
      return res.json({ balance: 0 });
    }
    if (error) throw error;
    res.json({ balance: data.balance });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Gửi yêu cầu nạp thẻ (Chờ Admin duyệt)
app.post('/api/nap-the', async (req, res) => {
  try {
    const { deviceId, amount, type, serial, pin } = req.body;
    const { error } = await supabase.from('cards').insert([{ 
      device_id: deviceId, 
      amount: Number(amount), 
      type, 
      serial, 
      pin, 
      status: 'pending' 
    }]);
    if (error) throw error;
    res.json({ ok: true, message: 'Đã gửi yêu cầu nạp thẻ!' });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Mua bằng QR (Tạo đơn chờ thanh toán)
app.post('/api/buy-qr/:productId', async (req, res) => {
  try {
    const { productId } = req.params;
    const { data: product } = await supabase.from('products').select('*').eq('id', productId).single();
    const payment_code = 'DH' + Date.now().toString().slice(-6);
    
    await supabase.from('orders').insert([{ product_id: productId, amount: product.price, status: 'pending', payment_code }]);
    res.json({ ok: true, payment_code, amount: product.price, productName: product.name });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Lấy lịch sử mua hàng của khách
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

// Kiểm tra trạng thái VIP của thiết bị
app.get('/api/check-vip/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const { data, error } = await supabase.from('users').select('is_vip').eq('device_id', deviceId).single();
    if (error && error.code === 'PGRST116') {
      await supabase.from('users').insert([{ device_id: deviceId, balance: 0, is_vip: false }]);
      return res.json({ is_vip: false });
    }
    if (error) throw error;
    res.json({ is_vip: data.is_vip });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ================= API ADMIN =================

// Lấy danh sách đơn hàng
app.get('/api/admin/orders', async (req, res) => {
  try {
    const { data, error } = await supabase.from('orders').select('*').order('id', { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Duyệt đơn hàng (Giao Key)
app.post('/api/admin/orders/:id/approve', async (req, res) => {
  try {
    const { id } = req.params;
    const { data: order } = await supabase.from('orders').select('product_id').eq('id', id).single();
    
    let { data: keys } = await supabase.from('keys').select('*').eq('product_id', order.product_id).eq('sold', false).limit(1);
    let keyValue = '';
    if (keys && keys.length > 0) {
      keyValue = keys[0].key_value;
      await supabase.from('keys').update({ sold: true }).eq('id', keys[0].id);
    } else {
      keyValue = 'KEY-' + Math.random().toString(36).substring(2, 10).toUpperCase();
    }

    await supabase.from('orders').update({ status: 'paid', key_value: keyValue }).eq('id', id);
    res.json({ ok: true, key: keyValue });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Lấy danh sách thiết bị chờ duyệt VIP
app.get('/api/admin/pending-users', async (req, res) => {
  try {
    const { data, error } = await supabase.from('users').select('*').eq('is_vip', false).order('id', { ascending: false });
    if (error) throw error;
    res.json(data || []);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Cấp quyền VIP cho thiết bị
app.post('/api/admin/users/:deviceId/approve', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const { error } = await supabase.from('users').update({ is_vip: true }).eq('device_id', deviceId);
    if (error) throw error;
    res.json({ ok: true, message: 'Đã cấp quyền VIP thành công!' });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Lấy danh sách thẻ chờ duyệt
app.get('/api/admin/cards', async (req, res) => {
  try {
    const { data, error } = await supabase.from('cards').select('*').eq('status', 'pending').order('id', { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Duyệt thẻ (Cộng tiền cho khách)
app.post('/api/admin/cards/:id/approve', async (req, res) => {
  try {
    const { id } = req.params;
    const { data: card, error: cardError } = await supabase.from('cards').select('*').eq('id', id).single();
    if (cardError || !card) return res.status(404).json({ error: 'Không tìm thấy thẻ' });
    if (card.status === 'approved') return res.status(400).json({ error: 'Thẻ này đã được duyệt rồi!' });

    const { data: user } = await supabase.from('users').select('balance').eq('device_id', card.device_id).single();
    const currentBalance = user ? Number(user.balance) : 0;
    const newBalance = currentBalance + Number(card.amount);
    
    if (user) {
      await supabase.from('users').update({ balance: newBalance }).eq('device_id', card.device_id);
    } else {
      await supabase.from('users').insert([{ device_id: card.device_id, balance: newBalance, is_vip: false }]);
    }

    await supabase.from('cards').update({ status: 'approved' }).eq('id', id);
    res.json({ ok: true, message: 'Đã duyệt thẻ và cộng tiền!' });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Thêm sản phẩm mới
app.post('/api/admin/products', async (req, res) => {
  try {
    const { name, price, description } = req.body;
    await supabase.from('products').insert([{ name, price, description }]);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Thêm Key vào kho (Hỗ trợ số lượng)
app.post('/api/admin/keys', async (req, res) => {
  try {
    const { product_id, key_value, quantity } = req.body;
    const qty = Number(quantity) || 1;
    
    const keysToInsert = [];
    for (let i = 0; i < qty; i++) {
      const finalKey = qty > 1 ? `${key_value}-${i + 1}` : key_value;
      keysToInsert.push({
        product_id: product_id,
        key_value: finalKey,
        sold: false
      });
    }

    const { error } = await supabase.from('keys').insert(keysToInsert);
    if (error) throw error;
    
    res.json({ ok: true, message: `Đã thêm thành công ${qty} key!` });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Lấy danh sách key trong kho theo sản phẩm
app.get('/api/admin/keys/:productId', async (req, res) => {
  try {
    const { productId } = req.params;
    const { data, error } = await supabase.from('keys').select('*').eq('product_id', productId).order('id', { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Khởi chạy Server
const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, "0.0.0.0", () => console.log(`🚀 Server chạy cổng ${PORT}`));
server.keepAliveTimeout = 120000;
server.headersTimeout = 120000;
