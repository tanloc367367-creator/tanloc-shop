import os, telebot, sqlite3, random, time, string
from datetime import datetime, timedelta
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

BOT_TOKEN = '9268542841:AAHJvJtXD7oXLfTlNeUyaSanWH5yni12DhQ' # ĐỔI TOKEN MỚI
ADMIN_ID = 8240363472
BANNER_URL = 'https://i.postimg.cc/G3P8qX0G/file-000000005d588209b919bcce17087b9f.png'
GAME_BANNER_URL = 'https://i.postimg.cc/nztdrLpQ/file-0000000089dc8211b7bef528f2d9543b.png' # THAY LINK ẢNH GAME VÀO ĐÂY

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
game_data = {} 
temp_lixi_data = {} 

def get_today(): return datetime.now().strftime("%Y-%m-%d")
def is_admin(msg): return msg.from_user.id == ADMIN_ID
def get_uname(msg): return f"@{msg.from_user.username}" if msg.from_user.username else None

def get_rank(k):
    if k >= 100: return "Kim Cương Cao Cấp 👑"
    if k >= 50: return "Kim Cương 💎"
    if k >= 25: return "Vàng 🥇"
    if k >= 10: return "Bạc 🥈"
    return "Đồng 🥉"

def db_query(query, params=(), fetch=False, commit=False):
    conn = sqlite3.connect('ctv_data.db')
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchone() if fetch == 'one' else c.fetchall() if fetch == 'all' else None
    if commit: conn.commit()
    conn.close()
    return res

# Khởi tạo DB
db_query('''CREATE TABLE IF NOT EXISTS ctv (username TEXT PRIMARY KEY, chat_id INTEGER, keys INTEGER, xu INTEGER DEFAULT 0, rank TEXT, join_date TEXT, quote TEXT, last_checkin TEXT, streak INTEGER, last_wheel TEXT, kudos INTEGER, last_xinxu TEXT, last_baohiem TEXT)''')
for col in ["chat_id INTEGER", "join_date TEXT", "quote TEXT", "last_checkin TEXT", "streak INTEGER DEFAULT 0", "last_wheel TEXT", "kudos INTEGER DEFAULT 0", "next_tx TEXT", "xu INTEGER DEFAULT 0", "next_doanso TEXT", "next_rps TEXT", "next_dovui TEXT", "next_latthe TEXT", "last_xinxu TEXT", "last_baohiem TEXT"]:
    try: db_query(f"ALTER TABLE ctv ADD COLUMN {col}", commit=True)
    except: pass

# Bảng Lì Xì
db_query('''CREATE TABLE IF NOT EXISTS lixi (code TEXT PRIMARY KEY, creator TEXT, loai TEXT, tong_gia_tri INTEGER, con_lai INTEGER, so_nguoi INTEGER, da_nhan INTEGER DEFAULT 0, status TEXT DEFAULT 'active')''')

def update_keys(uname, new_keys):
    rank = get_rank(new_keys)
    db_query("UPDATE ctv SET keys=?, rank=? WHERE username=?", (new_keys, rank, uname), commit=True)
    return rank

def update_xu(uname, amount):
    db_query("UPDATE ctv SET xu = xu + ? WHERE username=?", (amount, uname), commit=True)

def check_user(msg):
    uname = get_uname(msg)
    if not uname: 
        bot.reply_to(msg, "❌ Bạn cần tạo Username Telegram!"); return None
    data = db_query("SELECT keys, xu FROM ctv WHERE username=?", (uname,), fetch='one')
    if not data: 
        bot.reply_to(msg, "❌ Bạn chưa có trong hệ thống! Hãy gõ /start trước."); return None
    return uname, data[0], data[1]

# ================= MENU =================
def get_menu():
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("🏆 Xếp Hạng Key", callback_data="menu_xephang"), InlineKeyboardButton("💰 Top Đại Gia", callback_data="menu_topxu"))
    m.row(InlineKeyboardButton("📊 Cấp Bậc", callback_data="menu_capbac"), InlineKeyboardButton("👤 Thông Tin", callback_data="menu_info"))
    m.row(InlineKeyboardButton("🎲 Vòng Quay", callback_data="menu_vongquay"), InlineKeyboardButton("📅 Điểm Danh", callback_data="menu_diemdanh"))
    m.row(InlineKeyboardButton("🎮 GAME GIẢI TRÍ", callback_data="menu_game"))
    m.row(InlineKeyboardButton("💳 Hồ Sơ", callback_data="menu_profile"), InlineKeyboardButton("🎯 Nhiệm Vụ", callback_data="menu_nhiemvu"))
    return m

