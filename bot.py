import os, telebot, sqlite3, random, time
from datetime import datetime, timedelta
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

BOT_TOKEN = '9268542841:AAHJvJtXD7oXLfTlNeUyaSanWH5yni12DhQ' # ĐỔI TOKEN MỚI
ADMIN_ID = 8240363472
BANNER_URL = 'https://i.postimg.cc/G3P8qX0G/file-000000005d588209b919bcce17087b9f.png'
GAME_BANNER_URL = 'https://i.postimg.cc/nztdrLpQ/file-0000000089dc8211b7bef528f2d9543b.png' # THAY LINK ẢNH GAME VÀO ĐÂY

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
game_data = {} # Lưu data tạm cho tất cả game

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
db_query('''CREATE TABLE IF NOT EXISTS ctv (username TEXT PRIMARY KEY, chat_id INTEGER, keys INTEGER, rank TEXT, join_date TEXT, quote TEXT, last_checkin TEXT, streak INTEGER, last_wheel TEXT, kudos INTEGER)''')
for col in ["chat_id INTEGER", "join_date TEXT", "quote TEXT", "last_checkin TEXT", "streak INTEGER DEFAULT 0", "last_wheel TEXT", "kudos INTEGER DEFAULT 0"]:
    try: db_query(f"ALTER TABLE ctv ADD COLUMN {col}", commit=True)
    except: pass

def update_keys(uname, new_keys):
    rank = get_rank(new_keys)
    db_query("UPDATE ctv SET keys=?, rank=? WHERE username=?", (new_keys, rank, uname), commit=True)
    return rank

def check_user(msg):
    uname = get_uname(msg)
    if not uname: 
        bot.reply_to(msg, "❌ Bạn cần tạo Username Telegram!"); return None
    data = db_query("SELECT keys FROM ctv WHERE username=?", (uname,), fetch='one')
    if not data: 
        bot.reply_to(msg, "❌ Bạn chưa có trong hệ thống!"); return None
    return uname, data[0]

# ================= MENU =================
def get_menu():
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("🏆 Xếp Hạng", callback_data="menu_xephang"), InlineKeyboardButton("📊 Cấp Bậc", callback_data="menu_capbac"))
    m.row(InlineKeyboardButton("🎯 Nhiệm Vụ", callback_data="menu_nhiemvu"), InlineKeyboardButton("👤 Thông Tin", callback_data="menu_info"))
    m.row(InlineKeyboardButton("🎲 Vòng Quay", callback_data="menu_vongquay"), InlineKeyboardButton("📅 Điểm Danh", callback_data="menu_diemdanh"))
    m.row(InlineKeyboardButton("🎮 GAME GIẢI TRÍ", callback_data="menu_game"))
    m.row(InlineKeyboardButton("💳 Hồ Sơ", callback_data="menu_profile"), InlineKeyboardButton("🔥 Top 3", callback_data="menu_top"))
    return m

def get_game_menu():
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("🎰 Tài Xỉu", callback_data="game_taixiu"), InlineKeyboardButton("🔢 Đoán Số", callback_data="game_doanso"))
    m.row(InlineKeyboardButton("✂️ Búa Kéo Bao", callback_data="game_buakeobao"), InlineKeyboardButton("❓ Đố Vui", callback_data="game_dovui"))
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
            db_query("INSERT INTO ctv (username, chat_id, keys, rank, join_date) VALUES (?, ?, 0, ?, ?)", (uname, message.chat.id, "Đồng 🥉", get_today()), commit=True)

    text = ("Chào Sếp! Bot quản lý CTV.\n👇 Bấm nút bên dưới hoặc dùng lệnh:\n\n🛠 Lệnh Admin:\n/themctv /congkey /trukey /xoactv /thongke /thongbao /reset\n\n🛡 Quản trị nhóm:\n/kick /camchat /add\n\n🎮 Gõ /game để xem các game giải trí!" if is_admin(message) else "Chào bạn! Hệ thống quản lý CTV.\n👇 Bấm nút bên dưới hoặc dùng lệnh:\n/vongquay /diemdanh /profile /setquote /khen\n/game - Kho game giải trí")
    try: bot.send_photo(message.chat.id, BANNER_URL, caption=text, parse_mode='HTML', reply_markup=get_menu())
    except: bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_') or call.data.startswith('game_'))
