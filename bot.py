import os
import telebot
import sqlite3
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CẤU HÌNH =================
# DÁN TOKEN MỚI CỦA BẠN VÀO GIỮA 2 DẤU NHÁY ĐƠN DƯỚI ĐÂY:
BOT_TOKEN = '9268542841:AAHJvJtXD7oXLfTlNeUyaSanWH5yni12DhQ'
ADMIN_ID = 8240363472 # SỬA 123456789 THÀNH ID TELEGRAM CỦA BẠN
# ============================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Khởi tạo Database
def init_db():
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ctv
                 (username TEXT PRIMARY KEY, keys INTEGER, rank TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Hàm kiểm tra quyền Admin
def is_admin(message):
    return message.from_user.id == ADMIN_ID

# Hàm tự động tính cấp bậc dựa trên số key
def get_rank(keys):
    if keys >= 100:
        return "Kim Cương Cao Cấp 👑"
    elif keys >= 50:
        return "Kim Cương 💎"
    elif keys >= 25:
        return "Vàng 🥇"
    elif keys >= 10:
        return "Bạc 🥈"
    else:
        return "Đồng 🥉"

# Tạo Menu nút bấm
def get_main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🏆 Xếp Hạng", callback_data="menu_xephang"),
               InlineKeyboardButton("📊 Cấp Bậc", callback_data="menu_capbac"))
    markup.row(InlineKeyboardButton("🎯 Nhiệm Vụ", callback_data="menu_nhiemvu"))
    return markup

# ================= CÁC LỆNH CỦA BOT =================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = ("Chào bạn! Đây là Bot quản lý CTV.\n"
            "👇 Bấm vào các nút bên dưới để xem thông tin:\n\n"
            "🛠 <b>Lệnh cho Admin:</b>\n"
            "/themctv @ten - Thêm CTV\n"
            "/congkey @ten sokey - Cộng key\n"
            "/trukey @ten sokey - Trừ key\n"
            "/xoactv @ten - Xóa CTV\n"
            "/thongke - Xem tổng quan hệ thống\n"
            "/tangcapbac - Cập nhật lại cấp bậc\n"
            "/reset - Reset toàn bộ về 0")
    bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_main_menu())

# --- XỬ LÝ KHI BẤM NÚT MENU ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu_callback(call):
    bot.answer_callback_query(call.id)
    if call.data == 'menu_xephang':
        xep_hang(call.message)
    elif call.data == 'menu_capbac':
        xem_cap_bac(call.message)
    elif call.data == 'menu_nhiemvu':
        nhiem_vu(call.message)

# 1. Lệnh /xephang
@bot.message_handler(commands=['xephang'])
def xep_hang(message):
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT username, keys, rank FROM ctv ORDER BY keys DESC")
    users = c.fetchall()
    conn.close()

    if not users:
        bot.reply_to(message, "📭 Chưa có CTV nào trong danh sách!")
        return

    text = "🏆 <b>BẢNG XẾP HẠNG CTV</b> 🏆\n\n"
    for idx, user in enumerate(users, 1):
        username, keys, rank = user
        text += f"{idx}. {username} | {rank} | Đã bán: {keys} key\n"
    
    bot.reply_to(message, text, parse_mode='HTML')

# 2. Lệnh /capbac
@bot.message_handler(commands=['capbac'])
def xem_cap_bac(message):
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT username, rank, keys FROM ctv ORDER BY keys DESC")
    users = c.fetchall()
    conn.close()

    if not users:
        bot.reply_to(message, "📭 Chưa có CTV nào trong danh sách!")
        return

    text = "📊 <b>CẤP BẬC CỦA CÁC CTV</b> 📊\n\n"
    for user in users:
        username, rank, keys = user
        text += f"👤 {username}: <b>{rank}</b> (Đã bán: {keys} key)\n"
    
    bot.reply_to(message, text, parse_mode='HTML')