def get_game_menu():
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("🎰 Tài Xỉu", callback_data="game_taixiu"), InlineKeyboardButton("🔢 Đoán Số", callback_data="game_doanso"))
    m.row(InlineKeyboardButton("✂️ Búa Kéo Bao", callback_data="game_keobuabao"), InlineKeyboardButton("❓ Đố Vui", callback_data="game_dovui"))
    m.row(InlineKeyboardButton("💣 Lật Thẻ", callback_data="game_latthe"))
    return m

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    uname = get_uname(message)
    if uname:
        check = db_query("SELECT chat_id FROM ctv WHERE username=?", (uname,), fetch='one')
        if check:
            db_query("UPDATE ctv SET chat_id=? WHERE username=?", (message.chat.id, uname), commit=True)
            if not check[0]: bot.reply_to(message, f"🎉 Chào mừng <b>{uname}</b> đã kích hoạt tài khoản!", parse_mode='HTML')
        else:
            db_query("INSERT INTO ctv (username, chat_id, keys, xu, rank, join_date) VALUES (?, ?, 0, 0, ?, ?)", (uname, message.chat.id, "Đồng 🥉", get_today()), commit=True)

    text = ("Chào Sếp! Bot quản lý CTV.\n👇 Bấm nút bên dưới hoặc dùng lệnh:\n\n🛠 Lệnh Admin:\n/themctv /congkey /trukey /congxu /truxu /xoactv /thongke /thongbao /reset\n/soicau [ten_game]\n\n🧧 Lì Xì:\n/guilixi - Tạo túi lì xì\n/bulixi [mã] - Nhận lì xì\n\n🛡 Quản trị nhóm:\n/kick /camchat /add\n\n🎮 Gõ /game để xem các game giải trí (Dùng Xu)!" if is_admin(message) else "Chào bạn! Hệ thống quản lý CTV.\n👇 Bấm nút bên dưới hoặc dùng lệnh:\n/vongquay /diemdanh /profile /setquote /khen\n💸 /chuyenxu /chuyenkey - Chuyển tiền\n🎁 /xinxu /baohiem - Cứu trợ\n🧧 /bulixi [mã] - Nhận lì xì\n/game - Kho game giải trí\n👉 Cú pháp chơi game: /tengame [số xu]")
    try: bot.send_photo(message.chat.id, BANNER_URL, caption=text, parse_mode='HTML', reply_markup=get_menu())
    except: bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu(call):
    bot.answer_callback_query(call.id)
    actions = {
        'menu_xephang': xep_hang, 'menu_capbac': xem_cap_bac, 'menu_nhiemvu': nhiem_vu,
        'menu_info': xem_info, 'menu_vongquay': vong_quay, 'menu_diemdanh': diem_danh,
        'menu_profile': xem_profile, 'menu_top': xem_top_3, 'menu_game': menu_game,
        'menu_topxu': top_dai_gia
    }
    if call.data in actions: actions[call.data](call.message)

@bot.message_handler(commands=['game'])
def menu_game(message):
    text = ("🎮 <b>TỔNG HỢP GAME GIẢI TRÍ</b> 🎮\n"
            "👉 <b>Cú pháp:</b> /tengame [số xu cược]\n"
            "Ví dụ: <code>/taixiu 10</code> (Chơi Tài Xỉu cược 10 xu)\n\n"
            "🎰 <b>Tài Xỉu:</b> Đoán Tài (11-18) hoặc Xỉu (3-10).\n"
            "🔢 <b>Đoán Số:</b> Đoán số từ 1-50.\n"
            "✂️ <b>Búa Kéo Bao:</b> Đấu với Bot.\n"
            "❓ <b>Đố Vui:</b> Trả lời câu hỏi.\n"
            "💣 <b>Lật Thẻ:</b> Né 3 quả boom.")
    try: bot.send_photo(message.chat.id, GAME_BANNER_URL, caption=text, parse_mode='HTML', reply_markup=get_game_menu())
    except: bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_game_menu())

# ================= TÍNH NĂNG CHUYỂN TIỀN =================
@bot.message_handler(commands=['chuyenxu', 'chuyenkey'])
def chuyen_tien(message):
    u = check_user(message)
    if not u: return
    sender, sender_keys, sender_xu = u
    
    parts = message.text.split()
    if len(parts) < 3: return bot.reply_to(message, f"❌ Cú pháp: /{parts[0][1:]} @ten_nguoi_nhan so_luong")
    
    target, amount = parts[1], parts[2]
    if not amount.isdigit(): return bot.reply_to(message, "❌ Số lượng phải là số nguyên dương!")
    amount = int(amount)
    if amount <= 0: return bot.reply_to(message, "❌ Số lượng phải lớn hơn 0!")
    if target == sender: return bot.reply_to(message, "🤦 Không thể tự chuyển cho mình!")
    
    receiver = db_query("SELECT username FROM ctv WHERE username=?", (target,), fetch='one')
    if not receiver: return bot.reply_to(message, f"❌ Không tìm thấy người dùng {target}!")
    
    is_key = 'key' in parts[0]
    loai = "Key" if is_key else "Xu"
    icon = "🔑" if is_key else "🪙"
    
    if is_key:
        if sender_keys < amount: return bot.reply_to(message, f"❌ Bạn không đủ Key! (Bạn có {sender_keys})")
        update_keys(sender, sender_keys - amount)
        old_r = db_query("SELECT keys FROM ctv WHERE username=?", (target,), fetch='one')[0]
        update_keys(target, old_r + amount)
        sender_after, receiver_after = sender_keys - amount, old_r + amount
    else:
        if sender_xu < amount: return bot.reply_to(message, f"❌ Bạn không đủ Xu! (Bạn có {sender_xu})")
        update_xu(sender, -amount)
        old_r = db_query("SELECT xu FROM ctv WHERE username=?", (target,), fetch='one')[0]
        update_xu(target, amount)
        sender_after, receiver_after = sender_xu - amount, old_r + amount

    text = (f"💸 <b>{sender}</b> ĐÃ CHUYỂN CHO <b>{target}</b> 💸\n\n"
            f"📉 <b>SỐ DƯ BIẾN ĐỘNG:</b>\n"
            f"👤 {sender}: {sender_keys if is_key else sender_xu} {icon} ➡️ {sender_after} {icon}\n"
            f"👤 {target}: {old_r} {icon} ➡️ {receiver_after} {icon}\n\n"
            f"🪎 <b>CHUYỂN THÀNH CÔNG!</b>")
    bot.reply_to(message, text, parse_mode='HTML')

# ================= TÍNH NĂNG CỨU TRỢ =================
@bot.message_handler(commands=['xinxu'])
def xin_xu(message):
    u = check_user(message)
    if not u: return
    uname = u[0]
    
    last_xin = db_query("SELECT last_xinxu FROM ctv WHERE username=?", (uname,), fetch='one')[0]
    if last_xin == get_today(): return bot.reply_to(message, "⏳ Hôm nay bạn đã xin xu rồi! Mai quay lại nhé.")
    
    amount = random.randint(1, 200)
    update_xu(uname, amount)
    db_query("UPDATE ctv SET last_xinxu=? WHERE username=?", (get_today(), uname), commit=True)
    bot.reply_to(message, f"🎁 Bạn đã xin được <b>{amount} xu</b> từ hệ thống!\nHãy chăm chỉ chơi game để kiếm thêm nhé.", parse_mode='HTML')

