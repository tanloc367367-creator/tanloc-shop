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
game_data, temp_lixi = {}, {}

def get_today(): return datetime.now().strftime("%Y-%m-%d")
def is_admin(msg): return msg.from_user.id == ADMIN_ID
def get_uname(msg): return f"@{msg.from_user.username}" if msg.from_user.username else None

def get_rank(k):
    if k >= 100: return "Kim Cương Cao Cấp 👑"
    if k >= 50: return "Kim Cương 💎"
    if k >= 25: return "Vàng 🥇"
    if k >= 10: return "Bạc 🥈"
    return "Đồng 🥉"

def db(query, params=(), f=None, c=False):
    conn = sqlite3.connect('ctv_data.db')
    cur = conn.cursor(); cur.execute(query, params)
    res = cur.fetchone() if f == 'one' else cur.fetchall() if f == 'all' else None
    if c: conn.commit()
    conn.close(); return res

db('''CREATE TABLE IF NOT EXISTS ctv (username TEXT PRIMARY KEY, chat_id INTEGER, keys INTEGER, xu INTEGER DEFAULT 0, rank TEXT, join_date TEXT, quote TEXT, last_checkin TEXT, streak INTEGER, last_wheel TEXT, kudos INTEGER, last_xinxu TEXT, last_baohiem TEXT, next_tx TEXT, next_doanso TEXT, next_rps TEXT, next_dovui TEXT, next_latthe TEXT)''')
db('''CREATE TABLE IF NOT EXISTS lixi (code TEXT PRIMARY KEY, creator TEXT, loai TEXT, tong INTEGER, con_lai INTEGER, so_nguoi INTEGER, da_nhan INTEGER DEFAULT 0, status TEXT DEFAULT 'active')''')
for col in ["chat_id INTEGER", "keys INTEGER", "xu INTEGER DEFAULT 0", "rank TEXT", "join_date TEXT", "quote TEXT", "last_checkin TEXT", "streak INTEGER DEFAULT 0", "last_wheel TEXT", "kudos INTEGER DEFAULT 0", "last_xinxu TEXT", "last_baohiem TEXT", "next_tx TEXT", "next_doanso TEXT", "next_rps TEXT", "next_dovui TEXT", "next_latthe TEXT"]:
    try: db(f"ALTER TABLE ctv ADD COLUMN {col}", c=True)
    except: pass

def upd_key(u, k):
    r = get_rank(k); db("UPDATE ctv SET keys=?, rank=? WHERE username=?", (k, r, u), c=True); return r
def upd_xu(u, x): db("UPDATE ctv SET xu = xu + ? WHERE username=?", (x, u), c=True)
def get_user(msg):
    u = get_uname(msg)
    if not u: bot.reply_to(msg, "❌ Cần Username Telegram!"); return None
    d = db("SELECT keys, xu FROM ctv WHERE username=?", (u,), f='one')
    if not d: bot.reply_to(msg, "❌ Chưa có trong hệ thống! Gõ /start."); return None
    return u, d[0], d[1]

# ================= MENU =================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(msg):
    u = get_uname(msg)
    if u:
        c = db("SELECT chat_id FROM ctv WHERE username=?", (u,), f='one')
        if c:
            db("UPDATE ctv SET chat_id=? WHERE username=?", (msg.chat.id, u), c=True)
            if not c[0]: 
                bot.reply_to(msg, f"🎉 Chào mừng <b>{u}</b> đã kích hoạt!", parse_mode='HTML')
        else: 
            db("INSERT INTO ctv (username, chat_id, keys, xu, rank, join_date) VALUES (?, ?, 0, 0, ?, ?)", (u, msg.chat.id, "Đồng 🥉", get_today()), c=True)

txt = ("Chào Sếp! Bot quản lý CTV.\n👇 Bấm nút bên dưới hoặc dùng lệnh:\n\n"
       "🛠 <b>Lệnh Admin:</b>\n/themctv /congkey /trukey /congxu /truxu /xoactv /thongke /thongbao /reset\n/soicau [ten_game]\n\n"
       "🧧 <b>Lì Xì:</b>\n/guilixi - Tạo túi lì xì\n/bulixi [mã] - Nhận lì xì\n\n"
       "🛡 <b>Quản trị nhóm:</b>\n/kick /camchat /add\n\n"
       "🎮 <b>Game & Tiện ích:</b>\n/game - Kho game (Dùng Xu)\n/chuyenxu /chuyenkey - Chuyển tiền\n/xinxu /baohiem - Cứu trợ\n/topxu - Đại gia"
       if is_admin(msg) else 
       "Chào bạn! Hệ thống quản lý CTV.\n👇 Bấm nút bên dưới hoặc dùng lệnh:\n\n"
       "👤 <b>Thông tin:</b>\n/vongquay /diemdanh /profile /setquote /khen\n\n"
       "💸 <b>Giao dịch:</b>\n/chuyenxu /chuyenkey\n\n"
       "🎁 <b>Cứu trợ:</b>\n/xinxu /baohiem\n\n"
       "🧧 <b>Lì Xì:</b>\n/bulixi [mã]\n\n"
       "🎮 <b>Game:</b>\n/game - Kho game (Dùng Xu)\n👉 Cú pháp chơi: /tengame [số xu]")

try: 
    bot.send_photo(msg.chat.id, BANNER_URL, caption=txt, parse_mode='HTML', reply_markup=get_menu())
