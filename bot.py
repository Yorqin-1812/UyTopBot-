import logging
import os
import sqlite3

# Railway Variables'dan o'qish (Replit Secrets emas)
from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    constants,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

load_dotenv()

# ==================================================
# CONFIGURATION
# ==================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Railway Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "Karta kiritilmagan") # Agar kiritilmagan bo'lsa, defolt matn

# ADMIN_ID ni int turiga o'tkazish
try:
    ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR else None
except ValueError:
    logger.error("ADMIN_ID Variables'da to'g'ri (raqam) kiritilmagan!")
    ADMIN_ID = None

DB_NAME = "uytop.db"
PRICE = 1000

# --- Keyboards ---
MAIN_BUTTONS = [
    ["🏠 Sotuvdagi uylar"],
    ["🔑 Ijara uchun uylar"],
    ["➕ E'lon joylashtirish"],
]

def main_keyboard():
    return ReplyKeyboardMarkup(MAIN_BUTTONS, resize_keyboard=True, is_persistent=True)

# Admin paneli uchun klaviatura
def get_admin_keyboard():
    keyboard = [
        ["📋 Kutilayotgan e'lonlar"],
        ["📊 Statistika"],
        ["⬅️ Asosiy menyu"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ==================================================
# DATABASE
# ==================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            ad_type TEXT,
            address TEXT,
            house_type TEXT,
            rooms TEXT,
            area TEXT,
            price TEXT,
            description TEXT,
            phone TEXT,
            photo_ids TEXT, 
            status TEXT DEFAULT 'pending', -- pending, approved, rejected
            payment_status TEXT DEFAULT 'pending', -- pending, approved, rejected
            payment_receipt_id TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Ma'lumotlar bazasi initsializatsiya qilindi.")


# ==================================================
# STATES
# ==================================================
(
    AD_TYPE,
    ADDRESS,
    HOUSE_TYPE,
    ROOMS,
    AREA,
    PRICE_STATE,
    DESCRIPTION,
    PHONE,
    PHOTO,
    CONFIRM,
    RECEIPT,
) = range(11)


# ==================================================
# START & MY ID
# ==================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    await update.message.reply_text(
       " Assalomu alaykum! 👋\n\n "
        "🏠 Zarafshon UyTop botiga xush kelibsiz!\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=main_keyboard(),
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    await update.message.reply_text(
        f"Sizning Telegram ID'ingiz:\n\n<code>{update.effective_user.id}</code>",
        parse_mode=constants.ParseMode.HTML
    )


# ==================================================
# ADMIN PANEL (To'liq Bog'langan)
# ==================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda admin huquqi yo‘q.")
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=get_admin_keyboard()
    )

async def admin_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID: return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM ads WHERE status='approved'")
    approved_ads = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ads WHERE status='pending'")
    pending_ads = cursor.fetchone()[0]
    
    conn.close()

    await update.message.reply_text(
        "📊 STATISTIKA\n\n"
        f"✅ Tasdiqlangan e'lonlar: {approved_ads} ta\n"
        f"📋 Kutilayotgan e'lonlar: {pending_ads} ta"
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    await update.message.reply_text(
        "Asosiy menyuga qaytdingiz.",
        reply_markup=main_keyboard()
    )


# ==================================================
# E'LON JOYLASHTIRISH
# ==================================================
async def start_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return ConversationHandler.END

    context.user_data.clear()
    context.user_data["photos"] = []

    keyboard = [["🏠 Sotuv", "🔑 Ijara"], ["❌ Bekor qilish"]]
    await update.message.reply_text(
        "➕ E'lon joylashtirish\n\n"
        "E'lon turini tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
    )
    return AD_TYPE

async def get_ad_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Bekor qilish":
        await update.message.reply_text("❌ E'lon bekor qilindi.", reply_markup=main_keyboard())
        return ConversationHandler.END

    if text in ["🏠 Sotuv", "🔑 Ijara"]:
        context.user_data["ad_type"] = text.replace("🏠 ", "").replace("🔑 ", "")
    else:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.")
        return AD_TYPE

    await update.message.reply_text(
        "📍 Uy manzilini kiriting:\n\nMasalan: Zarafshon shahri, 2-mavze"
    )
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text
    await update.message.reply_text("🏠 Uy turini kiriting:\n\nMasalan: Hovli uy, kvartira, kottej")
    return HOUSE_TYPE

async def get_house_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["house_type"] = update.message.text
    await update.message.reply_text("🛏 Xonalar sonini kiriting:\n\nMasalan: 4 xona")
    return ROOMS

async def get_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rooms"] = update.message.text
    await update.message.reply_text("📐 Uy maydonini kiriting:\n\nMasalan: 120 m²")
    return AREA

async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["area"] = update.message.text
    await update.message.reply_text("💰 Uy narxini kiriting:\n\nMasalan: 350 000 000 so'm")
    return PRICE_STATE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["price"] = update.message.text
    await update.message.reply_text("📝 Uy haqida qisqacha ma'lumot yozing.")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("📞 Telefon raqamingizni kiriting:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    # To'g'ri tugma
    keyboard = [["✅ Tayyor"]]
    await update.message.reply_text(
        "📸 Endi uy rasmlarini yuboring (maksimal 10 ta).\n\n"
        "Rasmlarni yuborib bo‘lgach, ✅ Tayyor deb yozing.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = context.user_data.setdefault("photos", [])

    if update.message.text:
        # Tuzatilgan shart
        if update.message.text == "✅ Tayyor":
            if not photos:
                await update.message.reply_text("❗ Kamida 1 ta rasm yuboring.")
                return PHOTO

            data = context.user_data
            summary = (
                "📋 E'LON MA'LUMOTLARI\n\n"
                f"🏷 Turi: {data['ad_type']}\n"
                f"📍 Manzil: {data['address']}\n"
                f"🏠 Uy turi: {data['house_type']}\n"
                f"🛏 Xonalar: {data['rooms']}\n"
                f"📐 Maydon: {data['area']}\n"
                f"💰 Narx: {data['price']}\n"
                f"📝 Tavsif: {data['description']}\n"
                f"📞 Telefon: {data['phone']}\n"
                f"📸 Rasmlar: {len(photos)} ta\n\n"
                "Ma'lumotlar to‘g‘rimi?"
            )
            keyboard = [
                [InlineKeyboardButton("✅ Ha, davom etish", callback_data="submit_ad")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_ad")],
            ]
            await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard))
            return CONFIRM
        
        # Agar foydalanuvchi "Tayyor" dan boshqa narsa yozsa
        await update.message.reply_text("📸 Rasm yuboring yoki ✅ Tayyor deb yozing.")
        return PHOTO

    if update.message.photo:
        if len(photos) >= 10:
            await update.message.reply_text("⚠️ Maksimal 10 ta rasm.")
            return PHOTO
        photo_id = update.message.photo[-1].file_id
        photos.append(photo_id)
        await update.message.reply_text(f"📸 Rasm qabul qilindi: {len(photos)}/10")

    return PHOTO


# ==================================================
# TO'LOV VA CHEK
# ==================================================
async def confirm_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_ad":
        context.user_data.clear()
        await query.edit_message_text("❌ E'lon joylashtirish bekor qilindi.")
        await context.bot.send_message(chat_id=query.from_user.id, text="Asosiy menyu:", reply_markup=main_keyboard())
        return ConversationHandler.END

    if query.data == "submit_ad":
        await query.edit_message_text(
            "💳 TO'LOV BOSQICHI\n\n"
            f"E'lon joylashtirish narxi: {PRICE:,} so'm.\n\n"
            f"Karta raqami:\n<code>{PAYMENT_CARD}</code>\n\n"
            "To'lovni amalga oshiring va chekni rasm ko'rinishida yuboring.",
            parse_mode=constants.ParseMode.HTML
        )
        return RECEIPT

async def get_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("📸 Iltimos, chekni rasm ko‘rinishida yuboring.")
        return RECEIPT

    receipt_id = update.message.photo[-1].file_id
    data = context.user_data
    photos = data.get("photos", [])
    user = update.effective_user

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ads (
            user_id, username, ad_type, address, house_type, rooms, area, price,
            description, phone, photo_ids, status, payment_status, payment_receipt_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'pending', ?)
    """, (
        user.id, user.username or "", data["ad_type"], data["address"],
        data["house_type"], data["rooms"], data["area"], data["price"],
        data["description"], data["phone"], ",".join(photos), receipt_id
    ))
    ad_id = cursor.lastrowid
    conn.commit()
    conn.close()

    await update.message.reply_text(
        Assalomu alaykum!👋\n\n✅ Chekingiz va e'loningiz qabul qilindi.\n"
        "🔎 Admin to‘lovni va e'lonni tekshirmoqda.",
        reply_markup=main_keyboard(),
    )

    # Adminga xabar
    if ADMIN_ID:
        admin_text = (
            f"💳 YANGI TO'LOV VA E'LON #{ad_id}\n\n"
            f"💰 Summa: {PRICE:,} so'm\n"
            f"🏷 E'lon turi: {data['ad_type']}\n"
            f"📍 Manzil: {data['address']}\n\n"
            f"👤 @{user.username or 'yo‘q'}\n"
            f"🆔 ID: {user.id}"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ TASDIQ", callback_data=f"pay_app_{ad_id}"),
                InlineKeyboardButton("❌ RAD ETISH", callback_data=f"pay_rej_{ad_id}")
            ]
        ]
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=receipt_id,
            caption=admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    context.user_data.clear()
    return ConversationHandler.END


# ==================================================
# ADMIN ACTIONS (To'liq Bog'langan)
# ==================================================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if ADMIN_ID is None or query.from_user.id != ADMIN_ID:
        await query.answer("❌ Sizda admin huquqi yo‘q.", show_alert=True)
        return

    await query.answer()
    data = query.data

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # TO'LOV TASDIQLASH (pay_rej_ emas, pay_app_ bo'lishi kerak)
    if data.startswith("pay_app_"):
        ad_id = int(data.split("_")[-1])
        cursor.execute("UPDATE ads SET payment_status='approved' WHERE id=?", (ad_id,))
        cursor.execute("SELECT id, ad_type, address, price, photo_ids FROM ads WHERE id=?", (ad_id,))
        ad = cursor.fetchone()

        if ad:
            (ad_id, ad_type, address, price, photo_ids) = ad
            await query.edit_message_caption(caption=f"✅ TO'LOV #{ad_id} TASDIQLANDI.\nE'lonni tekshiring.")
            
            photos = photo_ids.split(",")
            review_text = (
                f"🧐 E'LONNI TEKSHIRISH #{ad_id}\n\n"
                f"🏷 Turi: {ad_type}\n"
                f"📍 Manzil: {address}\n"
                f"💰 Narx: {price}\n"
                f"💳 To'lov: ✅ TASDIQLANGAN\n\n"
                "Ushbu e'lonni tasdiqlaysizmi?"
            )
            keyboard = [[
                InlineKeyboardButton("✅ E'LONNI TASDIQLASH", callback_data=f"ad_app_{ad_id}"),
                InlineKeyboardButton("❌ E'LONNI RAD ETISH", callback_data=f"ad_rej_{ad_id}")
            ]]
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=photos[0], caption=review_text, reply_markup=InlineKeyboardMarkup(keyboard))
            
    # TO'LOV RAD ETISH
    elif data.startswith("pay_rej_"):
        ad_id = int(data.split("_")[-1])
        cursor.execute("SELECT user_id FROM ads WHERE id=?", (ad_id,))
        res = cursor.fetchone()
        cursor.execute("UPDATE ads SET payment_status='rejected', status='rejected' WHERE id=?", (ad_id,))
        
        await query.edit_message_caption(caption=f"❌ TO'LOV #{ad_id} RAD ETILDI.")
        if res:
            await context.bot.send_message(chat_id=res[0], text=f"❌ E'lon #{ad_id} uchun to'lov chekingiz rad etildi.")

    # E'LONNI YAKUNIY TASDIQLASH (Botga chiqarish)
    elif data.startswith("ad_app_"):
        ad_id = int(data.split("_")[-1])
        cursor.execute("UPDATE ads SET status='approved' WHERE id=?", (ad_id,))
        cursor.execute("SELECT user_id FROM ads WHERE id=?", (ad_id,))
        res = cursor.fetchone()
        
        await query.edit_message_caption(caption=f"✅ E'LON #{ad_id} TASDIQLANDI. Botga joylandi.")
        if res:
            await context.bot.send_message(
                chat_id=res[0],
                text=f"🎉 Tabriklaymiz! E'loningiz #{ad_id} tasdiqlandi va botga joylashtirildi."
            )

    # E'LONNI RAD ETISH
    elif data.startswith("ad_rej_"):
        ad_id = int(data.split("_")[-1])
        cursor.execute("SELECT user_id FROM ads WHERE id=?", (ad_id,))
        res = cursor.fetchone()
        cursor.execute("UPDATE ads SET status='rejected' WHERE id=?", (ad_id,))
        
        await query.edit_message_caption(caption=f"❌ E'LON #{ad_id} RAD ETILDI.")
        if res:
            await context.bot.send_message(chat_id=res[0], text=f"❌ E'loningiz #{ad_id} rad etildi.")

    conn.commit()
    conn.close()


# ==================================================
# E'LONLARNI KO'RSATISH
# ==================================================
async def show_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    text = update.message.text
    
    if text == "🏠 Sotuvdagi uylar":
        ad_type = "Sotuv"; title = "🏠 SOTUVDAGI UYLAR"
    elif text == "🔑 Ijara uchun uylar":
        ad_type = "Ijara"; title = "🔑 IJARA UCHUN UYLAR"
    else: return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, address, house_type, rooms, area, price, description, phone, photo_ids
        FROM ads WHERE ad_type=? AND status='approved' ORDER BY id DESC
    """, (ad_type,))
    ads = cursor.fetchall()
    conn.close()

    if not ads:
        await update.message.reply_text(f"{title}\n\nHozircha tasdiqlangan e'lonlar yo‘q.", reply_markup=main_keyboard())
        return

    await update.message.reply_text(f"{title}\n\nJami: {len(ads)} ta e'lon.", reply_markup=main_keyboard())

    for ad in ads:
        (ad_id, address, house_type, rooms, area, price, description, phone, photo_ids) = ad
        photos = photo_ids.split(",")
        caption = (
            f"🏠 E'lon #{ad_id}\n\n📍 Manzil: {address}\n"
            f"🏠 {house_type} | 🛏 {rooms} | 📐 {area}\n💰 Narx: {price}\n\n📝 {description}\n\n📞 Aloqa: {phone}"
        )
        await update.message.reply_photo(photo=photos[0], caption=caption)


# ==================================================
# CANCEL & ERROR
# ==================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ E'lon joylashtirish bekor qilindi.", reply_markup=main_keyboard())
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception handling update:", exc_info=context.error)


# ==================================================
# MAIN
# ==================================================
def main() -> None:
    init_db()
    
    if not BOT_TOKEN:
        print("XATO: Variables'da BOT_TOKEN kiritilmagan!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # E'lon joylashtirish conversation handler'i
    ad_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ E'lon joylashtirish$"), start_ad)],
        states={
            AD_TYPE: [MessageHandler(filters.TEXT & ~filters.Regex(r"^❌Bekor qilish$"), get_ad_type)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.Regex(r"^❌Bekor qilish$"), get_address)],
            HOUSE_TYPE: [MessageHandler(filters.TEXT & ~filters.Regex(r"^❌Bekor qilish$"), get_house_type)],
            ROOMS: [MessageHandler(filters.TEXT & ~filters.Regex(r"^❌Bekor qilish$"), get_rooms)],
            AREA: [MessageHandler(filters.TEXT & ~filters.Regex(r"^❌Bekor qilish$"), get_area)],
            PRICE_STATE: [MessageHandler(filters.TEXT & ~filters.Regex(r"^❌Bekor qilish$"), get_price)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.Regex(r"^❌Bekor qilish$"), get_description)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.Regex(r"^❌Bekor qilish$"), get_phone)],
            PHOTO: [
                MessageHandler(filters.Photo | filters.Regex(r"^✅ Tayyor$"), get_photo),
            ],
     CONFIRM: [CallbackQueryHandler(confirm_ad, pattern="^(submit_ad|cancel_ad)$")],
            RECEIPT: [MessageHandler(filters.Photo, get_receipt)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex(r"^❌Bekor qilish$"), cancel)],
        persistent=False
    )

    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myid", myid))
    
    # Admin handlerlari (to'liq bog'langan)
    application.add_handler(MessageHandler(filters.Text("🔐 Admin Panel"), admin_panel))
    application.add_handler(MessageHandler(filters.Text("📊 Statistika"), admin_statistics))
    application.add_handler(MessageHandler(filters.Text("⬅️ Asosiy menyu"), back_to_main))
    # patternlar to'g'rilandi
    application.add_handler(CallbackQueryHandler(admin_action, pattern="^(pay_|ad_)"))

    # E'lonlar conversation
    application.add_handler(ad_conv_handler)
    
    # Bekor qilish (konversationdan tashqarida)
    application.add_handler(MessageHandler(filters.Regex(r"^❌Bekor qilish$"), cancel))

    # E'lonlarni ko'rsatish
    application.add_handler(MessageHandler(filters.Regex(r"^(🏠 Sotuvdagi uylar|🔑 Ijara uchun uylar)$"), show_ads))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    print("Zarafshon UyTop bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