@bot.message_handler(commands=['baohiem'])
def bao_hiem(message):
    u = check_user(message)
    if not u: return
    uname, k, x = u
    
    last_bh = db_query("SELECT last_baohiem FROM ctv WHERE username=?", (uname,), fetch='one')[0]
    if last_bh == get_today(): return bot.reply_to(message, "⏳ Hôm nay bạn đã nhận bảo hiểm rồi! Mai quay lại nhé.")
    
    if x >= 100: return bot.reply_to(message, f"❌ Bạn đang có {x} xu (trên 100), không đủ điều kiện nhận bảo hiểm!")
    
    amount = 100
    update_xu(uname, amount)
    db_query("UPDATE ctv SET last_baohiem=? WHERE username=?", (get_today(), uname), commit=True)
    bot.reply_to(message, f"🛡 Bạn đã nhận được <b>{amount} xu</b> bảo hiểm. Hãy chơi game thông minh hơn nhé!", parse_mode='HTML')

# ================= TÍNH NĂNG VÒNG QUAY NÂNG CẤP =================
@bot.message_handler(commands=['vongquay'])
def vong_quay(message):
    u = check_user(message)
    if not u: return
    uname, k, x = u
    parts = message.text.split()
    
    if len(parts) == 1:
        # Vòng quay free 1 lần/ngày
        lw = db_query("SELECT last_wheel FROM ctv WHERE username=?", (uname,), fetch='one')[0]
        if lw == get_today(): return bot.reply_to(message, "⏳ Hôm nay bạn đã quay miễn phí rồi!\n👉 Nếu muốn quay tiếp, hãy cược xu: /vongquay [số xu]")
        
        won = random.choices([0, 1, 1, 3, 5], weights=[40, 30, 15, 10, 5], k=1)[0]
        update_xu(uname, won)
        db_query("UPDATE ctv SET last_wheel=? WHERE username=?", (get_today(), uname), commit=True)
        bot.reply_to(message, f"🎲 <b>VÒNG QUAY MIỄN PHÍ</b>\nKết quả: <b>{won} xu</b>!\nTổng: {x+won} xu", parse_mode='HTML')
    else:
        # Vòng quay cược xu
        try: cost = int(parts[1])
        except: return bot.reply_to(message, "❌ Số xu cược không hợp lệ!")
        if cost < 10: return bot.reply_to(message, "❌ Cược tối thiểu là 10 xu!")
        if x < cost: return bot.reply_to(message, f"❌ Bạn không đủ {cost} xu! (Bạn có {x} xu)")
        
        multiplier = random.choices([0, 1.5, 2, 5], weights=[50, 25, 20, 5], k=1)[0]
        won = int(cost * multiplier)
        update_xu(uname, won - cost)
        
        if multiplier == 0:
            bot.reply_to(message, f"🎲 <b>VÒNG QUAY MAY MẮN</b>\nBạn cược {cost} xu.\nKết quả: <b>TRƯỢT (Mất {cost} xu)</b>\nTổng: {x - cost} xu", parse_mode='HTML')
        else:
            bot.reply_to(message, f"🎲 <b>VÒNG QUAY MAY MẮN</b>\nBạn cược {cost} xu.\nKết quả: Hệ số <b>x{multiplier}</b>!\nThắng nhận: <b>{won} xu</b>.\nTổng: {x - cost + won} xu", parse_mode='HTML')

# ================= LỆNH TÍNH NĂNG KHÁC =================
@bot.message_handler(commands=['xephang'])
def xep_hang(message):
    users = db_query("SELECT username, keys, xu, rank FROM ctv ORDER BY keys DESC", fetch='all')
    text = "🏆 <b>BẢNG XẾP HẠNG (THEO KEY)</b> 🏆\n\n" + "".join([f"{i}. {u[0]} | {u[3]} | {u[1]} key\n" for i, u in enumerate(users, 1)]) if users else "📭 Chưa có CTV nào!"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['topxu'])
def top_dai_gia(message):
    users = db_query("SELECT username, xu FROM ctv ORDER BY xu DESC LIMIT 5", fetch='all')
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    text = "💰 <b>TOP 5 ĐẠI GIA (XU)</b> 💰\n\n" + "".join([f"{medals[i]} {u[0]}: <b>{u[1]} xu</b>\n" for i, u in enumerate(users)]) if users else "📭 Chưa có ai có xu!"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['capbac'])
def xem_cap_bac(message):
    users = db_query("SELECT username, rank, keys FROM ctv ORDER BY keys DESC", fetch='all')
    text = "📊 <b>CẤP BẬC CTV</b> 📊\n\n" + "".join([f"👤 {u[0]}: <b>{u[1]}</b> ({u[2]} key)\n" for u in users]) if users else "📭 Chưa có CTV nào!"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['top'])
def xem_top_3(message):
    users = db_query("SELECT username, keys, rank FROM ctv ORDER BY keys DESC LIMIT 3", fetch='all')
    medals = ["🥇", "🥈", "🥉"]
    text = "🔥 <b>TOP 3 XUẤT SẮC</b> 🔥\n\n" + "".join([f"{medals[i]} {u[0]} | {u[2]} | {u[1]} key\n" for i, u in enumerate(users)]) if users else "📭 Chưa có CTV nào!"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['nhiemvu'])
def nhiem_vu(message):
    parts = message.text.split()
    if len(parts) == 1: return bot.reply_to(message, "🎯 <b>NHIỆM VỤ</b>\n\n1. Bán 5 key\n2. Bán 20 key\n3. Bán 30 key\n\n👉 Xem: <code>/nhiemvu @ten</code>", parse_mode='HTML')
    data = db_query("SELECT keys FROM ctv WHERE username=?", (parts[1],), fetch='one')
    if not data: return bot.reply_to(message, f"❌ Không tìm thấy {parts[1]}!")
    k = data[0]
    bot.reply_to(message, f"🎯 <b>TIẾN ĐỘ CỦA {parts[1]}</b>\n\n📊 Tổng: <b>{k} key</b>\n\n1. Mốc 5: {'✅' if k >= 5 else f'❌ Thiếu {5-k}'}\n2. Mốc 20: {'✅' if k >= 20 else f'❌ Thiếu {20-k}'}\n3. Mốc 30: {'✅' if k >= 30 else f'❌ Thiếu {30-k}'}", parse_mode='HTML')