def handle_menu(call):
    bot.answer_callback_query(call.id)
    actions = {
        'menu_xephang': xep_hang, 'menu_capbac': xem_cap_bac, 'menu_nhiemvu': nhiem_vu,
        'menu_info': xem_info, 'menu_vongquay': vong_quay, 'menu_diemdanh': diem_danh,
        'menu_profile': xem_profile, 'menu_top': xem_top_3, 'menu_game': menu_game,
        'game_taixiu': game_tai_xiu, 'game_doanso': game_doan_so,
        'game_buakeobao': game_bua_keo_bao, 'game_dovui': game_do_vui, 'game_latthe': game_lat_the
    }
    if call.data in actions: actions[call.data](call.message)

@bot.message_handler(commands=['game'])
def menu_game(message):
    text = ("🎮 <b>TỔNG HỢP GAME GIẢI TRÍ</b> 🎮\n👇 Bấm nút bên dưới để chơi ngay!\n\n"
            "🎰 <b>Tài Xỉu:</b> Cược 5 key. Đoán Tài (11-18) hoặc Xỉu (3-10).\n"
            "🔢 <b>Đoán Số:</b> Cược 2 key. Đoán số từ 1-50.\n"
            "✂️ <b>Búa Kéo Bao:</b> Cược 3 key. Đấu với Bot.\n"
            "❓ <b>Đố Vui:</b> Cược 2 key. Trả lời đúng +5 key.\n"
            "💣 <b>Lật Thẻ:</b> Cược 5 key. Né 3 quả boom.")
    try: bot.send_photo(message.chat.id, GAME_BANNER_URL, caption=text, parse_mode='HTML', reply_markup=get_game_menu())
    except: bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_game_menu())

# ================= LỆNH TÍNH NĂNG =================
@bot.message_handler(commands=['xephang'])
def xep_hang(message):
    users = db_query("SELECT username, keys, rank FROM ctv ORDER BY keys DESC", fetch='all')
    text = "🏆 <b>BẢNG XẾP HẠNG</b> 🏆\n\n" + "".join([f"{i}. {u[0]} | {u[2]} | {u[1]} key\n" for i, u in enumerate(users, 1)]) if users else "📭 Chưa có CTV nào!"
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
    k, r = db_query("SELECT keys, rank FROM ctv WHERE username=?", (u[0],), fetch='one')
    goal = f"{10-k} key lên Bạc" if k < 10 else f"{25-k} key lên Vàng" if k < 25 else f"{50-k} key lên Kim Cương" if k < 50 else f"{100-k} key lên KC Cao Cấp" if k < 100 else "Đã đạt tối cao!"
    bot.reply_to(message, f"👤 <b>THÔNG TIN: {u[0]}</b>\n\n📊 Cấp: <b>{r}</b>\n🔑 Key: <b>{k}</b>\n🎯 Mục tiêu: Cần thêm {goal}", parse_mode='HTML')

@bot.message_handler(commands=['profile'])
def xem_profile(message):
    u = check_user(message)
    if not u: return
    data = db_query("SELECT keys, rank, join_date, quote, kudos FROM ctv WHERE username=?", (u[0],), fetch='one')
    k, r, jd, q, kd = data[0], data[1], data[2] or "Không rõ", data[3] or "Chưa có...", data[4] or 0
    bot.reply_to(message, f"💳 <b>THẺ CĂN CƯỚC CTV</b> 💳\n-------------------\n👤 <b>Chủ thẻ:</b> {u[0]}\n📅 <b>Gia nhập:</b> {jd}\n🏅 <b>Cấp bậc:</b> {r}\n🔑 <b>Key:</b> {k}\n💖 <b>Khen:</b> {kd}\n-------------------\n💬 <b>Châm ngôn:</b> <i>\"{q}\"</i>", parse_mode='HTML')