except: 
    bot.reply_to(msg, txt, parse_mode='HTML', reply_markup=get_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu(call):
    bot.answer_callback_query(call.id)
    acts = {'menu_xephang': xep_hang, 'menu_capbac': xem_cap_bac, 'menu_nhiemvu': nhiem_vu, 'menu_info': xem_info, 'menu_vongquay': vong_quay, 'menu_diemdanh': diem_danh, 'menu_profile': xem_profile, 'menu_top': xem_top_3, 'menu_game': menu_game, 'menu_topxu': top_dai_gia}
    if call.data in acts: acts[call.data](call.message)

@bot.message_handler(commands=['game'])
def menu_game(msg):
    txt = ("🎮 <b>GAME GIẢI TRÍ</b> 🎮\n👉 <b>Cú pháp:</b> /tengame [số xu]\nVD: <code>/taixiu 10</code>\n\n🎰 Tài Xỉu\n🔢 Đoán Số\n✂️ Búa Kéo Bao\n❓ Đố Vui\n💣 Lật Thẻ")
    try: bot.send_photo(msg.chat.id, GAME_BANNER_URL, caption=txt, parse_mode='HTML', reply_markup=get_game_menu())
    except: bot.reply_to(msg, txt, parse_mode='HTML', reply_markup=get_game_menu())

# ================= TÍNH NĂNG =================
@bot.message_handler(commands=['chuyenxu', 'chuyenkey'])
def chuyen_tien(msg):
    u = get_user(msg)
    if not u: return
    s, sk, sx = u
    p = msg.text.split()
    if len(p) < 3 or not p[2].isdigit() or int(p[2]) <= 0: return bot.reply_to(msg, f"❌ Cú pháp: /{p[0][1:]} @ten so_luong")
    target, amt = p[1], int(p[2])
    if target == s: return bot.reply_to(msg, "🤦 Không thể tự chuyển!")
    if not db("SELECT username FROM ctv WHERE username=?", (target,), f='one'): return bot.reply_to(msg, f"❌ Không tìm thấy {target}!")
    
    is_key = 'key' in p[0]; icon = "🔑" if is_key else "🪙"
    if is_key:
        if sk < amt: return bot.reply_to(msg, f"❌ Bạn không đủ Key! (Có {sk})")
        upd_key(s, sk - amt); old_r = db("SELECT keys FROM ctv WHERE username=?", (target,), f='one')[0]; upd_key(target, old_r + amt)
        s_after, r_after = sk - amt, old_r + amt
    else:
        if sx < amt: return bot.reply_to(msg, f"❌ Bạn không đủ Xu! (Có {sx})")
        upd_xu(s, -amt); old_r = db("SELECT xu FROM ctv WHERE username=?", (target,), f='one')[0]; upd_xu(target, amt)
        s_after, r_after = sx - amt, old_r + amt

    txt = (f"💸 <b>{s}</b> ĐÃ CHUYỂN CHO <b>{target}</b> 💸\n\n📉 <b>SỐ DƯ BIẾN ĐỘNG:</b>\n👤 {s}: {sk if is_key else sx} {icon} ➡️ {s_after} {icon}\n👤 {target}: {old_r} {icon} ➡️ {r_after} {icon}\n\n🪎 <b>CHUYỂN THÀNH CÔNG!</b>")
    bot.reply_to(msg, txt, parse_mode='HTML')

@bot.message_handler(commands=['xinxu'])
def xin_xu(msg):
    u = get_user(msg)
    if not u: return
    un = u[0]
    if db("SELECT last_xinxu FROM ctv WHERE username=?", (un,), f='one')[0] == get_today(): return bot.reply_to(msg, "⏳ Hôm nay đã xin rồi!")
    amt = random.randint(1, 200); upd_xu(un, amt); db("UPDATE ctv SET last_xinxu=? WHERE username=?", (get_today(), un), c=True)
    bot.reply_to(msg, f"🎁 Bạn xin được <b>{amt} xu</b>!", parse_mode='HTML')

@bot.message_handler(commands=['baohiem'])
def bao_hiem(msg):
    u = get_user(msg)
    if not u: return
    un, k, x = u
    if db("SELECT last_baohiem FROM ctv WHERE username=?", (un,), f='one')[0] == get_today(): return bot.reply_to(msg, "⏳ Hôm nay đã nhận rồi!")
    if x >= 100: return bot.reply_to(msg, f"❌ Bạn có {x} xu (trên 100), không đủ điều kiện!")
    upd_xu(un, 100); db("UPDATE ctv SET last_baohiem=? WHERE username=?", (get_today(), un), c=True)
    bot.reply_to(msg, "🛡 Bạn đã nhận <b>100 xu</b> bảo hiểm!", parse_mode='HTML')

@bot.message_handler(commands=['vongquay'])
def vong_quay(msg):
    u = get_user(msg)
    if not u: return
    un, k, x = u
    p = msg.text.split()
    if len(p) == 1:
        if db("SELECT last_wheel FROM ctv WHERE username=?", (un,), f='one')[0] == get_today(): return bot.reply_to(msg, "⏳ Hết lượt free! Cược xu: /vongquay [số xu]")
        won = random.choices([0, 1, 1, 3, 5], weights=[40, 30, 15, 10, 5], k=1)[0]; upd_xu(un, won); db("UPDATE ctv SET last_wheel=? WHERE username=?", (get_today(), un), c=True)
        bot.reply_to(msg, f"🎲 <b>QUAY FREE</b>\nKết quả: <b>{won} xu</b>!\nTổng: {x+won} xu", parse_mode='HTML')
    else:
        try: cost = int(p[1])
        except: return bot.reply_to(msg, "❌ Số xu không hợp lệ!")
        if cost < 10: return bot.reply_to(msg, "❌ Cược tối thiểu 10 xu!")
        if x < cost: return bot.reply_to(msg, f"❌ Không đủ {cost} xu! (Có {x})")
        mult = random.choices([0, 1.5, 2, 5], weights=[50, 25, 20, 5], k=1)[0]; won = int(cost * mult); upd_xu(un, won - cost)
        if mult == 0: bot.reply_to(msg, f"🎲 <b>QUAY CƯỢC</b>\nCược {cost} xu.\nKết quả: <b>TRƯỢT (Mất {cost})</b>\nTổng: {x - cost} xu", parse_mode='HTML')
        else: bot.reply_to(msg, f"🎲 <b>QUAY CƯỢC</b>\nCược {cost} xu.\nKết quả: <b>x{mult}</b>!\nThắng: <b>{won} xu</b>.\nTổng: {x - cost + won} xu", parse_mode='HTML')

@bot.message_handler(commands=['xephang'])
def xep_hang(msg):
    us = db("SELECT username, keys, rank FROM ctv ORDER BY keys DESC", f='all')
    txt = "🏆 <b>XẾP HẠNG KEY</b> 🏆\n\n" + "".join([f"{i}. {u[0]} | {u[2]} | {u[1]} key\n" for i, u in enumerate(us, 1)]) if us else "📭 Trống!"
    bot.reply_to(msg, txt, parse_mode='HTML')

@bot.message_handler(commands=['topxu'])
def top_dai_gia(msg):
    us = db("SELECT username, xu FROM ctv ORDER BY xu DESC LIMIT 5", f='all')
    md = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    txt = "💰 <b>TOP 5 ĐẠI GIA</b> 💰\n\n" + "".join([f"{md[i]} {u[0]}: <b>{u[1]} xu</b>\n" for i, u in enumerate(us)]) if us else "📭 Trống!"
    bot.reply_to(msg, txt, parse_mode='HTML')

@bot.message_handler(commands=['capbac'])
def xem_cap_bac(msg):
    us = db("SELECT username, rank, keys FROM ctv ORDER BY keys DESC", f='all')
    txt = "📊 <b>CẤP BẬC</b> 📊\n\n" + "".join([f"👤 {u[0]}: <b>{u[1]}</b> ({u[2]} key)\n" for u in us]) if us else "📭 Trống!"
    bot.reply_to(msg, txt, parse_mode='HTML')

@bot.message_handler(commands=['top'])
def xem_top_3(msg):
    us = db("SELECT username, keys, rank FROM ctv ORDER BY keys DESC LIMIT 3", f='all')
    md = ["🥇", "🥈", "🥉"]
    txt = "🔥 <b>TOP 3</b> 🔥\n\n" + "".join([f"{md[i]} {u[0]} | {u[2]} | {u[1]} key\n" for i, u in enumerate(us)]) if us else "📭 Trống!"
    bot.reply_to(msg, txt, parse_mode='HTML')

@bot.message_handler(commands=['nhiemvu'])
def nhiem_vu(msg):
    p = msg.text.split()
    if len(p) == 1: return bot.reply_to(msg, "🎯 <b>NHIỆM VỤ</b>\n1. Bán 5 key\n2. Bán 20 key\n3. Bán 30 key\n👉 Xem: <code>/nhiemvu @ten</code>", parse_mode='HTML')
    d = db("SELECT keys FROM ctv WHERE username=?", (p[1],), f='one')
    if not d: return bot.reply_to(msg, f"❌ Không thấy {p[1]}!")
    k = d[0]
    bot.reply_to(msg, f"🎯 <b>TIẾN ĐỘ {p[1]}</b>\nTổng: <b>{k} key</b>\n1. Mốc 5: {'✅' if k >= 5 else f'❌ Thiếu {5-k}'}\n2. Mốc 20: {'✅' if k >= 20 else f'❌ Thiếu {20-k}'}\n3. Mốc 30: {'✅' if k >= 30 else f'❌ Thiếu {30-k}'}", parse_mode='HTML')

@bot.message_handler(commands=['info'])
def xem_info(msg):
    u = get_user(msg)
    if not u: return
    k, x = db("SELECT keys, xu FROM ctv WHERE username=?", (u[0],), f='one')
    goal = f"{10-k} lên Bạc" if k < 10 else f"{25-k} lên Vàng" if k < 25 else f"{50-k} lên K.Cương" if k < 50 else f"{100-k} lên K.Cương VIP" if k < 100 else "Max!"
    bot.reply_to(msg, f"👤 <b>{u[0]}</b>\n📊 Cấp: <b>{get_rank(k)}</b>\n🔑 Key: <b>{k}</b>\n🪙 Xu: <b>{x}</b>\n🎯 Mục tiêu: {goal}", parse_mode='HTML')

@bot.message_handler(commands=['profile'])
def xem_profile(msg):
    u = get_user(msg)
    if not u: return
    d = db("SELECT keys, xu, rank, join_date, quote, kudos FROM ctv WHERE username=?", (u[0],), f='one')
    bot.reply_to(msg, f"💳 <b>THẺ CTV</b> 💳\n-------------------\n👤 <b>Chủ thẻ:</b> {u[0]}\n📅 <b>Gia nhập:</b> {d[3] or 'Không rõ'}\n🏅 <b>Cấp bậc:</b> {d[2]}\n🔑 <b>Key:</b> {d[0]}\n🪙 <b>Xu:</b> {d[1]}\n💖 <b>Khen:</b> {d[5] or 0}\n-------------------\n💬 <b>Châm ngôn:</b> <i>\"{d[4] or 'Chưa có...'}\"</i>", parse_mode='HTML')

@bot.message_handler(commands=['setquote'])
def set_quote(msg):
    u = get_uname(msg)
    if not u: return
    txt = msg.text.replace('/setquote', '').strip()
    if not txt or len(txt) > 50: return bot.reply_to(msg, "❌ Châm ngôn phải từ 1-50 ký tự!")
    db("UPDATE ctv SET quote=? WHERE username=?", (txt, u), c=True)
    bot.reply_to(msg, f"✅ Đã đổi: <i>\"{txt}\"</i>", parse_mode='HTML')

@bot.message_handler(commands=['diemdanh'])
def diem_danh(msg):
    u = get_user(msg)
    if not u: return
    un, k, x = u
    lc, st = db("SELECT last_checkin, streak FROM ctv WHERE username=?", (un,), f='one')
    if lc == get_today(): return bot.reply_to(msg, "⏳ Đã điểm danh hôm nay!")
    st = st + 1 if lc == (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") else 1
    add = 1; bonus = ""
    if st >= 7: add += 5; bonus = "\n🔥 Chuỗi 7 ngày! Thưởng +5 xu!"; st = 0
    upd_xu(un, add); db("UPDATE ctv SET last_checkin=?, streak=? WHERE username=?", (get_today(), st, un), c=True)
    bot.reply_to(msg, f"✅ Nhận <b>{add} xu</b>! (Chuỗi: {st}/7){bonus}\nTổng: {x+add} xu", parse_mode='HTML')

@bot.message_handler(commands=['khen'])
def khen(msg):
    p = msg.text.split()
    if len(p) < 2: return bot.reply_to(msg, "❌ Cú pháp: /khen @ten")
    target, me = p[1], get_uname(msg)
    if target == me: return bot.reply_to(msg, "🤦 Không tự khen mình!")
    d = db("SELECT kudos FROM ctv WHERE username=?", (target,), f='one')
    if not d: return bot.reply_to(msg, f"❌ Không thấy {target}!")
    db("UPDATE ctv SET kudos=? WHERE username=?", ((d[0] or 0) + 1, target), c=True)
    bot.reply_to(msg, f"💖 <b>{me}</b> đã khen <b>{target}</b>!", parse_mode='HTML')

@bot.message_handler(commands=['thongbao'])
def thong_bao(msg):
    if not is_admin(msg): return
    txt = msg.text.replace('/thongbao', '').strip()
    if not txt: return
    us = db("SELECT username, chat_id FROM ctv", f='all')
    s, f, failed = 0, 0, []
    for un, cid in us:
        try: bot.send_message(cid or un, f"📢 <b>THÔNG BÁO</b> 📢\n\n{txt}", parse_mode='HTML'); s += 1; time.sleep(0.1)
        except: f += 1; failed.append(un)
    m = f"✅ Thành công: {s}.\n❌ Thất bại: {f}."
    if failed: m += f"\n👉 Chưa /start: {', '.join(failed)}"
    bot.reply_to(msg, m)

# ================= ADMIN =================
@bot.message_handler(commands=['themctv', 'xoactv', 'congkey', 'trukey', 'congxu', 'truxu', 'thongke', 'reset'])
def admin_cmd(msg):
    if not is_admin(msg): return
    cmd = msg.text.split()[0].replace('/', '')
    try:
        if cmd == 'themctv':
            un = msg.text.split()[1]
            if db("SELECT username FROM ctv WHERE username=?", (un,), f='one'): return bot.reply_to(msg, "⚠️ Đã có!")
            db("INSERT INTO ctv (username, keys, xu, rank, join_date) VALUES (?, 0, 0, ?, ?)", (un, "Đồng 🥉", get_today()), c=True)
            bot.reply_to(msg, f"✅ Đã thêm {un}.")
            cid = db("SELECT chat_id FROM ctv WHERE username=?", (un,), f='one')[0]
            if cid: bot.send_message(cid, f"🎉 Chào mừng <b>{un}</b>! Gõ /start.", parse_mode='HTML')
        elif cmd == 'xoactv': db("DELETE FROM ctv WHERE username=?", (msg.text.split()[1],), c=True); bot.reply_to(msg, "🗑 Đã xóa!")
        elif cmd in ['congkey', 'trukey']:
            un, num = msg.text.split()[1], int(msg.text.split()[2]) * (1 if cmd == 'congkey' else -1)
            d = db("SELECT keys FROM ctv WHERE username=?", (un,), f='one')
            if not d: return bot.reply_to(msg, f"❌ Không thấy {un}!")
            old_r, new_r = get_rank(d[0]), upd_key(un, max(0, d[0] + num))
            bot.reply_to(msg, f"✅ Đã cập nhật {num} key cho {un}.\nTổng: {d[0] + num} ({new_r})")
            if old_r != new_r and num > 0: bot.send_message(msg.chat.id, f"🎉 <b>{un}</b> thăng cấp <b>{new_r}</b>!", parse_mode='HTML')
        elif cmd in ['congxu', 'truxu']:
            un, num = msg.text.split()[1], int(msg.text.split()[2]) * (1 if cmd == 'congxu' else -1)
            d = db("SELECT xu FROM ctv WHERE username=?", (un,), f='one')
            if not d: return bot.reply_to(msg, f"❌ Không thấy {un}!")
            db("UPDATE ctv SET xu=? WHERE username=?", (max(0, d[0] + num), un), c=True)
            bot.reply_to(msg, f"✅ Đã cập nhật {num} xu cho {un}.\nTổng: {max(0, d[0] + num)} xu")
        elif cmd == 'thongke':
            t = db("SELECT COUNT(*), SUM(keys), SUM(xu) FROM ctv", f='one'); top1 = db("SELECT username, keys FROM ctv ORDER BY keys DESC LIMIT 1", f='one')
            txt = f"📈 <b>THỐNG KÊ</b>\n👥 CTV: <b>{t[0]}</b>\n🔑 Key: <b>{t[1] or 0}</b>\n🪙 Xu: <b>{t[2] or 0}</b>"
            if top1: txt += f"\n🥇 Top 1: {top1[0]} ({top1[1]} key)"
            bot.reply_to(msg, txt, parse_mode='HTML')
        elif cmd == 'reset': db("UPDATE ctv SET keys=0, xu=0, rank='Đồng 🥉', streak=0, kudos=0", c=True); bot.reply_to(msg, "🧹 Đã reset!")
    except Exception as e: bot.reply_to(msg, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['soicau'])
def soi_cau(msg):
    if not is_admin(msg): return bot.reply_to(msg, "❌ Chỉ Admin!")
    p = msg.text.split()
    if len(p) < 2: return bot.reply_to(msg, "❌ Cú pháp: /soicau [taixiu/doanso/keobuabao/dovui/latthe]")
    g = p[1].lower(); col, dd, txt = "", "", ""
    if g == 'taixiu': col, dd, txt = 'next_tx', random.choice(['tai', 'xiu']), "TÀI" if dd == 'tai' else "XỈU"
    elif g == 'doanso': col, dd, txt = 'next_doanso', str(random.randint(1, 50)), dd
    elif g == 'keobuabao': col, dd, txt = 'next_rps', random.choice(['bua', 'keo', 'bao']), {'bua': 'BÚA', 'keo': 'KÉO', 'bao': 'BAO'}[dd]
    elif g == 'dovui': q, opts, ans = random.choice(DOVUI); col, dd, txt = 'next_dovui', str(ans), opts[ans]
    elif g == 'latthe': col, dd, txt = 'next_latthe', ",".join(map(str, random.sample(range(9), 3))), f"Vị trí Boom: {dd}"
    else: return bot.reply_to(msg, "❌ Game không hợp lệ!")
    db(f"UPDATE ctv SET {col}=? WHERE username=?", (dd, get_uname(msg)), c=True)
    bot.reply_to(msg, f"🔮 <b>SOI CẦU {g.upper()}</b> 🔮\nVán tới ra: <b>{txt}</b>\n(100% - Chỉ Admin thấy)", parse_mode='HTML')

# ================= LÌ XÌ =================
@bot.message_handler(commands=['guilixi'])
def gui_lixi(msg):
    if len(msg.text.split()) == 1:
        temp_lixi[msg.from_user.id] = {'step': 1, 'loai': '', 'tong': 0, 'so_nguoi': 0}
        m = InlineKeyboardMarkup().row(InlineKeyboardButton("🔑 Key", callback_data="lixi_loai_key"), InlineKeyboardButton("🪙 Xu", callback_data="lixi_loai_xu"))
        return bot.reply_to(msg, "🧧 <b>TẠO LÌ XÌ</b> 🧧\nBước 1: Chọn loại:", parse_mode='HTML', reply_markup=m)
    bot.reply_to(msg, "❌ Gõ /guilixi để tạo.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('lixi_loai_'))
def lixi_loai(call):
    loai = call.data.split('_')[2]; temp_lixi[call.from_user.id] = {'step': 2, 'loai': loai, 'tong': 0, 'so_nguoi': 0}
    bot.edit_message_text(f"🧧 Gửi lì xì bằng <b>{loai.upper()}</b>.\nBước 2: Nhập tổng số {loai}.\n(Cú pháp: <code>/số</code>. VD: <code>/100</code>)", call.message.chat.id, call.message.message_id, parse_mode='HTML'); bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.from_user.id in temp_lixi and m.text.startswith('/'))
def lixi_nhap(msg):
    st = temp_lixi[msg.from_user.id]; txt = msg.text.replace('/', '').strip()
    if not txt.isdigit(): return bot.reply_to(msg, "❌ Nhập số hợp lệ (VD: /100).")
    val = int(txt); u = get_user(msg)
    if not u: return
    if st['step'] == 2:
        bal = u[1] if st['loai'] == 'key' else u[2]
        if bal < val: return bot.reply_to(msg, f"❌ Không đủ {st['loai']}! (Có {bal}).")
        st['tong'] = val; st['step'] = 3
        bot.reply_to(msg, f"✅ Tổng: <b>{val} {st['loai']}</b>.\nBước 3: Nhập số người nhận.\n(Cú pháp: <code>/số_người</code>. VD: <code>/5</code>)", parse_mode='HTML')
    elif st['step'] == 3:
        if val <= 0 or val > 100: return bot.reply_to(msg, "❌ Số người 1-100.")
        st['so_nguoi'] = val; code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)); un = u[0]
        db("UPDATE ctv SET keys = keys - ? WHERE username=?", (st['tong'], un), c=True) if st['loai'] == 'key' else db("UPDATE ctv SET xu = xu - ? WHERE username=?", (st['tong'], un), c=True)
        db("INSERT INTO lixi (code, creator, loai, tong, con_lai, so_nguoi) VALUES (?, ?, ?, ?, ?, ?)", (code, un, st['loai'], st['tong'], st['tong'], st['so_nguoi']), c=True)
        del temp_lixi[msg.from_user.id]
        bot.reply_to(msg, f"🧧 <b>TẠO THÀNH CÔNG!</b>\n👤 Gửi: {un}\n🎁 Loại: {st['loai'].upper()} (Tổng: {st['tong']})\n👥 Số người: <b>{st['so_nguoi']}</b>\n\n👉 Nhập <code>/bulixi {code}</code> để nhận.\n(Nhanh tay, đủ người túi sẽ đóng!)", parse_mode='HTML')