@bot.message_handler(commands=['info'])
def xem_info(message):
    u = check_user(message)
    if not u: return
    k, x = db_query("SELECT keys, xu FROM ctv WHERE username=?", (u[0],), fetch='one')
    r = get_rank(k)
    goal = f"{10-k} key lên Bạc" if k < 10 else f"{25-k} key lên Vàng" if k < 25 else f"{50-k} key lên Kim Cương" if k < 50 else f"{100-k} key lên KC Cao Cấp" if k < 100 else "Đã đạt tối cao!"
    bot.reply_to(message, f"👤 <b>THÔNG TIN: {u[0]}</b>\n\n📊 Cấp: <b>{r}</b>\n🔑 Key: <b>{k}</b>\n🪙 Xu: <b>{x}</b>\n🎯 Mục tiêu: Cần thêm {goal}", parse_mode='HTML')

@bot.message_handler(commands=['profile'])
def xem_profile(message):
    u = check_user(message)
    if not u: return
    data = db_query("SELECT keys, xu, rank, join_date, quote, kudos FROM ctv WHERE username=?", (u[0],), fetch='one')
    k, x, r, jd, q, kd = data[0], data[1], data[2], data[3] or "Không rõ", data[4] or "Chưa có...", data[5] or 0
    bot.reply_to(message, f"💳 <b>THẺ CĂN CƯỚC CTV</b> 💳\n-------------------\n👤 <b>Chủ thẻ:</b> {u[0]}\n📅 <b>Gia nhập:</b> {jd}\n🏅 <b>Cấp bậc:</b> {r}\n🔑 <b>Key:</b> {k}\n🪙 <b>Xu:</b> {x}\n💖 <b>Khen:</b> {kd}\n-------------------\n💬 <b>Châm ngôn:</b> <i>\"{q}\"</i>", parse_mode='HTML')

@bot.message_handler(commands=['setquote'])
def set_quote(message):
    u = get_uname(message)
    if not u: return
    txt = message.text.replace('/setquote', '').strip()
    if not txt or len(txt) > 50: return bot.reply_to(message, "❌ Châm ngôn phải từ 1-50 ký tự!")
    db_query("UPDATE ctv SET quote=? WHERE username=?", (txt, u), commit=True)
    bot.reply_to(message, f"✅ Đã đổi châm ngôn: <i>\"{txt}\"</i>", parse_mode='HTML')

@bot.message_handler(commands=['diemdanh'])
def diem_danh(message):
    u = check_user(message)
    if not u: return
    uname, k, x = u
    lc, st = db_query("SELECT last_checkin, streak FROM ctv WHERE username=?", (uname,), fetch='one')
    if lc == get_today(): return bot.reply_to(message, "⏳ Hôm nay đã điểm danh rồi!")
    st = st + 1 if lc == (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") else 1
    add = 1; bonus = ""
    if st >= 7: add += 5; bonus = "\n🔥 Chuỗi 7 ngày! Thưởng +5 xu!"; st = 0
    update_xu(uname, add)
    db_query("UPDATE ctv SET last_checkin=?, streak=? WHERE username=?", (get_today(), st, uname), commit=True)
    bot.reply_to(message, f"✅ Điểm danh nhận <b>{add} xu</b>! (Chuỗi: {st}/7){bonus}\nTổng: {x+add} xu", parse_mode='HTML')

@bot.message_handler(commands=['khen'])
def khen(message):
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "❌ Cú pháp: /khen @ten")
    target, me = parts[1], get_uname(message)
    if target == me: return bot.reply_to(message, "🤦 Không tự khen mình được!")
    data = db_query("SELECT kudos FROM ctv WHERE username=?", (target,), fetch='one')
    if not data: return bot.reply_to(message, f"❌ Không tìm thấy {target}!")
    kd = (data[0] or 0) + 1
    db_query("UPDATE ctv SET kudos=? WHERE username=?", (kd, target), commit=True)
    bot.reply_to(message, f"💖 <b>{me}</b> đã khen <b>{target}</b>! (Tổng: {kd})", parse_mode='HTML')

@bot.message_handler(commands=['thongbao'])
def thong_bao(message):
    if not is_admin(message): return
    txt = message.text.replace('/thongbao', '').strip()
    if not txt: return
    users = db_query("SELECT username, chat_id FROM ctv", fetch='all')
    s, f, failed = 0, 0, []
    for uname, chat_id in users:
        try: 
            bot.send_message(chat_id or uname, f"📢 <b>THÔNG BÁO</b> 📢\n\n{txt}", parse_mode='HTML')
            s += 1; time.sleep(0.1)
        except: f += 1; failed.append(uname)
    msg = f"✅ Gửi thành công: {s}.\n❌ Thất bại: {f}."
    if failed: msg += f"\n👉 Chưa bấm /start: {', '.join(failed)}"
    bot.reply_to(message, msg)