@bot.message_handler(commands=['setquote'])
def set_quote(message):
    u = get_uname(message)
    if not u: return
    txt = message.text.replace('/setquote', '').strip()
    if not txt or len(txt) > 50: return bot.reply_to(message, "❌ Châm ngôn phải từ 1-50 ký tự!")
    db_query("UPDATE ctv SET quote=? WHERE username=?", (txt, u), commit=True)
    bot.reply_to(message, f"✅ Đã đổi châm ngôn: <i>\"{txt}\"</i>", parse_mode='HTML')

@bot.message_handler(commands=['vongquay'])
def vong_quay(message):
    u = check_user(message)
    if not u: return
    uname, k = u
    lw = db_query("SELECT last_wheel FROM ctv WHERE username=?", (uname,), fetch='one')[0]
    if lw == get_today(): return bot.reply_to(message, "⏳ Mai quay lại nhé!")
    won = random.choices([0, 1, 1, 3, 5], weights=[40, 30, 15, 10, 5], k=1)[0]
    nr = update_keys(uname, k + won)
    db_query("UPDATE ctv SET last_wheel=? WHERE username=?", (get_today(), uname), commit=True)
    bot.reply_to(message, f"🎲 Kết quả: <b>{won} key</b>!\nTổng: {k+won} key ({nr})", parse_mode='HTML')