# 3. Lệnh /nhiemvu
@bot.message_handler(commands=['nhiemvu'])
def nhiem_vu(message):
    parts = message.text.split()
    
    if len(parts) == 1:
        text = ("🎯 <b>BẢNG NHIỆM VỤ CTV</b> 🎯\n\n"
                "1. Bán 5 key (Nhận danh hiệu Đồng 🥉)\n"
                "2. Bán 20 key (Tiến gần tới Bạc 🥈)\n"
                "3. Bán 30 key (Nhận danh hiệu Vàng 🥇)\n\n"
                "👉 Để xem tiến độ của bạn, hãy gõ: <code>/nhiemvu @ten_cua_ban</code>")
        bot.reply_to(message, text, parse_mode='HTML')
        
    else:
        username = parts[1]
        conn = sqlite3.connect('ctv_data.db')
        c = conn.cursor()
        c.execute("SELECT keys FROM ctv WHERE username=?", (username,))
        data = c.fetchone()
        conn.close()
        
        if not data:
            bot.reply_to(message, f"❌ Không tìm thấy CTV {username} trong hệ thống!")
            return
            
        keys = data[0]
        
        check_5 = "✅ Đã đạt" if keys >= 5 else f"❌ Còn thiếu {5 - keys} key"
        check_20 = "✅ Đã đạt" if keys >= 20 else f"❌ Còn thiếu {20 - keys} key"
        check_30 = "✅ Đã đạt" if keys >= 30 else f"❌ Còn thiếu {30 - keys} key"
        
        text = (f"🎯 <b>TIẾN ĐỘ NHIỆM VỤ CỦA {username}</b> 🎯\n\n"
                f"📊 Tổng số key đã bán: <b>{keys} key</b>\n\n"
                f"1. Mốc 5 key: {check_5}\n"
                f"2. Mốc 20 key: {check_20}\n"
                f"3. Mốc 30 key: {check_30}\n\n"
                f"💪 Cố gắng lên nhé!")
        bot.reply_to(message, text, parse_mode='HTML')

