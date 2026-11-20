import os, telebot, sqlite3, random, time
from datetime import datetime, timedelta
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

BOT_TOKEN = '9268542841:AAHJvJtXD7oXLfTlNeUyaSanWH5yni12DhQ'
ADMIN_ID = 8240363472 # SỬA ID CỦA BẠN
BANNER_URL = 'https://i.postimg.cc/G3P8qX0G/file-000000005d588209b919bcce17087b9f.png'

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def get_today(): return datetime.now().strftime("%Y-%m-%d")
def is_admin(msg): return msg.from_user.id == ADMIN_ID
def get_rank(keys):
    if keys >= 100: return "Kim Cương Cao Cấp 👑"
    if keys >= 50: return "Kim Cương 💎"
    if keys >= 25: return "Vàng 🥇"
    if keys >= 10: return "Bạc 🥈"
    return "Đồng 🥉"

def init_db():
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ctv (username TEXT PRIMARY KEY, keys INTEGER, rank TEXT, join_date TEXT, quote TEXT, last_checkin TEXT, streak INTEGER, last_wheel TEXT, kudos INTEGER)''')
    for col in ["join_date TEXT", "quote TEXT", "last_checkin TEXT", "streak INTEGER DEFAULT 0", "last_wheel TEXT", "kudos INTEGER DEFAULT 0"]:
        try: c.execute(f"ALTER TABLE ctv ADD COLUMN {col}")
        except: pass
    conn.commit(); conn.close()
init_db()

def update_keys(username, new_keys):
    new_rank = get_rank(new_keys)
    conn = sqlite3.connect('ctv_data.db')
    conn.execute("UPDATE ctv SET keys=?, rank=? WHERE username=?", (new_keys, new_rank, username))
    conn.commit(); conn.close()
    return new_rank

def get_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🏆 Xếp Hạng", callback_data="menu_xephang"), InlineKeyboardButton("📊 Cấp Bậc", callback_data="menu_capbac"))
    markup.row(InlineKeyboardButton("🎯 Nhiệm Vụ", callback_data="menu_nhiemvu"), InlineKeyboardButton("👤 Thông Tin", callback_data="menu_info"))
    markup.row(InlineKeyboardButton("🎲 Vòng Quay", callback_data="menu_vongquay"), InlineKeyboardButton("📅 Điểm Danh", callback_data="menu_diemdanh"))
    markup.row(InlineKeyboardButton("💳 Hồ Sơ", callback_data="menu_profile"), InlineKeyboardButton("🔥 Top 3", callback_data="menu_top"))
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = "Chào Sếp! Bot quản lý CTV.\n👇 Bấm nút bên dưới hoặc dùng lệnh:\n\n🛠 Lệnh Admin:\n/themctv @ten - Thêm CTV\n/congkey @ten so - Cộng key\n/trukey @ten so - Trừ key\n/xoactv @ten - Xóa CTV\n/thongke - Tổng quan\n/thongbao [nội dung]\n/reset - Reset toàn bộ\n\n🛡 Quản trị nhóm (Cần Reply tin nhắn):\n/kick - Đuổi khỏi nhóm\n/camchat [thời gian] - Cấm chat (VD: 1h, 30m)\n/add - Tạo link mời tham gia" if is_admin(message) else "Chào bạn! Hệ thống quản lý CTV.\n👇 Bấm nút bên dưới hoặc dùng lệnh:\n/vongquay - Quay số nhận key\n/diemdanh - Điểm danh hàng ngày\n/profile - Xem thẻ CTV\n/setquote [châm ngôn]\n/khen @ten - Thả tim"
    try: bot.send_photo(message.chat.id, BANNER_URL, caption=text, parse_mode='HTML', reply_markup=get_menu())
    except Exception as e: 
        print(f"Lỗi ảnh: {e}")
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu(call):
    bot.answer_callback_query(call.id)
    if call.data == 'menu_xephang': xep_hang(call.message)
    elif call.data == 'menu_capbac': xem_cap_bac(call.message)
    elif call.data == 'menu_nhiemvu': nhiem_vu(call.message)
    elif call.data == 'menu_info': xem_info(call.message)
    elif call.data == 'menu_vongquay': vong_quay(call.message)
    elif call.data == 'menu_diemdanh': diem_danh(call.message)
    elif call.data == 'menu_profile': xem_profile(call.message)
    elif call.data == 'menu_top': xem_top_3(call.message)

@bot.message_handler(commands=['xephang'])
def xep_hang(message):
    conn = sqlite3.connect('ctv_data.db')
    users = conn.execute("SELECT username, keys, rank FROM ctv ORDER BY keys DESC").fetchall()
    conn.close()
    if not users: return bot.reply_to(message, "📭 Chưa có CTV nào!")
    text = "🏆 <b>BẢNG XẾP HẠNG</b> 🏆\n\n" + "".join([f"{i}. {u[0]} | {u[2]} | {u[1]} key\n" for i, u in enumerate(users, 1)])
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['capbac'])
def xem_cap_bac(message):
    conn = sqlite3.connect('ctv_data.db')
    users = conn.execute("SELECT username, rank, keys FROM ctv ORDER BY keys DESC").fetchall()
    conn.close()
    if not users: return bot.reply_to(message, "📭 Chưa có CTV nào!")
    text = "📊 <b>CẤP BẬC CTV</b> 📊\n\n" + "".join([f"👤 {u[0]}: <b>{u[1]}</b> ({u[2]} key)\n" for u in users])
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['top'])
def xem_top_3(message):
    conn = sqlite3.connect('ctv_data.db')
    users = conn.execute("SELECT username, keys, rank FROM ctv ORDER BY keys DESC LIMIT 3").fetchall()
    conn.close()
    if not users: return bot.reply_to(message, "📭 Chưa có CTV nào!")
    medals = ["🥇", "🥈", "🥉"]
    text = "🔥 <b>TOP 3 XUẤT SẮC</b> 🔥\n\n" + "".join([f"{medals[i]} {u[0]} | {u[2]} | {u[1]} key\n" for i, u in enumerate(users)])
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['nhiemvu'])
def nhiem_vu(message):
    parts = message.text.split()
    if len(parts) == 1:
        return bot.reply_to(message, "🎯 <b>NHIỆM VỤ</b>\n\n1. Bán 5 key\n2. Bán 20 key\n3. Bán 30 key\n\n👉 Xem tiến độ: <code>/nhiemvu @ten</code>", parse_mode='HTML')
    conn = sqlite3.connect('ctv_data.db')
    data = conn.execute("SELECT keys FROM ctv WHERE username=?", (parts[1],)).fetchone()
    conn.close()
    if not data: return bot.reply_to(message, f"❌ Không tìm thấy {parts[1]}!")
    k = data[0]
    text = f"🎯 <b>TIẾN ĐỘ CỦA {parts[1]}</b>\n\n📊 Tổng: <b>{k} key</b>\n\n1. Mốc 5: {'✅' if k >= 5 else f'❌ Thiếu {5-k}'}\n2. Mốc 20: {'✅' if k >= 20 else f'❌ Thiếu {20-k}'}\n3. Mốc 30: {'✅' if k >= 30 else f'❌ Thiếu {30-k}'}"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['info'])
def xem_info(message):
    uname = f"@{message.from_user.username}" if message.from_user.username else None
    if not uname: return bot.reply_to(message, "❌ Bạn cần tạo Username Telegram!")
    conn = sqlite3.connect('ctv_data.db')
    data = conn.execute("SELECT keys, rank FROM ctv WHERE username=?", (uname,)).fetchone()
    conn.close()
    if not data: return bot.reply_to(message, "❌ Bạn chưa có trong hệ thống!")
    k, r = data
    goal = f"{10-k} key lên Bạc" if k < 10 else f"{25-k} key lên Vàng" if k < 25 else f"{50-k} key lên Kim Cương" if k < 50 else f"{100-k} key lên KC Cao Cấp" if k < 100 else "Đã đạt tối cao!"
    bot.reply_to(message, f"👤 <b>THÔNG TIN: {uname}</b>\n\n📊 Cấp: <b>{r}</b>\n🔑 Key: <b>{k}</b>\n🎯 Mục tiêu: Cần thêm {goal}", parse_mode='HTML')

@bot.message_handler(commands=['profile'])
def xem_profile(message):
    uname = f"@{message.from_user.username}" if message.from_user.username else None
    if not uname: return
    conn = sqlite3.connect('ctv_data.db')
    data = conn.execute("SELECT keys, rank, join_date, quote, kudos FROM ctv WHERE username=?", (uname,)).fetchone()
    conn.close()
    if not data: return bot.reply_to(message, "❌ Bạn chưa có trong hệ thống!")
    k, r, jd, q, kd = data[0], data[1], data[2] or "Không rõ", data[3] or "Chưa có...", data[4] or 0
    text = f"💳 <b>THẺ CĂN CƯỚC CTV</b> 💳\n-------------------\n👤 <b>Chủ thẻ:</b> {uname}\n📅 <b>Gia nhập:</b> {jd}\n🏅 <b>Cấp bậc:</b> {r}\n🔑 <b>Key:</b> {k}\n💖 <b>Khen:</b> {kd}\n-------------------\n💬 <b>Châm ngôn:</b> <i>\"{q}\"</i>"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['setquote'])
def set_quote(message):
    uname = f"@{message.from_user.username}" if message.from_user.username else None
    if not uname: return
    txt = message.text.replace('/setquote', '').strip()
    if not txt or len(txt) > 50: return bot.reply_to(message, "❌ Châm ngôn phải từ 1-50 ký tự!")
    conn = sqlite3.connect('ctv_data.db')
    conn.execute("UPDATE ctv SET quote=? WHERE username=?", (txt, uname))
    conn.commit(); conn.close()
    bot.reply_to(message, f"✅ Đã đổi châm ngôn: <i>\"{txt}\"</i>", parse_mode='HTML')

@bot.message_handler(commands=['vongquay'])
def vong_quay(message):
    uname = f"@{message.from_user.username}" if message.from_user.username else None
    if not uname: return
    conn = sqlite3.connect('ctv_data.db')
    data = conn.execute("SELECT keys, last_wheel FROM ctv WHERE username=?", (uname,)).fetchone()
    if not data: return bot.reply_to(message, "❌ Chưa có trong hệ thống!")
    k, lw = data
    if lw == get_today(): return bot.reply_to(message, "⏳ Mai quay lại nhé!")
    won = random.choices([0, 1, 1, 3, 5], weights=[40, 30, 15, 10, 5], k=1)[0]
    nr = update_keys(uname, k + won)
    conn.execute("UPDATE ctv SET last_wheel=? WHERE username=?", (get_today(), uname))
    conn.commit(); conn.close()
    bot.reply_to(message, f"🎲 Kết quả: <b>{won} key</b>!\nTổng: {k+won} key ({nr})", parse_mode='HTML')

@bot.message_handler(commands=['diemdanh'])
def diem_danh(message):
    uname = f"@{message.from_user.username}" if message.from_user.username else None
    if not uname: return
    conn = sqlite3.connect('ctv_data.db')
    data = conn.execute("SELECT keys, last_checkin, streak FROM ctv WHERE username=?", (uname,)).fetchone()
    if not data: return bot.reply_to(message, "❌ Chưa có trong hệ thống!")
    k, lc, st = data[0], data[1], data[2] or 0
    if lc == get_today(): return bot.reply_to(message, "⏳ Hôm nay đã điểm danh rồi!")
    st = st + 1 if lc == (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") else 1
    add = 1
    bonus = ""
    if st >= 7: add += 5; bonus = "\n🔥 Chuỗi 7 ngày! Thưởng +5 key!"; st = 0
    nr = update_keys(uname, k + add)
    conn.execute("UPDATE ctv SET last_checkin=?, streak=? WHERE username=?", (get_today(), st, uname))
    conn.commit(); conn.close()
    bot.reply_to(message, f"✅ Điểm danh nhận <b>{add} key</b>! (Chuỗi: {st}/7){bonus}\nTổng: {k+add} key ({nr})", parse_mode='HTML')

@bot.message_handler(commands=['khen'])
def khen(message):
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "❌ Cú pháp: /khen @ten")
    target, me = parts[1], f"@{message.from_user.username}"
    if target == me: return bot.reply_to(message, "🤦 Không tự khen mình được!")
    conn = sqlite3.connect('ctv_data.db')
    data = conn.execute("SELECT kudos FROM ctv WHERE username=?", (target,)).fetchone()
    if not data: return bot.reply_to(message, f"❌ Không tìm thấy {target}!")
    kd = (data[0] or 0) + 1
    conn.execute("UPDATE ctv SET kudos=? WHERE username=?", (kd, target))
    conn.commit(); conn.close()
    bot.reply_to(message, f"💖 <b>{me}</b> đã khen <b>{target}</b>! (Tổng: {kd})", parse_mode='HTML')

@bot.message_handler(commands=['thongbao'])
def thong_bao(message):
    if not is_admin(message): return
    txt = message.text.replace('/thongbao', '').strip()
    if not txt: return
    conn = sqlite3.connect('ctv_data.db')
    users = conn.execute("SELECT username FROM ctv").fetchall()
    conn.close()
    s, f = 0, 0
    for u in users:
        try: bot.send_message(u[0], f"📢 <b>THÔNG BÁO</b> 📢\n\n{txt}", parse_mode='HTML'); s += 1; time.sleep(0.1)
        except: f += 1
    bot.reply_to(message, f"✅ Gửi thành công: {s}. Thất bại: {f}.")

@bot.message_handler(commands=['themctv'])
def them_ctv(message):
    if not is_admin(message): return
    try:
        uname = message.text.split()[1]
        conn = sqlite3.connect('ctv_data.db')
        if conn.execute("SELECT username FROM ctv WHERE username=?", (uname,)).fetchone(): return bot.reply_to(message, "⚠️ Đã có trong danh sách!")
        conn.execute("INSERT INTO ctv (username, keys, rank, join_date) VALUES (?, 0, ?, ?)", (uname, "Đồng 🥉", get_today()))
        conn.commit(); conn.close()
        bot.reply_to(message, f"✅ Đã thêm {uname}.")
        try: bot.send_message(uname, "🎉 Chào mừng bạn gia nhập hệ thống CTV! Gõ /start để xem tính năng.")
        except: bot.reply_to(message, f"⚠️ Không thể gửi tin chào mừng (Do {uname} chưa start bot).")
    except: bot.reply_to(message, "❌ Cú pháp: /themctv @ten")

@bot.message_handler(commands=['congkey', 'trukey'])
def thay_doi_key(message):
    if not is_admin(message): return
    try:
        cmd, uname, num = message.text.split()
        num = int(num) if cmd == '/congkey' else -int(num)
        conn = sqlite3.connect('ctv_data.db')
        data = conn.execute("SELECT keys FROM ctv WHERE username=?", (uname,)).fetchone()
        if not data: return bot.reply_to(message, f"❌ Không tìm thấy {uname}!")
        old_r = get_rank(data[0])
        new_k = max(0, data[0] + num)
        new_r = update_keys(uname, new_k)
        conn.close()
        bot.reply_to(message, f"✅ Đã cập nhật {num} key cho {uname}.\nTổng: {new_k} ({new_r})")
        if old_r != new_r and num > 0: bot.send_message(message.chat.id, f"🎉 Chúc mừng <b>{uname}</b> thăng cấp <b>{new_r}</b>!", parse_mode='HTML')
    except: bot.reply_to(message, "❌ Cú pháp: /congkey (hoặc /trukey) @ten so_key")

@bot.message_handler(commands=['xoactv'])
def xoa_ctv(message):
    if not is_admin(message): return
    try:
        uname = message.text.split()[1]
        conn = sqlite3.connect('ctv_data.db')
        conn.execute("DELETE FROM ctv WHERE username=?", (uname,))
        conn.commit(); conn.close()
        bot.reply_to(message, f"🗑 Đã xóa {uname}!")
    except: bot.reply_to(message, "❌ Cú pháp: /xoactv @ten")

@bot.message_handler(commands=['thongke'])
def thong_ke(message):
    if not is_admin(message): return
    conn = sqlite3.connect('ctv_data.db')
    total = conn.execute("SELECT COUNT(*), SUM(keys) FROM ctv").fetchone()
    top1 = conn.execute("SELECT username, keys FROM ctv ORDER BY keys DESC LIMIT 1").fetchone()
    conn.close()
    text = f"📈 <b>THỐNG KÊ</b>\n\n👥 Tổng CTV: <b>{total[0]}</b>\n🔑 Tổng Key: <b>{total[1] or 0}</b>\n\n"
    if top1: text += f"🥇 Top 1: {top1[0]} ({top1[1]} key)"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['reset'])
def reset(message):
    if not is_admin(message): return
    conn = sqlite3.connect('ctv_data.db')
    conn.execute("UPDATE ctv SET keys=0, rank='Đồng 🥉', streak=0, kudos=0")
    conn.commit(); conn.close()
    bot.reply_to(message, "🧹 Đã reset toàn bộ!")

# ================= QUẢN TRỊ NHÓM =================
def parse_time(time_str):
    try:
        unit = time_str[-1].lower()
        val = int(time_str[:-1])
        if unit == 'm': return val * 60
        if unit == 'h': return val * 3600
        if unit == 'd': return val * 86400
        return val 
    except: return 60 

@bot.message_handler(commands=['kick'])
def kick_user(message):
    if not is_admin(message): return
    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Hãy Reply (trả lời) tin nhắn của người muốn kick và gõ /kick")
    try:
        bot.kick_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, f"👢 Đã đuổi {message.reply_to_message.from_user.first_name} khỏi nhóm!")
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi (Bot cần quyền Admin): {e}")

@bot.message_handler(commands=['camchat'])
def mute_user(message):
    if not is_admin(message): return
    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Hãy Reply tin nhắn của người đó và gõ:\n/camchat [thời gian]\n(VD: /camchat 1h, /camchat 30m)")
    try:
        parts = message.text.split()
        if len(parts) < 2: return bot.reply_to(message, "❌ Thiếu thời gian! VD: /camchat 1h")
        duration = parse_time(parts[1])
        until = int(time.time()) + duration
        perms = ChatPermissions(can_send_messages=False)
        
        bot.restrict_chat_member(
            chat_id=message.chat.id, 
            user_id=message.reply_to_message.from_user.id, 
            permissions=perms, 
            until_date=until
        )
        
        bot.reply_to(message, f"🤐 Đã cấm chat {message.reply_to_message.from_user.first_name} trong {parts[1]}!")
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['add'])
def add_user(message):
    if not is_admin(message): return
    try:
        link = bot.create_chat_invite_link(message.chat.id, member_limit=1)
        bot.reply_to(message, f"🔗 Link mời tham gia nhóm (chỉ dùng được 1 lần):\n{link.invite_link}\n\nHãy gửi link này cho người cần thêm vào nhóm.")
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi (Bot cần quyền Admin tạo link mời): {e}")

# ================= WEBHOOK =================
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{os.environ.get('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}")
    return "Bot đang chạy!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
