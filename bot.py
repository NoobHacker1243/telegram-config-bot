import os
import json
import random
import asyncio
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

# ساخت پوشه‌ها و فایل قیمت در صورت نیاز
for cat in CATEGORIES:
    os.makedirs(os.path.join(BASE_DIR, cat), exist_ok=True)
if not os.path.exists(PRICE_FILE):
    with open(PRICE_FILE, "w") as f:
        json.dump(DEFAULT_PRICES, f)
with open(PRICE_FILE) as f:
    prices = json.load(f)

# متغیرهای موقتی
admin_pending_files = {}
pending_payments = {}  # ذخیره رسید پرداخت (عکس) کاربر
admin_waiting_for_price = False

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

# دریافت فایل از ادمین
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔️ فقط ادمین می‌تونه فایل بفرسته.")
        return

    doc: Document = update.message.document
    admin_pending_files[user_id] = {
        "file_id": doc.file_id,
        "file_name": doc.file_name
    }

    keyboard = [
        [InlineKeyboardButton("🔓 رایگان", callback_data="save_free")],
        [InlineKeyboardButton("💰 پولی", callback_data="save_paid")],
        [InlineKeyboardButton("🌟 VIP", callback_data="save_vip")]
    ]
    await update.message.reply_text("📁 فایل رو تو کدوم دسته ذخیره کنم؟", reply_markup=InlineKeyboardMarkup(keyboard))

# ذخیره فایل
async def save_file_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in admin_pending_files:
        await query.edit_message_text("❗️فایلی در صف ذخیره نیست.")
        return

    data = admin_pending_files.pop(user_id)
    category = query.data.replace("save_", "")
    folder_path = os.path.join(BASE_DIR, category)
    file_path = os.path.join(folder_path, data["file_name"])

    file = await context.bot.get_file(data["file_id"])
    await file.download_to_drive(file_path)

    await query.edit_message_text(f"✅ فایل در دسته {category.upper()} ذخیره شد.")

# نمایش اطلاعات پرداخت
async def show_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    price = prices.get(category, 0)
    message = (
        f"💳 برای دریافت فایل {category.upper()}:\n\n"
        f"🏷 مبلغ: {price:,} تومان\n"
        f"💳 شماره کارت: 6037-9918-1234-5678\n"
        f"👤 به نام: علی رضایی\n\n"
        f"📩 لطفاً رسید پرداخت رو به صورت عکس بفرست تا بررسی کنیم."
    )
    await update.callback_query.message.reply_text(message)

# ارسال فایل تصادفی از یک دسته
async def send_random_from_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    files = os.listdir(os.path.join(BASE_DIR, category))
    if not files:
        await update.callback_query.message.reply_text("❌ فعلاً فایلی تو این دسته نیست.")
        return

    user_id = update.callback_query.from_user.id

    if category == "free":
        # چک عضویت کانال برای فایل رایگان
        try:
            member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
            if member.status in ['left', 'kicked']:
                raise Exception()
        except:
            await update.callback_query.message.reply_text(
                "❗️برای فایل رایگان باید عضو کانال باشی 👇",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
                    [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
                ])
            )
            return

        selected = random.choice(files)
        file_path = os.path.join(BASE_DIR, category, selected)
        await update.callback_query.message.reply_document(open(file_path, "rb"))

    elif category in ["paid", "vip"]:
        # نمایش راهنمای پرداخت
        await show_payment_info(update, context, category)

# دکمه‌ها
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_waiting_for_price
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data.startswith("save_"):
        await save_file_category(update, context)

    elif data.startswith("get_"):
        category = data.replace("get_", "")
        await send_random_from_category(update, context, category)

    elif data == "about":
        await query.answer()
        await query.message.reply_text("🤖 ربات فروش کانفیگ ساخته شده توسط ممد\n📢 کانال: https://t.me/V2File_Mamad")

    elif data == "set_price" and user_id == ADMIN_ID:
        admin_waiting_for_price = True
        await query.message.reply_text("💬 قیمت رو وارد کن:\nمثال:\n`paid:45000`\nیا\n`vip:90000`", parse_mode='Markdown')

    elif data == "check_membership":
        # بررسی عضویت در کانال برای دکمه "عضو شدم"
        try:
            member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
            if member.status not in ['left', 'kicked']:
                await query.edit_message_text("✅ عضویت شما تایید شد. فایل رایگان ارسال می‌شود.")
                # ارسال فایل رایگان
                files = os.listdir(os.path.join(BASE_DIR, "free"))
                if files:
                    selected = random.choice(files)
                    file_path = os.path.join(BASE_DIR, "free", selected)
                    await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"))
                else:
                    await context.bot.send_message(chat_id=user_id, text="❌ فعلاً فایلی تو دسته رایگان نیست.")
            else:
                await query.answer("❌ شما هنوز عضو کانال نیستید!", show_alert=True)
        except:
            await query.answer("❌ خطا در بررسی عضویت!", show_alert=True)