# ================= LỆNH ADMIN =================
@bot.message_handler(commands=['themctv', 'xoactv', 'congkey', 'trukey', 'congxu', 'truxu', 'thongke', 'reset'])
def admin_commands(message):
    if not is_admin(message): return
    cmd = message.text.split()[0].replace('/', '')
    try:
        if cmd == 'themctv':
            uname = message.text.split()[1]
            if db_query("SELECT username FROM ctv WHERE username=?", (uname,), fetch='one'): return bot.reply_to(message, "⚠️ Đã có trong danh sách!")
            db_query("INSERT INTO ctv (username, keys, xu, rank, join_date) VALUES (?, 0, 0, ?, ?)", (uname, "Đồng 🥉", get_today()), commit=True)
            bot.reply_to(message, f"✅ Đã thêm {uname}.")
            chat_id = db_query("SELECT chat_id FROM ctv WHERE username=?", (uname,), fetch='one')[0]
            if chat_id: 
                bot.send_message(chat_id, f"🎉 Chào mừng <b>{uname}</b>! Gõ /start để xem tính năng.", parse_mode='HTML')
            else: 
                bot.reply_to(message, f"💡 {uname} chưa bấm /start.")
        
        elif cmd == 'xoactv':
            db_query("DELETE FROM ctv WHERE username=?", (message.text.split()[1],), commit=True)
            bot.reply_to(message, "🗑 Đã xóa!")
        
        elif cmd in ['congkey', 'trukey']:
            uname, num = message.text.split()[1], message.text.split()[2]
            num = int(num) if cmd == 'congkey' else -int(num)
            data = db_query("SELECT keys FROM ctv WHERE username=?", (uname,), fetch='one')
            if not data: return bot.reply_to(message, f"❌ Không tìm thấy {uname}!")
            old_r, new_k = get_rank(data[0]), max(0, data[0] + num)
            new_r = update_keys(uname, new_k)
            bot.reply_to(message, f"✅ Đã cập nhật {num} key cho {uname}.\nTổng: {new_k} ({new_r})")
            if old_r != new_r and num > 0: 
                bot.send_message(message.chat.id, f"🎉 Chúc mừng <b>{uname}</b> thăng cấp <b>{new_r}</b>!", parse_mode='HTML')
        
        elif cmd in ['congxu', 'truxu']:
            uname, num = message.text.split()[1], int(message.text.split()[2])
            num = num if cmd == 'congxu' else -num
            data = db_query("SELECT xu FROM ctv WHERE username=?", (uname,), fetch='one')
            if not data: return bot.reply_to(message, f"❌ Không tìm thấy {uname}!")
            new_x = max(0, data[0] + num)
            db_query("UPDATE ctv SET xu=? WHERE username=?", (new_x, uname), commit=True)
            bot.reply_to(message, f"✅ Đã cập nhật {num} xu cho {uname}.\nTổng: {new_x} xu")
        
        elif cmd == 'thongke':
            total = db_query("SELECT COUNT(*), SUM(keys), SUM(xu) FROM ctv", fetch='one')
            top1 = db_query("SELECT username, keys FROM ctv ORDER BY keys DESC LIMIT 1", fetch='one')
            text = f"📈 <b>THỐNG KÊ</b>\n\n👥 Tổng CTV: <b>{total[0]}</b>\n🔑 Tổng Key: <b>{total[1] or 0}</b>\n🪙 Tổng Xu: <b>{total[2] or 0}</b>\n"
            if top1: text += f"\n🥇 Top 1: {top1[0]} ({top1[1]} key)"
            bot.reply_to(message, text, parse_mode='HTML')
        
        elif cmd == 'reset':
            db_query("UPDATE ctv SET keys=0, xu=0, rank='Đồng 🥉', streak=0, kudos=0", commit=True)
            bot.reply_to(message, "🧹 Đã reset toàn bộ Key và Xu!")
            
    except Exception as e: 
        bot.reply_to(message, f"❌ Sai cú pháp hoặc lỗi! Chi tiết: {e}")

# ================= LỆNH SOI CẦU =================
@bot.message_handler(commands=['soicau'])
def soi_cau_all(message):
    if not is_admin(message): return bot.reply_to(message, "❌ Chỉ Admin mới được dùng lệnh này!")
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "❌ Cú pháp: /soicau [taixiu/doanso/keobuabao/dovui/latthe]\nVD: /soicau taixiu")
    
    game = parts[1].lower()
    column = ""
    du_doan = ""
    ten_hien_thi = ""
    
    if game == 'taixiu':
        column = 'next_tx'; du_doan = random.choice(['tai', 'xiu']); ten_hien_thi = "TÀI" if du_doan == 'tai' else "XỈU"
    elif game == 'doanso':
        column = 'next_doanso'; du_doan = str(random.randint(1, 50)); ten_hien_thi = du_doan
    elif game == 'keobuabao':
        column = 'next_rps'; du_doan = random.choice(['bua', 'keo', 'bao']); ten_hien_thi = {'bua': 'BÚA', 'keo': 'KÉO', 'bao': 'BAO'}[du_doan]
    elif game == 'dovui':
        q, opts, ans = random.choice(DOVUI)
        column = 'next_dovui'; du_doan = str(ans); ten_hien_thi = opts[ans]
    elif game == 'latthe':
        column = 'next_latthe'; du_doan = ",".join(map(str, random.sample(range(9), 3))); ten_hien_thi = f"Vị trí Boom: {du_doan}"
    else:
        return bot.reply_to(message, "❌ Game không hợp lệ!")
        
    db_query(f"UPDATE ctv SET {column}=? WHERE username=?", (du_doan, get_uname(message)), commit=True)
    bot.reply_to(message, f"🔮 <b>SOI CẦU {game.upper()}</b> 🔮\n\nVán tiếp theo chắc chắn ra: <b>{ten_hien_thi}</b>\n(Độ chính xác 100% - Chỉ Admin thấy)", parse_mode='HTML')