# 4. Lệnh /themctv
@bot.message_handler(commands=['themctv'])
def them_ctv(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Bạn không phải Admin!")
        return
    
    try:
        parts = message.text.split()
        username = parts[1]
        
        conn = sqlite3.connect('ctv_data.db')
        c = conn.cursor()
        c.execute("SELECT username FROM ctv WHERE username=?", (username,))
        if c.fetchone():
            bot.reply_to(message, f"⚠️ {username} đã có trong danh sách!")
        else:
            c.execute("INSERT INTO ctv (username, keys, rank) VALUES (?, 0, ?)", (username, "Đồng 🥉"))
            conn.commit()
            bot.reply_to(message, f"✅ Đã thêm {username} với cấp bậc Đồng 🥉.")
        conn.close()
    except Exception:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /themctv @ten")

# 5. Lệnh /congkey (Có thông báo thăng hạng)
@bot.message_handler(commands=['congkey'])
def cong_key(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Bạn không phải Admin!")
        return
    
    try:
        parts = message.text.split()
        username = parts[1]
        added_keys = int(parts[2])
        
        conn = sqlite3.connect('ctv_data.db')
        c = conn.cursor()
        c.execute("SELECT keys FROM ctv WHERE username=?", (username,))
        data = c.fetchone()
        
        if data:
            current_keys = data[0]
            old_rank = get_rank(current_keys)
            
            new_keys = current_keys + added_keys
            new_rank = get_rank(new_keys) 
            
            c.execute("UPDATE ctv SET keys=?, rank=? WHERE username=?", (new_keys, new_rank, username))
            conn.commit()
            
            # Gửi tin nhắn cộng key thành công
            bot.reply_to(message, f"✅ Đã cộng {added_keys} key cho {username}.\nTổng key: {new_keys}\nCấp bậc hiện tại: {new_rank}")
            
            # THÔNG BÁO THĂNG HẠNG (Nếu có sự thay đổi cấp bậc)
            if old_rank != new_rank and added_keys > 0:
                bot.send_message(message.chat.id, f"🎉 Chúc mừng <b>{username}</b> đã thăng cấp lên <b>{new_rank}</b>! Quá xuất sắc!", parse_mode='HTML')
                
        else:
            bot.reply_to(message, f"❌ Không tìm thấy {username}. Hãy dùng /themctv trước.")
        conn.close()
    except Exception:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /congkey @ten 5")

# 6. Lệnh /trukey (Trừ key)
@bot.message_handler(commands=['trukey'])
def tru_key(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Bạn không phải Admin!")
        return
    
    try:
        parts = message.text.split()
        username = parts[1]
        minus_keys = int(parts[2])
        
        conn = sqlite3.connect('ctv_data.db')
        c = conn.cursor()
        c.execute("SELECT keys FROM ctv WHERE username=?", (username,))
        data = c.fetchone()
        
        if data:
            current_keys = data[0]
            # Đảm bảo số key không bị âm
            new_keys = max(0, current_keys - minus_keys) 
            new_rank = get_rank(new_keys) 
            
            c.execute("UPDATE ctv SET keys=?, rank=? WHERE username=?", (new_keys, new_rank, username))
            conn.commit()
            
            bot.reply_to(message, f"✅ Đã trừ {minus_keys} key của {username}.\nTổng key còn lại: {new_keys}\nCấp bậc hiện tại: {new_rank}")
        else:
            bot.reply_to(message, f"❌ Không tìm thấy {username}.")
        conn.close()
    except Exception:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /trukey @ten 5")

# 7. Lệnh /xoactv
@bot.message_handler(commands=['xoactv'])
def xoa_ctv(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Bạn không phải Admin!")
        return
    
    try:
        parts = message.text.split()
        username = parts[1]
        
        conn = sqlite3.connect('ctv_data.db')
        c = conn.cursor()
        c.execute("DELETE FROM ctv WHERE username=?", (username,))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"🗑 Đã xóa CTV {username} khỏi hệ thống!")
    except Exception:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /xoactv @ten")

# 8. Lệnh /thongke
@bot.message_handler(commands=['thongke'])
def thong_ke(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Bạn không phải Admin!")
        return
    
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    
    # Đếm tổng số CTV
    c.execute("SELECT COUNT(*) FROM ctv")
    total_ctv = c.fetchone()[0]
    
    # Tính tổng số key
    c.execute("SELECT SUM(keys) FROM ctv")
    total_keys = c.fetchone()[0]
    if total_keys is None: total_keys = 0
    
    # Tìm người Top 1
    c.execute("SELECT username, keys FROM ctv ORDER BY keys DESC LIMIT 1")
    top1 = c.fetchone()
    conn.close()
    
    text = "📈 <b>THỐNG KÊ HỆ THỐNG</b> 📈\n\n"
    text += f"👥 Tổng số CTV: <b>{total_ctv}</b> người\n"
    text += f"🔑 Tổng số key đã bán: <b>{total_keys}</b> key\n\n"
    
    if top1:
        text += f"🥇 <b>Top 1 hiện tại:</b> {top1[0]} với {top1[1]} key"
        
    bot.reply_to(message, text, parse_mode='HTML')

# 9. Lệnh /tangcapbac
@bot.message_handler(commands=['tangcapbac'])
def tang_cap_bac(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Bạn không phải Admin!")
        return
    
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT username, keys FROM ctv")
    users = c.fetchall()
    
    for user in users:
        username, keys = user
        new_rank = get_rank(keys)
        c.execute("UPDATE ctv SET rank=? WHERE username=?", (new_rank, username))
    
    conn.commit()
    conn.close()
    bot.reply_to(message, "✅ Đã tự động cập nhật lại cấp bậc cho toàn bộ CTV!")

# 10. Lệnh /nguoibian
@bot.message_handler(commands=['nguoibian'])
def nguoi_bi_an(message):
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT username, keys FROM ctv WHERE keys >= 100 ORDER BY keys DESC")
    elites = c.fetchall()
    conn.close()
    
    if not elites:
        bot.reply_to(message, "Hiện tại chưa có ai đạt cảnh giới 'Kim Cương Cao Cấp' (100+ key) 👽")
    else:
        text = "👽 <b>DANH SÁCH NGƯỜI BÍ ẨN (100+ KEY)</b> 👑\n\n"
        for e in elites:
            text += f"- {e[0]} ({e[1]} key)\n"
        bot.reply_to(message, text, parse_mode='HTML')

# 11. Lệnh /reset
@bot.message_handler(commands=['reset'])
def reset(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Bạn không phải Admin!")
        return
    
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("UPDATE ctv SET keys=0, rank='Đồng 🥉'")
    conn.commit()
    conn.close()
    bot.reply_to(message, "🧹 Đã reset toàn bộ key về 0 và hạ cấp bậc xuống Đồng 🥉!")

# ================= CẤU HÌNH WEBHOOK CHO RENDER =================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{os.environ.get('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}")
    return "Bot đang chạy!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
