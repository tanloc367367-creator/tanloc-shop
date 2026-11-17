import os
import telebot
from flask import Flask, request
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ================= CẤU HÌNH =================
BOT_TOKEN = os.environ.get('9238332861:AAGlo_aJxLohg1KO-syXahx8IIm7yALnSxg') # Lấy từ Render
ADMIN_ID = 9238332861 # Thay bằng ID Telegram của bạn
STK = "PMC2605614200000037"       # Số tài khoản của bạn
TEN_NGAN_HANG = "Techcombank" # Tên ngân hàng
GIA_TIEN = "50.000đ"

KEYS = [
    "KEY-APP-001",
    "KEY-APP-002",
    "KEY-APP-003"
]
# ============================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Giao diện Menu
def get_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🛒 Mua Key"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Chào bạn! Bấm nút bên dưới để mua key.", reply_markup=get_menu())

@bot.message_handler(func=lambda message: message.text == "🛒 Mua Key")
def buy_key(message):
    noi_dung = f"MUAKEY {message.from_user.id}"
    text = (f"👉 Vui lòng chuyển **{50k}**\n"
            f"🏦 Ngân hàng: **{MOMO}**\n"
            f"💳 STK: **{PMC2605614200000037}**\n"
            f"📝 Nội dung: **{DONECKSHOPKEYTANLOC}**\n\n"
            f"*(Lưu ý: Chuyển đúng nội dung để Admin dễ check)*")
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Tôi đã chuyển khoản", callback_data=f"paid_{message.from_user.id}"))
    
    bot.reply_to(message, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def handle_paid(call):
    user_id = call.data.split('_')[1]
    
    bot.answer_callback_query(call.id, "Đã gửi thông báo cho Admin. Vui lòng đợi chút nhé!")
    bot.send_message(call.from_user.id, "⏳ Đang chờ Admin kiểm tra và duyệt đơn...")
    
    admin_text = f"🔔 **CÓ ĐƠN HÀNG MỚI!**\nKhách hàng: {call.from_user.first_name} (@{call.from_user.username})\nID: `{user_id}`\nSố tiền: {GIA_TIEN}"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ DUYỆT & GỬI KEY", callback_data=f"approve_{user_id}"))
    
    bot.send_message(ADMIN_ID, admin_text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def handle_approve(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Bạn không phải Admin!", show_alert=True)
        return

    user_id = int(call.data.split('_')[1])
    
    if len(KEYS) == 0:
        bot.answer_callback_query(call.id, "❌ Đã hết key trong kho!", show_alert=True)
        return
        
    key_to_send = KEYS.pop(0)
    
    try:
        bot.send_message(user_id, f"🎉 Cảm ơn bạn đã mua hàng!\nKey của bạn là: `{key_to_send}`", parse_mode='Markdown')
        bot.edit_message_text(chat_id=ADMIN_ID, message_id=call.message.message_id, 
                              text=f"✅ Đã duyệt đơn của ID {user_id}. Đã gửi key: {key_to_send}.\n(Kho còn {len(KEYS)} key)", 
                              reply_markup=None)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Lỗi khi gửi tin nhắn: {e}", show_alert=True)

# ================= WEBHOOK CHO RENDER =================
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