# ================= TÍNH NĂNG LÌ XÌ =================
@bot.message_handler(commands=['guilixi'])
def gui_lixi(message):
    parts = message.text.split()
    if len(parts) == 1:
        temp_lixi_data[message.from_user.id] = {'step': 1, 'loai': '', 'tong': 0, 'so_nguoi': 0}
        m = InlineKeyboardMarkup().row(InlineKeyboardButton("🔑 Key", callback_data="lixi_loai_key"), InlineKeyboardButton("🪙 Xu", callback_data="lixi_loai_xu"))
        return bot.reply_to(message, "🧧 <b>TẠO TÚI LÌ XÌ</b> 🧧\nBước 1: Chọn loại lì xì bạn muốn gửi:", parse_mode='HTML', reply_markup=m)
    return bot.reply_to(message, "❌ Sai cú pháp. Hãy gõ /guilixi để tạo túi lì xì.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('lixi_loai_'))
def lixi_chon_loai(call):
    loai = call.data.split('_')[2]
    temp_lixi_data[call.from_user.id] = {'step': 2, 'loai': loai, 'tong': 0, 'so_nguoi': 0}
    bot.edit_message_text(f"🧧 Bạn chọn gửi lì xì bằng <b>{loai.upper()}</b>.\nBước 2: Nhập tổng số {loai} bạn muốn gửi.\n(Cú pháp: <code>/tongsố</code>. VD: <code>/100</code>)", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in temp_lixi_data and message.text.startswith('/'))
def lixi_nhap_so(message):
    state = temp_lixi_data[message.from_user.id]
    text = message.text.replace('/', '').strip()
    
    if not text.isdigit(): return bot.reply_to(message, "❌ Vui lòng nhập số hợp lệ (VD: /100).")
    val = int(text)
    u = check_user(message)
    if not u: return

    if state['step'] == 2:
        balance = u[1] if state['loai'] == 'key' else u[2]
        if balance < val: return bot.reply_to(message, f"❌ Bạn không đủ {state['loai']}! (Bạn có {balance}).")
        state['tong'] = val
        state['step'] = 3
        bot.reply_to(message, f"✅ Tổng {state['loai']}: <b>{val}</b>.\nBước 3: Nhập số người có thể nhận lì xì này.\n(Cú pháp: <code>/số_người</code>. VD: <code>/5</code>)", parse_mode='HTML')
        
    elif state['step'] == 3:
        if val <= 0 or val > 100: return bot.reply_to(message, "❌ Số người phải từ 1 đến 100.")
        state['so_nguoi'] = val
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        uname = u[0]
        
        if state['loai'] == 'key': db_query("UPDATE ctv SET keys = keys - ? WHERE username=?", (state['tong'], uname), commit=True)
        else: db_query("UPDATE ctv SET xu = xu - ? WHERE username=?", (state['tong'], uname), commit=True)
            
        db_query("INSERT INTO lixi (code, creator, loai, tong_gia_tri, con_lai, so_nguoi) VALUES (?, ?, ?, ?, ?, ?)", 
                 (code, uname, state['loai'], state['tong'], state['tong'], state['so_nguoi']), commit=True)
        del temp_lixi_data[message.from_user.id]
        
        text = (f"🧧 <b>TẠO TÚI LÌ XÌ THÀNH CÔNG!</b> 🧧\n\n"
                f"👤 Người gửi: {uname}\n"
                f"🎁 Loại: {state['loai'].upper()} (Tổng: {state['tong']})\n"
                f"👥 Số người có thể nhận: <b>{state['so_nguoi']}</b> người.\n\n"
                f"👉 Nhập lệnh <code>/bulixi {code}</code> để nhận.\n"
                f"(Nhanh tay lên, khi đủ {state['so_nguoi']} người nhận túi sẽ tự đóng lại!)")
        bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['bulixi'])
def nhan_lixi(message):
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "❌ Cú pháp: /bulixi [mã_code]\nVí dụ: /bulixi ABC123")
    code = parts[1].upper()
    u = check_user(message)
    if not u: return
    uname = u[0]
    
    li = db_query("SELECT * FROM lixi WHERE code=?", (code,), fetch='one')
    if not li: return bot.reply_to(message, "❌ Mã lì xì không tồn tại hoặc đã bị xóa!")
    if li[7] == 'closed': return bot.reply_to(message, "🧧 Túi lì xì này đã được bốc hết rồi (Hết lượt hoặc hết tiền)!")
    
    loai, tong, con_lai, so_nguoi, da_nhan = li[2], li[3], li[4], li[5], li[6]
    if da_nhan >= so_nguoi:
        db_query("UPDATE lixi SET status='closed' WHERE code=?", (code,), commit=True)
        return bot.reply_to(message, "🧧 Túi lì xì này đã hết lượt nhận!")
        
    nguoi_con_lai = so_nguoi - da_nhan
    if nguoi_con_lai == 1: nhan_duoc = con_lai
    else:
        nhan_duoc = random.randint(int(con_lai * 0.1), int(con_lai * 0.5))
        if nhan_duoc >= con_lai: nhan_duoc = con_lai - 1
    if nhan_duoc < 1: nhan_duoc = 1 
    
    con_lai_moi = con_lai - nhan_duoc
    da_nhan_moi = da_nhan + 1
    status = 'closed' if da_nhan_moi >= so_nguoi or con_lai_moi <= 0 else 'active'
    
    db_query("UPDATE lixi SET con_lai=?, da_nhan=?, status=? WHERE code=?", (con_lai_moi, da_nhan_moi, status, code), commit=True)
    
    if loai == 'key':
        k = db_query("SELECT keys FROM ctv WHERE username=?", (uname,), fetch='one')[0]
        update_keys(uname, k + nhan_duoc)
    else: update_xu(uname, nhan_duoc)
        
    bot.reply_to(message, f"🧧 <b>CHÚC MỪNG!</b> 🧧\nBạn đã nhận được <b>{nhan_duoc} {loai.upper()}</b> từ túi lì xì của {li[1]}.\n\n⏳ Trạng thái túi: Còn {so_nguoi - da_nhan_moi} lượt nhận.", parse_mode='HTML')
    
    if status == 'closed':
        bot.send_message(message.chat.id, f"🎊 <b>TÚI LÌ XÌ {code} ĐÃ ĐƯỢC BỐC HẾT!</b>\nCảm ơn <b>{li[1]}</b> đã gửi tặng {tong} {loai} cho mọi người!", parse_mode='HTML')

