import os
import telebot
import sqlite3
import random
import time
from datetime import datetime, timedelta
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CẤU HÌNH =================
BOT_TOKEN = '9268542841:AAHJvJtXD7oXLfTlNeUyaSanWH5yni12DhQ'
ADMIN_ID = 8240363472 # SỬA THÀNH ID CỦA BẠN
BANNER_URL = 'https://i.postimg.cc/G3P8qX0G/file-000000005d588209b919bcce17087b9f.png'
# ============================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Lấy ngày hôm nay định dạng YYYY-MM-DD
def get_today():
    return datetime.now().strftime("%Y-%m-%d")

# Khởi tạo và Nâng cấp Database
def init_db():
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    # Tạo bảng với đầy đủ các cột mới
    c.execute('''CREATE TABLE IF NOT EXISTS ctv
                 (username TEXT PRIMARY KEY, keys INTEGER, rank TEXT, 
                 join_date TEXT, quote TEXT, last_checkin TEXT, streak INTEGER, 
                 last_wheel TEXT, kudos INTEGER)''')
    
    # Nếu bảng đã tồn tại từ code cũ, tự động thêm các cột mới vào
    try:
        c.execute("ALTER TABLE ctv ADD COLUMN join_date TEXT")
        c.execute("ALTER TABLE ctv ADD COLUMN quote TEXT")
        c.execute("ALTER TABLE ctv ADD COLUMN last_checkin TEXT")
        c.execute("ALTER TABLE ctv ADD COLUMN streak INTEGER DEFAULT 0")
        c.execute("ALTER TABLE ctv ADD COLUMN last_wheel TEXT")
        c.execute("ALTER TABLE ctv ADD COLUMN kudos INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Các cột đã tồn tại thì bỏ qua
        
    conn.commit()
    conn.close()

init_db()

# Hàm kiểm tra quyền Admin
def is_admin(message):
    return message.from_user.id == ADMIN_ID

# Hàm tự động tính cấp bậc
def get_rank(keys):
    if keys >= 100: return "Kim Cương Cao Cấp 👑"
    elif keys >= 50: return "Kim Cương 💎"
    elif keys >= 25: return "Vàng 🥇"
    elif keys >= 10: return "Bạc 🥈"
    else: return "Đồng 🥉"

# Hàm cập nhật Database khi có thay đổi key
def update_keys(username, new_keys):
    new_rank = get_rank(new_keys)
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("UPDATE ctv SET keys=?, rank=? WHERE username=?", (new_keys, new_rank, username))
    conn.commit()
    conn.close()
    return new_rank

# Tạo Menu nút bấm
def get_main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🏆 Xếp Hạng", callback_data="menu_xephang"),
               InlineKeyboardButton("📊 Cấp Bậc", callback_data="menu_capbac"))
    markup.row(InlineKeyboardButton("🎯 Nhiệm Vụ", callback_data="menu_nhiemvu"),
               InlineKeyboardButton("👤 Thông Tin", callback_data="menu_info"))
    markup.row(InlineKeyboardButton("🎲 Vòng Quay", callback_data="menu_vongquay"),
               InlineKeyboardButton("📅 Điểm Danh", callback_data="menu_diemdanh"))
    markup.row(InlineKeyboardButton("💳 Hồ Sơ CTV", callback_data="menu_profile"),
               InlineKeyboardButton("🔥 Top 3", callback_data="menu_top"))
    return markup