@bot.message_handler(commands=['diemdanh'])
def diem_danh(message):
    u = check_user(message)
    if not u: return
    uname, k = u
    lc, st = db_query("SELECT last_checkin, streak FROM ctv WHERE username=?", (uname,), fetch='one')
    if lc == get_today(): return bot.reply_to(message, "⏳ Hôm nay đã điểm danh rồi!")
    st = st + 1 if lc == (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") else 1
    add = 1; bonus = ""
    if st >= 7: add += 5; bonus = "\n🔥 Chuỗi 7 ngày! Thưởng +5 key!"; st = 0
    nr = update_keys(uname, k + add)
    db_query("UPDATE ctv SET last_checkin=?, streak=? WHERE username=?", (get_today(), st, uname), commit=True)
    bot.reply_to(message, f"✅ Điểm danh nhận <b>{add} key</b>! (Chuỗi: {st}/7){bonus}\nTổng: {k+add} key ({nr})", parse_mode='HTML')

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

@bot.message_handler(commands=['themctv', 'xoactv', 'congkey', 'trukey', 'thongke', 'reset'])
def admin_commands(message):
    if not is_admin(message): return
    cmd = message.text.split()[0].replace('/', '')
    try:
        if cmd == 'themctv':
            uname = message.text.split()[1]
            if db_query("SELECT username FROM ctv WHERE username=?", (uname,), fetch='one'): return bot.reply_to(message, "⚠️ Đã có trong danh sách!")
            db_query("INSERT INTO ctv (username, keys, rank, join_date) VALUES (?, 0, ?, ?)", (uname, "Đồng 🥉", get_today()), commit=True)
            bot.reply_to(message, f"✅ Đã thêm {uname}.")
            chat_id = db_query("SELECT chat_id FROM ctv WHERE username=?", (uname,), fetch='one')[0]
            if chat_id: bot.send_message(chat_id, f"🎉 Chào mừng <b>{uname}</b>! Gõ /start để xem tính năng.", parse_mode='HTML')
            else: bot.reply_to(message, f"💡 {uname} chưa bấm /start.")
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
            if old_r != new_r and num > 0: bot.send_message(message.chat.id, f"🎉 Chúc mừng <b>{uname}</b> thăng cấp <b>{new_r}</b>!", parse_mode='HTML')
        elif cmd == 'thongke':
            total = db_query("SELECT COUNT(*), SUM(keys) FROM ctv", fetch='one')
            top1 = db_query("SELECT username, keys FROM ctv ORDER BY keys DESC LIMIT 1", fetch='one')
            text = f"📈 <b>THỐNG KÊ</b>\n\n👥 Tổng CTV: <b>{total[0]}</b>\n🔑 Tổng Key: <b>{total[1] or 0}</b>\n"
            if top1: text += f"\n🥇 Top 1: {top1[0]} ({top1[1]} key)"
            bot.reply_to(message, text, parse_mode='HTML')
        elif cmd == 'reset':
            db_query("UPDATE ctv SET keys=0, rank='Đồng 🥉', streak=0, kudos=0", commit=True)
            bot.reply_to(message, "🧹 Đã reset toàn bộ!")
    except: bot.reply_to(message, "❌ Sai cú pháp!")

# ================= KHU VỰC GAME =================
def game_check(msg, cost):
    u = check_user(msg)
    if not u: return None
    if u[1] < cost: bot.reply_to(msg, f"❌ Bạn cần ít nhất {cost} key!"); return None
    return u

@bot.message_handler(commands=['taixiu'])
def game_tai_xiu(message):
    if not game_check(message, 5): return
    m = InlineKeyboardMarkup().row(InlineKeyboardButton("🎲 TÀI", callback_data="tx_tai"), InlineKeyboardButton("🎲 XỈU", callback_data="tx_xiu")).row(InlineKeyboardButton("❌ Hủy", callback_data="tx_huy"))
    bot.reply_to(message, "🎰 <b>TÀI XỈU</b> 🎰\nCược <b>5 key</b>. Chọn:", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('tx_'))
def handle_taixiu(call):
    if call.data == 'tx_huy': return bot.edit_message_text("❌ Đã hủy.", call.message.chat.id, call.message.message_id)
    u = get_uname(call)
    if not u or db_query("SELECT keys FROM ctv WHERE username=?", (u,), fetch='one')[0] < 5: return bot.answer_callback_query(call.id, "Không đủ key!", show_alert=True)
    k = db_query("SELECT keys FROM ctv WHERE username=?", (u,), fetch='one')[0]
    cuoc, d1, d2, d3 = call.data.split('_')[1], random.randint(1,6), random.randint(1,6), random.randint(1,6)
    tong, ket_qua = d1+d2+d3, 'tai' if d1+d2+d3 >= 11 else 'xiu'
    new_keys = k + 5 if cuoc == ket_qua else k - 5
    status = "🎉 THẮNG (+5)" if cuoc == ket_qua else "😭 THUA (-5)"
    nr = update_keys(u, new_keys)
    bot.edit_message_text(f"🎲 {d1}-{d2}-{d3} = <b>{tong}</b> ({'TÀI' if ket_qua == 'tai' else 'XỈU'})\n{status}\n🔑 {new_keys} key ({nr})", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['doanso'])
def game_doan_so(message):
    if not game_check(message, 2): return
    game_data[get_uname(message)] = random.randint(1, 50)
    m = InlineKeyboardMarkup()
    for i in range(1, 51, 10): m.row(*[InlineKeyboardButton(str(j), callback_data=f"doan_{j}") for j in range(i, i+10)])
    bot.reply_to(message, "🔢 <b>ĐOÁN SỐ (1-50)</b>\nCược <b>2 key</b>. Đúng +5, sai -2.", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('doan_'))
def handle_doanso(call):
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    k = db_query("SELECT keys FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if k < 2: return bot.answer_callback_query(call.id, "Không đủ key!", show_alert=True)
    chon, may_man = int(call.data.split('_')[1]), game_data.pop(u)
    new_keys = k + 5 if chon == may_man else k - 2
    status = "🎉 ĐÚNG (+5)" if chon == may_man else f"😭 SAI (-2). Đáp án: {may_man}"
    nr = update_keys(u, new_keys)
    bot.edit_message_text(f"🔢 Chọn: <b>{chon}</b>\n{status}\n🔑 {new_keys} key ({nr})", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['buakeobao'])
def game_bua_keo_bao(message):
    if not game_check(message, 3): return
    m = InlineKeyboardMarkup().row(InlineKeyboardButton("✊ Búa", callback_data="rps_bua"), InlineKeyboardButton("✌️ Kéo", callback_data="rps_keo"), InlineKeyboardButton("✋ Bao", callback_data="rps_bao"))
    bot.reply_to(message, "✂️ <b>BÚA KÉO BAO</b>\nCược <b>3 key</b>. Chọn:", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rps_'))
def handle_rps(call):
    u = get_uname(call)
    if not u: return
    k = db_query("SELECT keys FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if k < 3: return bot.answer_callback_query(call.id, "Không đủ key!", show_alert=True)
    p, b = call.data.split('_')[1], random.choice(['bua', 'keo', 'bao'])
    ten = {'bua': '✊ Búa', 'keo': '✌️ Kéo', 'bao': '✋ Bao'}
    if p == b: new_keys, status = k, "🤝 HÒA"
    elif (p=='bua' and b=='keo') or (p=='keo' and b=='bao') or (p=='bao' and b=='bua'): new_keys, status = k+3, "🎉 THẮNG (+3)"
    else: new_keys, status = k-3, "😭 THUA (-3)"
    nr = update_keys(u, new_keys)
    bot.edit_message_text(f"Bạn: {ten[p]} | Bot: {ten[b]}\n{status}\n🔑 {new_keys} key ({nr})", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

DOVUI = [("Con gì càng lớn càng nhỏ?", ["Con cua", "Con rắn", "Con voi"], 0), ("Trái gì ăn sống chua, nấu chín ngọt?", ["Chanh", "Khế", "Me"], 0)]
@bot.message_handler(commands=['dovui'])
def game_do_vui(message):
    if not game_check(message, 2): return
    q, opts, ans = random.choice(DOVUI)
    game_data[get_uname(message)] = ans
    m = InlineKeyboardMarkup()
    for i, o in enumerate(opts): m.add(InlineKeyboardButton(o, callback_data=f"dv_{i}"))
    bot.reply_to(message, f"❓ <b>ĐỐ VUI</b>\n{q}\n(Đúng +5, Sai -2)", parse_mode='HTML', reply_markup=m)

@bot.message_handler(commands=['buakeobao'])
def game_bua_keo_bao(message):
    if not game_check(message, 3): return
    m = InlineKeyboardMarkup().row(InlineKeyboardButton("✊ Búa", callback_data="rps_bua"), InlineKeyboardButton("✌️ Kéo", callback_data="rps_keo"), InlineKeyboardButton("✋ Bao", callback_data="rps_bao"))
    bot.reply_to(message, "✂️ <b>BÚA KÉO BAO</b>\nCược <b>3 key</b>. Chọn:", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rps_'))
def handle_rps(call):
    u = get_uname(call)
    if not u: return
    k = db_query("SELECT keys FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if k < 3: return bot.answer_callback_query(call.id, "Không đủ key!", show_alert=True)
    p, b = call.data.split('_')[1], random.choice(['bua', 'keo', 'bao'])
    ten = {'bua': '✊ Búa', 'keo': '✌️ Kéo', 'bao': '✋ Bao'}
    if p == b: new_keys, status = k, "🤝 HÒA"
    elif (p=='bua' and b=='keo') or (p=='keo' and b=='bao') or (p=='bao' and b=='bua'): new_keys, status = k+3, "🎉 THẮNG (+3)"
    else: new_keys, status = k-3, "😭 THUA (-3)"
    nr = update_keys(u, new_keys)
    bot.edit_message_text(f"Bạn: {ten[p]} | Bot: {ten[b]}\n{status}\n🔑 {new_keys} key ({nr})", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

DOVUI = [
    ("Con gì càng lớn càng nhỏ?", ["Con cua", "Con rắn", "Con voi"], 0), 
    ("Trái gì ăn sống chua, nấu chín ngọt?", ["Chanh", "Khế", "Me"], 0),
    ("Cái gì của bạn nhưng người khác dùng nhiều hơn?", ["Tên của bạn", "Điện thoại", "Quần áo"], 0),
    ("Một năm có bao nhiêu tháng có 28 ngày?", ["12 tháng", "1 tháng", "2 tháng"], 0)
]

@bot.message_handler(commands=['dovui'])
def game_do_vui(message):
    if not game_check(message, 2): return
    q, opts, ans = random.choice(DOVUI)
    game_data[get_uname(message)] = ans
    m = InlineKeyboardMarkup()
    for i, o in enumerate(opts): m.add(InlineKeyboardButton(o, callback_data=f"dv_{i}"))
    bot.reply_to(message, f"❓ <b>ĐỐ VUI</b>\n{q}\n(Đúng +5, Sai -2)", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dv_'))
def handle_dovui(call):
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    k = db_query("SELECT keys FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if k < 2: return bot.answer_callback_query(call.id, "Không đủ key!", show_alert=True)
    chon, ans = int(call.data.split('_')[1]), game_data.pop(u)
    new_keys = k + 5 if chon == ans else k - 2
    nr = update_keys(u, new_keys)
    bot.edit_message_text(f"{'🎉 ĐÚNG (+5)' if chon == ans else '😭 SAI (-2)'}\n🔑 {new_keys} key ({nr})", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['latthe'])
def game_lat_the(message):
    if not game_check(message, 5): return
    game_data[get_uname(message)] = random.sample(range(9), 3)
    m = InlineKeyboardMarkup()
    for i in range(0, 9, 3): m.row(*[InlineKeyboardButton("❓", callback_data=f"lt_{j}") for j in range(i, i+3)])
    bot.reply_to(message, "💣 <b>LẬT THẺ</b>\nCược 5 key. Né 3 boom. An toàn +2, hết 6 ô +10.", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lt_'))
def handle_latthe(call):
    if call.data == 'lt_none': return bot.answer_callback_query(call.id)
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    k = db_query("SELECT keys FROM ctv WHERE username=?", (u,), fetch='one')[0]
    if k < 5: return bot.answer_callback_query(call.id, "Không đủ key!", show_alert=True)
    idx, booms = int(call.data.split('_')[1]), game_data[u]
    m = InlineKeyboardMarkup(); safe = 0
    for row in call.message.reply_markup.keyboard:
        new_row = []
        for btn in row:
            b_idx = int(btn.callback_data.split('_')[1]) if btn.callback_data != 'lt_none' else -1
            if b_idx == idx: new_row.append(InlineKeyboardButton("💥" if idx in booms else "💎", callback_data="lt_none"))
            else: new_row.append(btn)
            if btn.text == "💎" or (b_idx == idx and idx not in booms): safe += 1
        m.row(*new_row)
    if idx in booms:
        new_keys = k - 5; nr = update_keys(u, new_keys); del game_data[u]
        bot.edit_message_text(f"💥 <b>BÙM!</b> (-5 key)\n🔑 {new_keys} key ({nr})", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    else:
        new_keys = k + 2
        if safe == 6:
            new_keys += 10; nr = update_keys(u, new_keys); del game_data[u]
            bot.edit_message_text(f"🏆 <b>XUẤT SẮC!</b> (+12 key)\n🔑 {new_keys} key ({nr})", call.message.chat.id, call.message.message_id, parse_mode='HTML')
        else:
            nr = update_keys(u, new_keys)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=m)
            bot.answer_callback_query(call.id, f"💎 An toàn! +2 key (Tổng: {new_keys})")
    bot.answer_callback_query(call.id)

# ================= QUẢN TRỊ NHÓM & WEBHOOK =================
@bot.message_handler(commands=['kick', 'camchat', 'add'])
def group_admin(message):
    if not is_admin(message): return
    cmd = message.text.split()[0].replace('/', '')
    if cmd == 'add':
        try: bot.reply_to(message, f"🔗 Link mời:\n{bot.create_chat_invite_link(message.chat.id, member_limit=1).invite_link}")
        except Exception as e: bot.reply_to(message, f"❌ Lỗi: {e}")
        return
    if not message.reply_to_message: return bot.reply_to(message, f"❌ Reply tin nhắn người đó và gõ /{cmd}")
    try:
        if cmd == 'kick':
            bot.kick_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            bot.reply_to(message, "👢 Đã đuổi!")
        elif cmd == 'camchat':
            parts = message.text.split()
            if len(parts) < 2: return bot.reply_to(message, "❌ Thiếu thời gian (VD: 1h)")
            unit, val = parts[1][-1].lower(), int(parts[1][:-1])
            secs = val * {'m': 60, 'h': 3600, 'd': 86400}.get(unit, 60)
            bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False), until_date=int(time.time()) + secs)
            bot.reply_to(message, f"🤐 Đã cấm chat {parts[1]}!")
    except Exception as e: bot.reply_to(message, f"❌ Lỗi: {e}")

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook(): return "Bot đang chạy!", 200

if __name__ == "__main__":
    bot.remove_webhook()
    if os.environ.get('RENDER_EXTERNAL_URL'):
        bot.set_webhook(url=f"{os.environ.get('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