# پیام متنی (تنظیم قیمت)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_waiting_for_price
    user_id = update.message.from_user.id

    # تنظیم قیمت توسط ادمین
    if admin_waiting_for_price and user_id == ADMIN_ID:
        try:
            key, val = update.message.text.strip().split(":")
            key = key.strip()
            val = int(val.strip())
            if key in ["paid", "vip"]:
                prices[key] = val
                with open(PRICE_FILE, "w") as f:
                    json.dump(prices, f)
                await update.message.reply_text(f"✅ قیمت جدید برای {key.upper()} ثبت شد: {val:,} تومان")
            else:
                await update.message.reply_text("⛔️ دسته نامعتبره.")
        except:
            await update.message.reply_text("❌ فرمت اشتباهه. مثل این بنویس:\n`vip:75000`", parse_mode='Markdown')
        admin_waiting_for_price = False
        return

    # دریافت رسید پرداخت (عکس) برای فایل پولی و VIP
    if update.message.photo:
        # ذخیره رسید پرداخت به همراه آیدی کاربر در متغیر pending_payments
        pending_payments[user_id] = update.message.photo[-1].file_id
        # ارسال رسید به ادمین
        await context.bot.send_photo(chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"💳 رسید پرداخت از کاربر: {user_id}\nلطفاً تایید یا رد کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ تایید", callback_data=f"approve_{user_id}")],
                [InlineKeyboardButton("❌ رد", callback_data=f"reject_{user_id}")]
            ])
        )
        await update.message.reply_text("رسید پرداخت ارسال شد، منتظر تایید ادمین باشید.")
        return

# تایید یا رد پرداخت توسط ادمین
async def handle_approve_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if user_id != ADMIN_ID:
        await query.answer("⛔️ فقط ادمین می‌تواند اقدام کند.", show_alert=True)
        return

    if data.startswith("approve_"):
        buyer_id = int(data.split("_")[1])
        if buyer_id in pending_payments:
            # ارسال فایل پولی یا VIP به کاربر
            # برای سادگی اینجا فرض میکنیم پولی هست، میشه با ساختار بهتر دسته بندی کرد
            files = []
            # چک میکنیم کدام دسته مورد نظر بوده (برای ساده سازی فقط پولی می‌فرستیم)
            files = os.listdir(os.path.join(BASE_DIR, "paid"))
            if not files:
                await query.edit_message_text("❌ فایل پولی موجود نیست.")
                return
            selected = random.choice(files)
            file_path = os.path.join(BASE_DIR, "paid", selected)
            await context.bot.send_document(chat_id=buyer_id, document=open(file_path, "rb"))
            await query.edit_message_text(f"✅ پرداخت تایید شد و فایل برای کاربر {buyer_id} ارسال شد.")
            # حذف رسید پرداخت از لیست
            del pending_payments[buyer_id]
        else:
            await query.edit_message_text("❌ این کاربر رسید پرداخت ارسال نکرده.")
    elif data.startswith("reject_"):
        buyer_id = int(data.split("_")[1])
        if buyer_id in pending_payments:
            await query.edit_message_text(f"❌ پرداخت کاربر {buyer_id} رد شد.")
            del pending_payments[buyer_id]
        else:
            await query.edit_message_text("❌ این کاربر رسید پرداخت ارسال نکرده.")

# دستور ناشناس
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⛔️ دستور ناشناخته!")

# پینگ هر ۵ دقیقه برای جلوگیری از خاموشی
async def ping_loop(application):
    while True:
        try:
            await application.bot.get_me()
            # print("Pinged bot to keep alive")
        except Exception as e:
            print(f"Ping error: {e}")
        await asyncio.sleep(300)  # ۵ دقیقه

# اجرای ربات
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.PHOTO, handle_text))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(CallbackQueryHandler(handle_approve_reject, pattern="^(approve_|reject_).*"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    # شروع همزمان پینگ و ربات
    await asyncio.gather(
        app.run_polling(),
        ping_loop(app)
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