# ================= KHU VỰC GAME (DÙNG XU TỰ CHỌN) =================
DOVUI = [
    ("Con gì càng lớn càng nhỏ?", ["Con cua", "Con rắn", "Con voi"], 0), 
    ("Trái gì ăn sống chua, nấu chín ngọt?", ["Chanh", "Khế", "Me"], 0),
    ("Cái gì của bạn nhưng người khác dùng nhiều hơn?", ["Tên của bạn", "Điện thoại", "Quần áo"], 0),
    ("Một năm có bao nhiêu tháng có 28 ngày?", ["12 tháng", "1 tháng", "2 tháng"], 0)
]

def game_check(msg, args, min_cost):
    u = check_user(msg)
    if not u: return None
    uname, k, x = u
    
    cost = min_cost
    if len(args) > 1:
        try: 
            cost = int(args[1])
            if cost < min_cost: 
                bot.reply_to(msg, f"❌ Số xu cược tối thiểu là {min_cost}!")
                return None
        except: 
            bot.reply_to(msg, f"❌ Số xu không hợp lệ. Cú pháp: /tengame [số xu]")
            return None
            
    if x < cost: 
        bot.reply_to(msg, f"❌ Bạn cần ít nhất {cost} xu để chơi! (Bạn có {x} xu)"); 
        return None
    return uname, k, x, cost

# --- TÀI XỈU ---
@bot.message_handler(commands=['taixiu'])
def game_tai_xiu(message):
    args = message.text.split()
    res = game_check(message, args, 5) 
    if not res: return
    uname, k, x, cost = res
    
    m = InlineKeyboardMarkup().row(InlineKeyboardButton("🎲 TÀI", callback_data=f"tx_tai_{cost}"), InlineKeyboardButton("🎲 XỈU", callback_data=f"tx_xiu_{cost}")).row(InlineKeyboardButton("❌ Hủy", callback_data="tx_huy"))
    bot.reply_to(message, f"🎰 <b>TÀI XỈU</b> 🎰\nCược <b>{cost} xu</b>. Chọn:", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('tx_'))