@bot.message_handler(commands=['bulixi'])
def nhan_lixi(msg):
    p = msg.text.split()
    if len(p) < 2: return bot.reply_to(msg, "❌ Cú pháp: /bulixi [mã]")
    code = p[1].upper(); u = get_user(msg)
    if not u: return
    un = u[0]; li = db("SELECT * FROM lixi WHERE code=?", (code,), f='one')
    if not li: return bot.reply_to(msg, "❌ Mã không tồn tại!")
    if li[7] == 'closed': return bot.reply_to(msg, "🧧 Túi đã hết!")
    loai, tong, con_lai, so_nguoi, da_nhan = li[2], li[3], li[4], li[5], li[6]
    if da_nhan >= so_nguoi: db("UPDATE lixi SET status='closed' WHERE code=?", (code,), c=True); return bot.reply_to(msg, "🧧 Túi đã hết lượt!")
    nguoi_con = so_nguoi - da_nhan
    nhan = con_lai if nguoi_con == 1 else random.randint(int(con_lai * 0.1), int(con_lai * 0.5))
    if nhan >= con_lai: nhan = con_lai - 1
    if nhan < 1: nhan = 1 
    con_moi = con_lai - nhan; da_moi = da_nhan + 1
    status = 'closed' if da_moi >= so_nguoi or con_moi <= 0 else 'active'
    db("UPDATE lixi SET con_lai=?, da_nhan=?, status=? WHERE code=?", (con_moi, da_moi, status, code), c=True)
    upd_key(un, db("SELECT keys FROM ctv WHERE username=?", (un,), f='one')[0] + nhan) if loai == 'key' else upd_xu(un, nhan)
    bot.reply_to(msg, f"🧧 <b>CHÚC MỪNG!</b> 🧧\nBạn nhận được <b>{nhan} {loai.upper()}</b> từ {li[1]}.\n\n⏳ Còn {so_nguoi - da_moi} lượt.", parse_mode='HTML')
    if status == 'closed': bot.send_message(msg.chat.id, f"🎊 <b>TÚI LÌ XÌ {code} ĐÃ HẾT!</b>\nCảm ơn <b>{li[1]}</b> đã tặng {tong} {loai}!", parse_mode='HTML')