# ================= CÁC LỆNH CỦA BOT =================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if is_admin(message):
        text = ("Chào Sếp! Bot quản lý CTV đã được nâng cấp.\n"
                "👇 Bấm nút bên dưới hoặc dùng lệnh:\n\n"
                "🛠 <b>Lệnh Admin:</b>\n"
                "/themctv @ten - Thêm CTV\n"
                "/congkey @ten sokey - Cộng key\n"
                "/trukey @ten sokey - Trừ key\n"
                "/xoactv @ten - Xóa CTV\n"
                "/thongke - Tổng quan hệ thống\n"
                "/thongbao [nội dung] - Gửi thông báo toàn bộ\n"
                "/reset - Reset toàn bộ về 0")
    else:
        text = ("Chào bạn! Chào mừng đến với hệ thống CTV.\n"
                "👇 Bấm nút bên dưới hoặc dùng lệnh:\n"
                "/vongquay - Quay số nhận key\n"
                "/diemdanh - Điểm danh hàng ngày\n"
                "/profile - Xem thẻ CTV\n"
                "/setquote [châm ngôn] - Đổi châm ngôn\n"
                "/khen @ten - Thả tim đồng đội")
    
    try:
        bot.send_photo(message.chat.id, BANNER_URL, caption=text, parse_mode='HTML', reply_markup=get_main_menu())
    except Exception:
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_main_menu())

# --- XỬ LÝ NÚT BẤM MENU ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu_callback(call):
    bot.answer_callback_query(call.id)
    if call.data == 'menu_xephang': xep_hang(call.message)
    elif call.data == 'menu_capbac': xem_cap_bac(call.message)
    elif call.data == 'menu_nhiemvu': nhiem_vu(call.message)
    elif call.data == 'menu_info': xem_thong_tin_ca_nhan(call.message)
    elif call.data == 'menu_vongquay': vong_quay(call.message)
    elif call.data == 'menu_diemdanh': diem_danh(call.message)
    elif call.data == 'menu_profile': xem_profile(call.message)
    elif call.data == 'menu_top': xem_top_3(call.message)

# --- CÁC TÍNH NĂNG GIẢI TRÍ MỚI ---

