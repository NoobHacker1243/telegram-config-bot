import os
import json
import random
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# تنظیمات اصلی
BOT_TOKEN = "7978339304:AAESYFoIzMymbwoc4Vfsg3TyAmcR0MQOp_c"
ADMIN_ID = 7112285392
CHANNEL_USERNAME = "@V2File_Mamad"
BASE_DIR = "configs"
PRICE_FILE = "prices.json"

CATEGORIES = ["free", "paid", "vip"]
DEFAULT_PRICES = {"paid": 50000, "vip": 100000}

# ساخت پوشه و فایل قیمت
for cat in CATEGORIES:
    os.makedirs(os.path.join(BASE_DIR, cat), exist_ok=True)
if not os.path.exists(PRICE_FILE):
    with open(PRICE_FILE, "w") as f:
        json.dump(DEFAULT_PRICES, f)
with open(PRICE_FILE) as f:
    prices = json.load(f)

# متغیرهای موقتی
admin_pending_files = {}
admin_waiting_for_price = False
pending_payments = {}

# منوی اصلی
def get_main_menu(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("📥 فایل رایگان", callback_data="get_free")],
        [InlineKeyboardButton("💰 فایل پولی", callback_data="get_paid")],
        [InlineKeyboardButton("🌟 فایل VIP", callback_data="get_vip")],
        [InlineKeyboardButton("ℹ️ درباره ما", callback_data="about")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("💵 تنظیم قیمت", callback_data="set_price")])
    return InlineKeyboardMarkup(keyboard)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = (user_id == ADMIN_ID)
    await update.message.reply_text(
        "🎉 خوش اومدی! یکی از گزینه‌های زیر رو انتخاب کن 👇",
        reply_markup=get_main_menu(is_admin)
    )

# اجرای ربات
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🤖 ربات آماده اجراست...")
    app.run_polling()

# ایجاد وب‌سرور برای UptimeRobot
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "ربات آنلاین است ✅"

if __name__ == "__main__":
    import threading
    threading.Thread(target=main).start()
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