# ================= GAME =================
DOVUI = [("Con gì càng lớn càng nhỏ?", ["Con cua", "Con rắn", "Con voi"], 0), ("Trái gì ăn sống chua, nấu chín ngọt?", ["Chanh", "Khế", "Me"], 0), ("Cái gì của bạn nhưng người khác dùng nhiều hơn?", ["Tên", "Điện thoại", "Quần áo"], 0), ("Năm nào có 28 ngày?", ["12 tháng", "1 tháng", "2 tháng"], 0)]

def game_check(msg, args, min_cost):
    u = get_user(msg)
    if not u: return None
    un, k, x = u
    cost = min_cost
    if len(args) > 1:
        try: cost = int(args[1])
        except: bot.reply_to(msg, "❌ Số xu không hợp lệ. Cú pháp: /tengame [số xu]"); return None
        if cost < min_cost: bot.reply_to(msg, f"❌ Cược tối thiểu {min_cost}!"); return None
    if x < cost: bot.reply_to(msg, f"❌ Cần {cost} xu! (Có {x})"); return None
    return un, k, x, cost

@bot.message_handler(commands=['taixiu'])
def game_tai_xiu(msg):
    r = game_check(msg, msg.text.split(), 5)
    if not r: return
    un, k, x, cost = r
    m = InlineKeyboardMarkup().row(InlineKeyboardButton("🎲 TÀI", callback_data=f"tx_tai_{cost}"), InlineKeyboardButton("🎲 XỈU", callback_data=f"tx_xiu_{cost}")).row(InlineKeyboardButton("❌ Hủy", callback_data="tx_huy"))
    bot.reply_to(msg, f"🎰 <b>TÀI XỈU</b>\nCược <b>{cost} xu</b>. Chọn:", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('tx_'))