# 1. Lệnh /vongquay
@bot.message_handler(commands=['vongquay'])
def vong_quay(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if not username:
        bot.reply_to(message, "❌ Bạn cần tạo Username Telegram để chơi!")
        return

    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT keys, last_wheel FROM ctv WHERE username=?", (username,))
    data = c.fetchone()
    
    if not data:
        bot.reply_to(message, "❌ Bạn chưa có trong hệ thống. Liên hệ Admin nhé!")
        conn.close()
        return
    
    current_keys, last_wheel = data
    today = get_today()
    
    if last_wheel == today:
        bot.reply_to(message, "⏳ Bạn đã quay hôm nay rồi. Hãy quay lại vào ngày mai nhé!")
        conn.close()
        return
        
    rewards = [0, 1, 1, 3, 5]
    weights = [40, 30, 15, 10, 5] # Tỉ lệ phần trăm (tổng = 100)
    won_keys = random.choices(rewards, weights=weights, k=1)[0]
    
    new_keys = current_keys + won_keys
    new_rank = update_keys(username, new_keys)
    
    c.execute("UPDATE ctv SET last_wheel=? WHERE username=?", (today, username))
    conn.commit()
    conn.close()
    
    if won_keys == 0:
        bot.reply_to(message, f"🎲 Kết quả: <b>Chúc bạn may mắn lần sau!</b> (0 key)\n(Tổng: {new_keys} key)", parse_mode='HTML')
    elif won_keys >= 3:
        bot.reply_to(message, f"🎉 QUÁ ĐỈNH! Bạn quay trúng <b>{won_keys} key</b>!\nCấp bậc: {new_rank}\n(Tổng: {new_keys} key)", parse_mode='HTML')
    else:
        bot.reply_to(message, f"🎊 Chúc mừng! Bạn nhận được <b>{won_keys} key</b>.\n(Tổng: {new_keys} key)", parse_mode='HTML')

# 2. Lệnh /diemdanh
@bot.message_handler(commands=['diemdanh'])
def diem_danh(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if not username:
        bot.reply_to(message, "❌ Bạn cần tạo Username Telegram để điểm danh!")
        return

    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT keys, last_checkin, streak FROM ctv WHERE username=?", (username,))
    data = c.fetchone()
    
    if not data:
        bot.reply_to(message, "❌ Bạn chưa có trong hệ thống!")
        conn.close()
        return
        
    current_keys, last_checkin, streak = data
    if streak is None: streak = 0
    today = get_today()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if last_checkin == today:
        bot.reply_to(message, "⏳ Hôm nay bạn đã điểm danh rồi. Quay lại vào ngày mai nhé!")
        conn.close()
        return
        
    # Xử lý chuỗi ngày (Streak)
    if last_checkin == yesterday:
        streak += 1
    else:
        streak = 1
        
    bonus_text = ""
    added_keys = 1 # Mặc định 1 key/ngày
    
    if streak >= 7:
        added_keys += 5 # Thưởng thêm 5 key nếu chuỗi 7 ngày
        bonus_text = "\n🔥 <b>TUYỆT VỜI! Bạn đã điểm danh đủ 7 ngày liên tiếp. Thưởng thêm 5 key!</b>"
        streak = 0 # Reset chuỗi sau khi nhận thưởng
        
    new_keys = current_keys + added_keys
    new_rank = update_keys(username, new_keys)
    
    c.execute("UPDATE ctv SET last_checkin=?, streak=? WHERE username=?", (today, streak, username))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Điểm danh thành công! Nhận <b>{added_keys} key</b>.\nChuỗi điểm danh: {streak}/7 ngày.{bonus_text}\n(Tổng: {new_keys} key - {new_rank})", parse_mode='HTML')

# 3. Lệnh /profile (Thẻ căn cước)
@bot.message_handler(commands=['profile'])
def xem_profile(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if not username:
        bot.reply_to(message, "❌ Bạn cần tạo Username Telegram để xem hồ sơ!")
        return
        
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT keys, rank, join_date, quote, kudos FROM ctv WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()
    
    if not data:
        bot.reply_to(message, "❌ Bạn chưa có trong hệ thống!")
        return
        
    keys, rank, join_date, quote, kudos = data
    if not quote: quote = "Chưa có châm ngôn..."
    if not join_date: join_date = "Không rõ"
    if kudos is None: kudos = 0
    
    text = (f"💳 <b>THẺ CĂN CƯỚC CTV</b> 💳\n"
            f"-----------------------------\n"
            f"👤 <b>Chủ thẻ:</b> {username}\n"
            f"📅 <b>Gia nhập:</b> {join_date}\n"
            f"🏅 <b>Cấp bậc:</b> {rank}\n"
            f"🔑 <b>Key sở hữu:</b> {keys} key\n"
            f"💖 <b>Lượt khen:</b> {kudos}\n"
            f"-----------------------------\n"
            f"💬 <b>Châm ngôn:</b> <i>\"{quote}\"</i>")
    bot.reply_to(message, text, parse_mode='HTML')

# 4. Lệnh /setquote
@bot.message_handler(commands=['setquote'])
def set_quote(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if not username:
        bot.reply_to(message, "❌ Bạn cần tạo Username Telegram để dùng lệnh này!")
        return
        
    text = message.text.replace('/setquote', '').strip()
    if not text:
        bot.reply_to(message, "❌ Vui lòng nhập châm ngôn. VD: /setquote Cày cuốc không ngại khó")
        return
    if len(text) > 50:
        bot.reply_to(message, "❌ Châm ngôn quá dài, vui lòng nhập dưới 50 ký tự thôi!")
        return
        
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("UPDATE ctv SET quote=? WHERE username=?", (text, username))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Đã cập nhật châm ngôn của bạn thành:\n<i>\"{text}\"</i>", parse_mode='HTML')

# 5. Lệnh /khen (Thả tim)
@bot.message_handler(commands=['khen'])
def khen_nguoi(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Cú pháp: /khen @ten_nguoi_ban_muon_khen")
        return
        
    target = parts[1]
    my_username = f"@{message.from_user.username}" if message.from_user.username else None
    
    if not my_username:
        bot.reply_to(message, "❌ Bạn cần có Username mới thả tim được!")
        return
        
    if target == my_username:
        bot.reply_to(message, "🤦 Bạn không thể tự khen mình được đâu nha!")
        return
        
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT kudos FROM ctv WHERE username=?", (target,))
    data = c.fetchone()
    
    if not data:
        bot.reply_to(message, f"❌ Không tìm thấy CTV {target} trong hệ thống!")
    else:
        current_kudos = data[0] if data[0] else 0
        c.execute("UPDATE ctv SET kudos=? WHERE username=?", (current_kudos + 1, target))
        conn.commit()
        bot.reply_to(message, f"💖 <b>{my_username}</b> đã gửi một lời khen ngợi đến <b>{target}</b>!\nTổng lượt khen: {current_kudos + 1}.", parse_mode='HTML')
    conn.close()

# 6. Lệnh /thongbao (Admin)
@bot.message_handler(commands=['thongbao'])
def thong_bao(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Chỉ Admin mới được dùng lệnh này!")
        return
        
    text = message.text.replace('/thongbao', '').strip()
    if not text:
        bot.reply_to(message, "❌ Cú pháp: /thongbao [Nội dung thông báo]")
        return
        
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT username FROM ctv")
    users = c.fetchall()
    conn.close()
    
    if not users:
        bot.reply_to(message, "📭 Chưa có CTV nào trong hệ thống để gửi!")
        return
        
    success = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user[0], f"📢 <b>THÔNG BÁO TỪ ADMIN</b> 📢\n\n{text}", parse_mode='HTML')
            success += 1
            time.sleep(0.1) # Tránh bị Telegram chặn do gửi quá nhanh
        except Exception:
            failed += 1
            
    bot.reply_to(message, f"✅ Đã gửi thành công: {success} người.\n❌ Thất bại: {failed} người (Do họ chưa start bot).")

# --- CÁC HÀM CŨ ĐƯỢC GIỮ NGUYÊN ---

@bot.message_handler(commands=['xephang'])
def xep_hang(message):
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT username, keys, rank FROM ctv ORDER BY keys DESC")
    users = c.fetchall()
    conn.close()

    if not users:
        bot.reply_to(message, "📭 Chưa có CTV nào!")
        return

    text = "🏆 <b>BẢNG XẾP HẠNG CTV</b> 🏆\n\n"
    for idx, user in enumerate(users, 1):
        username, keys, rank = user
        text += f"{idx}. {username} | {rank} | {keys} key\n"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['capbac'])
def xem_cap_bac(message):
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT username, rank, keys FROM ctv ORDER BY keys DESC")
    users = c.fetchall()
    conn.close()

    if not users:
        bot.reply_to(message, "📭 Chưa có CTV nào!")
        return

    text = "📊 <b>CẤP BẬC CỦA CÁC CTV</b> 📊\n\n"
    for user in users:
        username, rank, keys = user
        text += f"👤 {username}: <b>{rank}</b> ({keys} key)\n"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['nhiemvu'])
def nhiem_vu(message):
    parts = message.text.split()
    if len(parts) == 1:
        text = ("🎯 <b>BẢNG NHIỆM VỤ CTV</b> 🎯\n\n"
                "1. Bán 5 key (Nhận danh hiệu Đồng 🥉)\n"
                "2. Bán 20 key (Tiến gần tới Bạc 🥈)\n"
                "3. Bán 30 key (Nhận danh hiệu Vàng 🥇)\n\n"
                "👉 Xem tiến độ: <code>/nhiemvu @ten_cua_ban</code>")
        bot.reply_to(message, text, parse_mode='HTML')
    else:
        username = parts[1]
        conn = sqlite3.connect('ctv_data.db')
        c = conn.cursor()
        c.execute("SELECT keys FROM ctv WHERE username=?", (username,))
        data = c.fetchone()
        conn.close()
        
        if not data:
            bot.reply_to(message, f"❌ Không tìm thấy {username}!")
            return
        keys = data[0]
        check_5 = "✅ Đã đạt" if keys >= 5 else f"❌ Còn thiếu {5 - keys} key"
        check_20 = "✅ Đã đạt" if keys >= 20 else f"❌ Còn thiếu {20 - keys} key"
        check_30 = "✅ Đã đạt" if keys >= 30 else f"❌ Còn thiếu {30 - keys} key"
        
        text = (f"🎯 <b>TIẾN ĐỘ NHIỆM VỤ CỦA {username}</b> 🎯\n\n"
                f"📊 Tổng key: <b>{keys} key</b>\n\n"
                f"1. Mốc 5 key: {check_5}\n2. Mốc 20 key: {check_20}\n3. Mốc 30 key: {check_30}")
        bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['info'])
def xem_thong_tin_ca_nhan(message):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if not username:
        bot.reply_to(message, "❌ Bạn cần tạo Username Telegram!")
        return
    
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT keys, rank FROM ctv WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()
    
    if not data:
        bot.reply_to(message, f"❌ Bạn chưa có trong hệ thống!")
        return
        
    keys, rank = data
    next_goal = ""
    if keys < 10: next_goal = f"Cần thêm <b>{10 - keys}</b> key để lên Bạc 🥈"
    elif keys < 25: next_goal = f"Cần thêm <b>{25 - keys}</b> key để lên Vàng 🥇"
    elif keys < 50: next_goal = f"Cần thêm <b>{50 - keys}</b> key để lên Kim Cương 💎"
    elif keys < 100: next_goal = f"Cần thêm <b>{100 - keys}</b> key để lên Kim Cương Cao Cấp 👑"
    else: next_goal = "Bạn đã đạt cảnh giới tối cao! Quá đỉnh! 👽"

    text = (f"👤 <b>THÔNG TIN CỦA: {username}</b>\n\n"
            f"📊 Cấp bậc: <b>{rank}</b>\n"
            f"🔑 Số key: <b>{keys} key</b>\n"
            f"🎯 Mục tiêu: {next_goal}")
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['top'])
def xem_top_3(message):
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute("SELECT username, keys, rank FROM ctv ORDER BY keys DESC LIMIT 3")
    users = c.fetchall()
    conn.close()

    if not users:
        bot.reply_to(message, "📭 Chưa có CTV nào!")
        return

    text = "🔥 <b>TOP 3 CTV XUẤT SẮC NHẤT</b> 🔥\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for idx, user in enumerate(users):
        username, keys, rank = user
        text += f"{medals[idx]} {username} | {rank} | {keys} key\n"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['themctv'])