def handle_taixiu(call):
    if call.data == 'tx_huy': return bot.edit_message_text("❌ Đã hủy.", call.message.chat.id, call.message.message_id)
    u = get_uname(call)
    if not u: return bot.answer_callback_query(call.id, "Cần Username!", show_alert=True)
    
    parts = call.data.split('_')
    cuoc, cost = parts[1], int(parts[2])
    
    x = db_query("SELECT xu FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if x < cost: return bot.answer_callback_query(call.id, f"Bạn không đủ {cost} xu!", show_alert=True)
    
    next_tx = db_query("SELECT next_tx FROM ctv WHERE next_tx IS NOT NULL LIMIT 1", fetch='one')
    if next_tx and next_tx[0]: 
        ket_qua = next_tx[0] 
        db_query("UPDATE ctv SET next_tx=NULL WHERE next_tx IS NOT NULL", commit=True) 
    else:
        ket_qua = 'tai' if random.randint(3, 18) >= 11 else 'xiu'

    while True:
        d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
        tong = d1 + d2 + d3
        if (ket_qua == 'tai' and tong >= 11) or (ket_qua == 'xiu' and tong <= 10): break

    change = cost if cuoc == ket_qua else -cost
    status = f"🎉 THẮNG (+{cost} xu)" if cuoc == ket_qua else f"😭 THUA (-{cost} xu)"
    update_xu(u, change)
    
    bot.edit_message_text(f"🎲 {d1}-{d2}-{d3} = <b>{tong}</b> ({'TÀI' if ket_qua == 'tai' else 'XỈU'})\n{status}\n🪙 {x + change} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

# --- ĐOÁN SỐ ---
@bot.message_handler(commands=['doanso'])
def game_doan_so(message):
    args = message.text.split()
    res = game_check(message, args, 2) 
    if not res: return
    uname, k, x, cost = res
    
    game_data[uname] = random.randint(1, 50)
    m = InlineKeyboardMarkup()
    for i in range(1, 51, 10): m.row(*[InlineKeyboardButton(str(j), callback_data=f"doan_{j}_{cost}") for j in range(i, i+10)])
    bot.reply_to(message, f"🔢 <b>ĐOÁN SỐ (1-50)</b>\nCược <b>{cost} xu</b>. Đúng +{cost}, sai -{cost}.", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('doan_'))
def handle_doanso(call):
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    
    parts = call.data.split('_')
    chon, cost = int(parts[1]), int(parts[2])
    
    x = db_query("SELECT xu FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if x < cost: return bot.answer_callback_query(call.id, f"Bạn không đủ {cost} xu!", show_alert=True)
    
    next_ans = db_query("SELECT next_doanso FROM ctv WHERE next_doanso IS NOT NULL LIMIT 1", fetch='one')
    if next_ans and next_ans[0]:
        may_man = int(next_ans[0])
        db_query("UPDATE ctv SET next_doanso=NULL WHERE next_doanso IS NOT NULL", commit=True)
    else:
        may_man = game_data.pop(u)
        
    change = cost if chon == may_man else -cost
    status = f"🎉 ĐÚNG (+{cost} xu)" if chon == may_man else f"😭 SAI (-{cost} xu). Đáp án: {may_man}"
    update_xu(u, change)
    
    bot.edit_message_text(f"🔢 Chọn: <b>{chon}</b>\n{status}\n🪙 {x + change} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

# --- BÚA KÉO BAO ---
@bot.message_handler(commands=['keobuabao', 'buakeobao'])
def game_bua_keo_bao(message):
    args = message.text.split()
    res = game_check(message, args, 3) 
    if not res: return
    uname, k, x, cost = res
    
    m = InlineKeyboardMarkup().row(
        InlineKeyboardButton("✊ Búa", callback_data=f"rps_bua_{cost}"), 
        InlineKeyboardButton("✌️ Kéo", callback_data=f"rps_keo_{cost}"), 
        InlineKeyboardButton("✋ Bao", callback_data=f"rps_bao_{cost}")
    )
    bot.reply_to(message, f"✂️ <b>BÚA KÉO BAO</b>\nCược <b>{cost} xu</b>. Chọn:", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rps_'))
def handle_rps(call):
    u = get_uname(call)
    if not u: return
    
    parts = call.data.split('_')
    p, cost = parts[1], int(parts[2])
    
    x = db_query("SELECT xu FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if x < cost: return bot.answer_callback_query(call.id, f"Bạn không đủ {cost} xu!", show_alert=True)
    
    b = random.choice(['bua', 'keo', 'bao'])
    next_rps = db_query("SELECT next_rps FROM ctv WHERE next_rps IS NOT NULL LIMIT 1", fetch='one')
    if next_rps and next_rps[0]:
        b = next_rps[0]
        db_query("UPDATE ctv SET next_rps=NULL WHERE next_rps IS NOT NULL", commit=True)
        
    ten = {'bua': '✊ Búa', 'keo': '✌️ Kéo', 'bao': '✋ Bao'}
    
    if p == b: 
        change, status = 0, "🤝 HÒA (Hoàn lại xu)"
    elif (p == 'bua' and b == 'keo') or (p == 'keo' and b == 'bao') or (p == 'bao' and b == 'bua'): 
        change, status = cost, f"🎉 THẮNG (+{cost} xu)"
    else: 
        change, status = -cost, f"😭 THUA (-{cost} xu)"
        
    update_xu(u, change)
    bot.edit_message_text(f"Bạn: {ten[p]} | Bot: {ten[b]}\n{status}\n🪙 {x + change} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

# --- ĐỐ VUI ---
@bot.message_handler(commands=['dovui'])
def game_do_vui(message):
    args = message.text.split()
    res = game_check(message, args, 2) 
    if not res: return
    uname, k, x, cost = res
    
    q, opts, ans = random.choice(DOVUI)
    game_data[uname] = ans
    m = InlineKeyboardMarkup()
    for i, o in enumerate(opts): m.add(InlineKeyboardButton(o, callback_data=f"dv_{i}_{cost}"))
    bot.reply_to(message, f"❓ <b>ĐỐ VUI</b>\n{q}\n(Đúng +{cost} xu, Sai -{cost} xu)", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dv_'))
def handle_dovui(call):
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    
    parts = call.data.split('_')
    chon, cost = int(parts[1]), int(parts[2])
    
    x = db_query("SELECT xu FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if x < cost: return bot.answer_callback_query(call.id, f"Bạn không đủ {cost} xu!", show_alert=True)
    
    ans = game_data.pop(u)
    next_dv = db_query("SELECT next_dovui FROM ctv WHERE next_dovui IS NOT NULL LIMIT 1", fetch='one')
    if next_dv and next_dv[0]:
        ans = int(next_dv[0])
        db_query("UPDATE ctv SET next_dovui=NULL WHERE next_dovui IS NOT NULL", commit=True)
        
    change = cost if chon == ans else -cost
    status = f"🎉 ĐÚNG (+{cost} xu)" if chon == ans else f"😭 SAI (-{cost} xu)"
    update_xu(u, change)
    
    bot.edit_message_text(f"{status}\n🪙 {x + change} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

# --- LẬT THẺ ---
@bot.message_handler(commands=['latthe'])
def game_lat_the(message):
    args = message.text.split()
    res = game_check(message, args, 5) 
    if not res: return
    uname, k, x, cost = res
    
    booms = random.sample(range(9), 3)
    next_lt = db_query("SELECT next_latthe FROM ctv WHERE next_latthe IS NOT NULL LIMIT 1", fetch='one')
    if next_lt and next_lt[0]:
        booms = [int(i) for i in next_lt[0].split(',')]
        db_query("UPDATE ctv SET next_latthe=NULL WHERE next_latthe IS NOT NULL", commit=True)
        
    game_data[uname] = {'booms': booms, 'cost': cost, 'safe': 0}
    
    m = InlineKeyboardMarkup()
    for i in range(0, 9, 3): m.row(*[InlineKeyboardButton("❓", callback_data=f"lt_{j}") for j in range(i, i+3)])
    bot.reply_to(message, f"💣 <b>LẬT THẺ</b>\nCược <b>{cost} xu</b>. Né 3 boom. Lật an toàn +{cost//2}, hết 6 ô thưởng lớn.", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lt_'))
def handle_latthe(call):
    if call.data == 'lt_none': return bot.answer_callback_query(call.id)
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    
    state = game_data[u]
    cost, booms = state['cost'], state['booms']
    
    x = db_query("SELECT xu FROM ctv WHERE username=?", (u,), fetch='one')[0]
    
    idx = int(call.data.split('_')[1])
    m = InlineKeyboardMarkup()
    safe_count = 0
    
    for row in call.message.reply_markup.keyboard:
        new_row = []
        for btn in row:
            b_idx = int(btn.callback_data.split('_')[1]) if btn.callback_data != 'lt_none' else -1
            if b_idx == idx: new_row.append(InlineKeyboardButton("💥" if idx in booms else "💎", callback_data="lt_none"))
            else: new_row.append(btn)
            if btn.text == "💎" or (b_idx == idx and idx not in booms): safe_count += 1
        m.row(*new_row)
        
    if idx in booms:
        update_xu(u, -cost)
        del game_data[u]
        bot.edit_message_text(f"💥 <b>BÙM!</b> (-{cost} xu)\n🪙 {x - cost} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    else:
        thuong = cost // 2
        update_xu(u, thuong)
        if safe_count == 6:
            bonus = cost * 2
            update_xu(u, bonus)
            del game_data[u]
            bot.edit_message_text(f"🏆 <b>XUẤT SẮC!</b> (+{thuong} xu và thưởng {bonus} xu)\n🪙 {x + thuong + bonus} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML')
        else:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=m)
            bot.answer_callback_query(call.id, f"💎 An toàn! +{thuong} xu (Tổ