def handle_tx(call):
    if call.data == 'tx_huy': return bot.edit_message_text("❌ Hủy.", call.message.chat.id, call.message.message_id)
    u = get_uname(call)
    if not u: return bot.answer_callback_query(call.id, "Cần Username!", show_alert=True)
    p = call.data.split('_'); cuoc, cost = p[1], int(p[2])
    x = db("SELECT xu FROM ctv WHERE username=?", (u,), f='one')[0]
    if x < cost: return bot.answer_callback_query(call.id, f"Không đủ {cost} xu!", show_alert=True)
    nt = db("SELECT next_tx FROM ctv WHERE next_tx IS NOT NULL LIMIT 1", f='one')
    kq = nt[0] if nt and nt[0] else ('tai' if random.randint(3, 18) >= 11 else 'xiu')
    if nt: db("UPDATE ctv SET next_tx=NULL WHERE next_tx IS NOT NULL", c=True)
    while True:
        d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6); t = d1+d2+d3
        if (kq == 'tai' and t >= 11) or (kq == 'xiu' and t <= 10): break
    ch = cost if cuoc == kq else -cost; st = f"🎉 THẮNG (+{cost})" if cuoc == kq else f"😭 THUA (-{cost})"
    upd_xu(u, ch)
    bot.edit_message_text(f"🎲 {d1}-{d2}-{d3} = <b>{t}</b> ({'TÀI' if kq == 'tai' else 'XỈU'})\n{st}\n🪙 {x + ch} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML'); bot.answer_callback_query(call.id)

@bot.message_handler(commands=['doanso'])
def game_doanso(msg):
    r = game_check(msg, msg.text.split(), 2)
    if not r: return
    un, k, x, cost = r
    game_data[un] = random.randint(1, 50)
    m = InlineKeyboardMarkup()
    for i in range(1, 51, 10): m.row(*[InlineKeyboardButton(str(j), callback_data=f"doan_{j}_{cost}") for j in range(i, i+10)])
    bot.reply_to(msg, f"🔢 <b>ĐOÁN SỐ</b>\nCược <b>{cost} xu</b>. Đúng +{cost}, sai -{cost}.", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('doan_'))
def handle_doanso(call):
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    p = call.data.split('_'); chon, cost = int(p[1]), int(p[2])
    x = db("SELECT xu FROM ctv WHERE username=?", (u,), f='one')[0]
    if x < cost: return bot.answer_callback_query(call.id, f"Không đủ {cost} xu!", show_alert=True)
    na = db("SELECT next_doanso FROM ctv WHERE next_doanso IS NOT NULL LIMIT 1", f='one')
    mm = int(na[0]) if na and na[0] else game_data.pop(u)
    if na: db("UPDATE ctv SET next_doanso=NULL WHERE next_doanso IS NOT NULL", c=True)
    ch = cost if chon == mm else -cost; st = f"🎉 ĐÚNG (+{cost})" if chon == mm else f"😭 SAI (-{cost}). Đáp án: {mm}"
    upd_xu(u, ch)
    bot.edit_message_text(f"🔢 Chọn: <b>{chon}</b>\n{st}\n🪙 {x + ch} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML'); bot.answer_callback_query(call.id)

@bot.message_handler(commands=['keobuabao', 'buakeobao'])
def game_rps(msg):
    r = game_check(msg, msg.text.split(), 3)
    if not r: return
    un, k, x, cost = r
    m = InlineKeyboardMarkup().row(InlineKeyboardButton("✊ Búa", callback_data=f"rps_bua_{cost}"), InlineKeyboardButton("✌️ Kéo", callback_data=f"rps_keo_{cost}"), InlineKeyboardButton("✋ Bao", callback_data=f"rps_bao_{cost}"))
    bot.reply_to(msg, f"✂️ <b>BÚA KÉO BAO</b>\nCược <b>{cost} xu</b>. Chọn:", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rps_'))
def handle_rps(call):
    u = get_uname(call)
    if not u: return
    p = call.data.split('_'); pl, cost = p[1], int(p[2])
    x = db("SELECT xu FROM ctv WHERE username=?", (u,), f='one')[0]
    if x < cost: return bot.answer_callback_query(call.id, f"Không đủ {cost} xu!", show_alert=True)
    b = random.choice(['bua', 'keo', 'bao']); nr = db("SELECT next_rps FROM ctv WHERE next_rps IS NOT NULL LIMIT 1", f='one')
    if nr and nr[0]: b = nr[0]; db("UPDATE ctv SET next_rps=NULL WHERE next_rps IS NOT NULL", c=True)
    ten = {'bua': '✊ Búa', 'keo': '✌️ Kéo', 'bao': '✋ Bao'}
    if pl == b: ch, st = 0, "🤝 HÒA"
    elif (pl == 'bua' and b == 'keo') or (pl == 'keo' and b == 'bao') or (pl == 'bao' and b == 'bua'): ch, st = cost, f"🎉 THẮNG (+{cost})"
    else: ch, st = -cost, f"😭 THUA (-{cost})"
    upd_xu(u, ch)
    bot.edit_message_text(f"Bạn: {ten[pl]} | Bot: {ten[b]}\n{st}\n🪙 {x + ch} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML'); bot.answer_callback_query(call.id)

@bot.message_handler(commands=['dovui'])
def game_dovui(msg):
    r = game_check(msg, msg.text.split(), 2)
    if not r: return
    un, k, x, cost = r
    q, opts, ans = random.choice(DOVUI); game_data[un] = ans
    m = InlineKeyboardMarkup()
    for i, o in enumerate(opts): m.add(InlineKeyboardButton(o, callback_data=f"dv_{i}_{cost}"))
    bot.reply_to(msg, f"❓ <b>ĐỐ VUI</b>\n{q}\n(Đúng +{cost}, Sai -{cost})", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dv_'))
def handle_dv(call):
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    p = call.data.split('_'); chon, cost = int(p[1]), int(p[2])
    x = db("SELECT xu FROM ctv WHERE username=?", (u,), f='one')[0]
    if x < cost: return bot.answer_callback_query(call.id, f"Không đủ {cost} xu!", show_alert=True)
    ans = game_data.pop(u); nd = db("SELECT next_dovui FROM ctv WHERE next_dovui IS NOT NULL LIMIT 1", f='one')
    if nd and nd[0]: ans = int(nd[0]); db("UPDATE ctv SET next_dovui=NULL WHERE next_dovui IS NOT NULL", c=True)
    ch = cost if chon == ans else -cost; st = f"🎉 ĐÚNG (+{cost})" if chon == ans else f"😭 SAI (-{cost})"
    upd_xu(u, ch)
    bot.edit_message_text(f"{st}\n🪙 {x + ch} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML'); bot.answer_callback_query(call.id)

@bot.message_handler(commands=['latthe'])
def game_latthe(msg):
    r = game_check(msg, msg.text.split(), 5)
    if not r: return
    un, k, x, cost = r
    booms = random.sample(range(9), 3); nl = db("SELECT next_latthe FROM ctv WHERE next_latthe IS NOT NULL LIMIT 1", f='one')
    if nl and nl[0]: booms = [int(i) for i in nl[0].split(',')]; db("UPDATE ctv SET next_latthe=NULL WHERE next_latthe IS NOT NULL", c=True)
    game_data[un] = {'booms': booms, 'cost': cost, 'safe': 0}
    m = InlineKeyboardMarkup()
    for i in range(0, 9, 3): m.row(*[InlineKeyboardButton("❓", callback_data=f"lt_{j}") for j in range(i, i+3)])
    bot.reply_to(msg, f"💣 <b>LẬT THẺ</b>\nCược <b>{cost} xu</b>. Né 3 boom. An toàn +{cost//2}, hết 6 ô thưởng lớn.", parse_mode='HTML', reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lt_'))
def handle_lt(call):
    if call.data == 'lt_none': return bot.answer_callback_query(call.id)
    u = get_uname(call)
    if not u or u not in game_data: return bot.answer_callback_query(call.id, "Hết hạn!", show_alert=True)
    st = game_data[u]; cost, booms = st['cost'], st['booms']; x = db("SELECT xu FROM ctv WHERE username=?", (u,), f='one')[0]
    idx = int(call.data.split('_')[1]); m = InlineKeyboardMarkup(); safe = 0
    for row in call.message.reply_markup.keyboard:
        nr = []
        for btn in row:
            bi = int(btn.callback_data.split('_')[1]) if btn.callback_data != 'lt_none' else -1
            if bi == idx: nr.append(InlineKeyboardButton("💥" if idx in booms else "💎", callback_data="lt_none"))
            else: nr.append(btn)
            if btn.text == "💎" or (bi == idx and idx not in booms): safe += 1
        m.row(*nr)
    if idx in booms:
        upd_xu(u, -cost); del game_data[u]
        bot.edit_message_text(f"💥 <b>BÙM!</b> (-{cost} xu)\n🪙 {x - cost} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML')
    else:
        th = cost // 2; upd_xu(u, th)
        if safe == 6:
            bn = cost * 2; upd_xu(u, bn); del game_data[u]
            bot.edit_message_text(f"🏆 <b>XUẤT SẮC!</b> (+{th} và thưởng {bn})\n🪙 {x + th + bn} xu", call.message.chat.id, call.message.message_id, parse_mode='HTML')
        else:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=m)
            bot.answer_callback_query(call.id, f"💎 An toàn! +{th} xu (Tổng: {x + th})")
    bot.answer_callback_query(call.id)

# ================= QUẢN TRỊ NHÓM & WEBHOOK =================
@bot.message_handler(commands=['kick', 'camchat', 'add'])
def group_admin(msg):
    if not is_admin(msg): return
    cmd = msg.text.split()[0].replace('/', '')
    if cmd == 'add':
        try: bot.reply_to(msg, f"🔗 Link: {bot.create_chat_invite_link(msg.chat.id, member_limit=1).invite_link}")
        except Exception as e: bot.reply_to(msg, f"❌ Lỗi: {e}")
        return
    if not msg.reply_to_message: return bot.reply_to(msg, f"❌ Reply tin nhắn và gõ /{cmd}")
    try:
        if cmd == 'kick': bot.kick_chat_member(msg.chat.id, msg.reply_to_message.from_user.id); bot.reply_to(msg, "👢 Đã đuổi!")
        elif cmd == 'camchat':
            p = msg.text.split()
            if len(p) < 2: return bot.reply_to(msg, "❌ Thiếu tgian (VD: 1h)")
            secs = int(p[1][:-1]) * {'m': 60, 'h': 3600, 'd': 86400}.get(p[1][-1].lower(), 60)
            bot.restrict_chat_member(msg.chat.id, msg.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False), until_date=int(time.time()) + secs)
            bot.reply_to(msg, f"🤐 Đã cấm chat {p[1]}!")
    except Exception as e: bot.reply_to(msg, f"❌ Lỗi: {e}")

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage(): bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))]); return "!", 200
@app.route("/")
def webhook(): return "Bot đang chạy!", 200

if __name__ == "__main__":
    bot.remove_webhook()
    if os.environ.get('RENDER_EXTERNAL_URL'): bot.set_webhook(url=f"{os.environ.get('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