def them_ctv(message):
    if not is_admin(message): return
    try:
        parts = message.text.split()
        username = parts[1]
        
        conn = sqlite3.connect('ctv_data.db')
        c = conn.cursor()
        c.execute("SELECT username FROM ctv WHERE username=?", (username,))
        if c.fetchone():
            bot.reply_to(message, f"⚠️ {username} đã có trong danh sách!")
        else:
            today = get_today()
            c.execute("INSERT INTO ctv (username, keys, rank, join_date, quote, streak, kudos) VALUES (?, 0, ?, ?, ?, 0, 0)", 
                      (username, "Đồng 🥉", today, "Chưa có châm ngôn..."))
            conn.commit()
            bot.reply_to(message, f"✅ Đã thêm {username} với cấp bậc Đồng 🥉.")
            
            try:
                bot.send_message(username, f"🎉 Chào mừng <b>{username}</b> đã gia nhập hệ thống CTV!\n"
                                            f"Hãy gõ /start để xem các tính năng nhé!", parse_mode='HTML')
            except Exception:
                bot.send_message(message.chat.id, f"⚠️ Không thể gửi tin nhắn chào mừng cho {username} (Do họ chưa start bot).")
        conn.close()
    except Exception:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /themctv @ten")

@bot.message_handler(commands=['congkey'])
def cong_key(message):
    if not is_admin(message): return
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
            new_rank = update_keys(username, new_keys)
            
            bot.reply_to(message, f"✅ Đã cộng {added_keys} key cho {username}.\nTổng: {new_keys} key\nCấp bậc: {new_rank}")
            if old_rank != new_rank and added_keys > 0:
                bot.send_message(message.chat.id, f"🎉 Chúc mừng <b>{username}</b> đã thăng cấp lên <b>{new_rank}</b>!", parse_mode='HTML')
        else:
            bot.reply_to(message, f"❌ Không tìm thấy {username}.")
        conn.close()
    except Exception:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /congkey @ten 5")

@bot.message_handler(commands=['trukey'])
def tru_key(message):
    
