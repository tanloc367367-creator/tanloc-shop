import os
import telebot
import sqlite3
from flask import Flask, request

# ================= CẤU HÌNH =================
BOT_TOKEN = os.environ.get'9268542841:AAHJvJtXD7oXLfTlNeUyaSanWH5yni12DhQ'
ADMIN_ID = 8240363472 # <-- SỬA LẠI THÀNH ID TELEGRAM CỦA BẠN
# ============================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Khởi tạo Database (Lưu rank dưới dạng chữ)
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

# ================= CÁC LỆNH CỦA BOT =================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = ("Chào bạn! Đây là Bot quản lý CTV.\n"
            "Các lệnh có sẵn:\n"
            "/xephang - Xem bảng xếp hạng\n"
            "/capbac - Xem cấp bậc của mọi người\n"
            "/themctv @ten - Thêm CTV mới (Admin)\n"
            "/congkey @ten sokey - Cộng key (Admin)\n"
            "/tangcapbac - Cập nhật lại cấp bậc (Admin)\n"
            "/nguoibian - Danh sách người đạt 100+ key\n"
            "/reset - Reset toàn bộ về 0 (Admin)")
    bot.reply_to(message, text)

# 1. Lệnh /xephang (Bảng xếp hạng)
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

    text = "🏆 **BẢNG XẾP HẠNG CTV** 🏆\n\n"
    for idx, user in enumerate(users, 1):
        username, keys, rank = user
        text += f"{idx}. {username} | {rank} | Đã bán: {keys} key\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# 2. Lệnh /capbac (Xem cấp bậc)
@bot.message_handler(commands=['capbac'])
def xem_cap_bac(message):
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    # Sắp xếp theo số key giảm dần để dễ nhìn
    c.execute("SELECT username, rank, keys FROM ctv ORDER BY keys DESC")
    users = c.fetchall()
    conn.close()

    if not users:
        bot.reply_to(message, "📭 Chưa có CTV nào trong danh sách!")
        return

    text = "📊 **CẤP BẬC CỦA CÁC CTV** 📊\n\n"
    for user in users:
        username, rank, keys = user
        text += f"👤 {username}: **{rank}** (Đã bán: {keys} key)\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# 3. Lệnh /themctv
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

# 4. Lệnh /congkey
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
            new_keys = current_keys + added_keys
            new_rank = get_rank(new_keys) 
            
            c.execute("UPDATE ctv SET keys=?, rank=? WHERE username=?", (new_keys, new_rank, username))
            conn.commit()
            
            bot.reply_to(message, f"✅ Đã cộng {added_keys} key cho {username}.\nTổng key: {new_keys}\nCấp bậc hiện tại: {new_rank}")
        else:
            bot.reply_to(message, f"❌ Không tìm thấy {username}. Hãy dùng /themctv trước.")
        conn.close()
    except Exception:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /congkey @ten 5")

# 5. Lệnh /tangcapbac (Cập nhật lại toàn bộ rank)
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

# 6. Lệnh /nguoibian
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
        text = "👽 **DANH SÁCH NGƯỜI BÍ ẨN (100+ KEY)** 👑\n\n"
        for e in elites:
            text += f"- {e[0]} ({e[1]} key)\n"
        bot.reply_to(message, text, parse_mode='Markdown')

# 7. Lệnh /reset
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
