import logging
import os
import sqlite3

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
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

# ==================================================
# CONFIGURATION
# ==================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "Karta kiritilmagan")

try:
    ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR else None
except ValueError:
    logger.error("ADMIN_ID noto'g'ri kiritilgan!")
    ADMIN_ID = None

DB_NAME = "uytop.db"
PRICE = 5000


# ==================================================
# KEYBOARDS
# ==================================================

MAIN_BUTTONS = [
    ["🏠 Sotuvdagi uylar"],
    ["🔑 Ijara uchun uylar"],
    ["➕ E'lon joylashtirish"],
    ["🔐 Admin Panel"],
]


def main_keyboard():
    return ReplyKeyboardMarkup(
        MAIN_BUTTONS,
        resize_keyboard=True,
        is_persistent=True,
    )


def get_admin_keyboard():
    keyboard = [
        ["📋 Kutilayotgan e'lonlar"],
        ["📋 Tasdiqlangan e'lonlar"],
        ["📊 Statistika"],
        ["⬅️ Asosiy menyu"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


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
            status TEXT DEFAULT 'pending',
            payment_status TEXT DEFAULT 'pending',
            payment_receipt_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delete_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_id INTEGER,
            user_id INTEGER,
            username TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

    logger.info("Database tayyor.")


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
# START
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "🏠 UyTop botiga xush kelibsiz!\n\n"
        "Quyidagi menyudan kerakli bo‘limni tanlang.",
        reply_markup=main_keyboard(),
    )


# ==================================================
# MY ID
# ==================================================

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    await update.message.reply_text(
        f"Sizning Telegram ID'ingiz:\n\n"
        f"<code>{update.effective_user.id}</code>",
        parse_mode=constants.ParseMode.HTML,
    )


# ==================================================
# ADMIN PANEL
# ==================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if ADMIN_ID is None:
        await update.message.reply_text(
            "❌ ADMIN_ID Railway Variables'da kiritilmagan."
        )
        return

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Sizda admin huquqi yo‘q."
        )
        return

    await update.message.reply_text(
        "🔐 ADMIN PANEL\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=get_admin_keyboard(),
    )


# ==================================================
# ADMIN STATISTICS
# ==================================================

async def admin_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Sizda admin huquqi yo‘q."
        )
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM ads WHERE status='approved'"
    )
    approved_ads = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM ads WHERE status='pending'"
    )
    pending_ads = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM ads"
    )
    total_ads = cursor.fetchone()[0]

    conn.close()

    await update.message.reply_text(
        "📊 STATISTIKA\n\n"
        f"📦 Jami e'lonlar: {total_ads} ta\n"
        f"✅ Tasdiqlangan: {approved_ads} ta\n"
        f"⏳ Kutilayotgan: {pending_ads} ta"
    )


# ==================================================
# PENDING ADS
# ==================================================

async def pending_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Sizda admin huquqi yo‘q."
        )
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, ad_type, address, price, payment_status
        FROM ads
        WHERE status='pending'
        ORDER BY id DESC
    """)

    ads = cursor.fetchall()
    conn.close()

    if not ads:
        await update.message.reply_text(
            "📋 Hozircha kutilayotgan e'lonlar yo‘q."
        )
        return

    text = "📋 KUTILAYOTGAN E'LONLAR\n\n"

    for ad in ads:
        ad_id, ad_type, address, price, payment_status = ad

        text += (
            f"🆔 #{ad_id}\n"
            f"🏷 Turi: {ad_type}\n"
            f"📍 Manzil: {address}\n"
            f"💰 Narx: {price}\n"
            f"💳 To‘lov: {payment_status}\n\n"
        )

    await update.message.reply_text(text)


async def approved_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if ADMIN_ID is None or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Sizda admin huquqi yo‘q."
        )
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            ad_type,
            address,
            house_type,
            rooms,
            price,
            description,
            phone,
            photo_ids
        FROM ads
        WHERE status='approved'
        ORDER BY id DESC
    """)

    ads = cursor.fetchall()
    conn.close()

    if not ads:
        await update.message.reply_text(
            "📋 Hozircha tasdiqlangan e'lonlar yo‘q."
        )
        return

    await update.message.reply_text(
        f"📋 TASDIQLANGAN E'LONLAR\n\n"
        f"Jami: {len(ads)} ta"
    )

    for ad in ads:

        (
            ad_id,
            ad_type,
            address,
            house_type,
            rooms,
            price,
            description,
            phone,
            photo_ids,
        ) = ad

        caption = (
            f"🏠 E'lon #{ad_id}\n\n"
            f"🏷 Turi: {ad_type}\n"
            f"📍 Manzil: {address}\n"
            f"🏠 Uy turi: {house_type}\n"
            f"🛏 Xonalar: {rooms}\n"
            f"💰 Narx: {price}\n"
            f"📝 {description}\n"
            f"📞 Telefon: {phone}"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🗑 O‘CHIRISH",
                    callback_data=f"delete_confirm_{ad_id}"
                )
            ]
        ]

        photos = [p for p in photo_ids.split(",") if p]

        if len(photos) == 1:

            await update.message.reply_photo(
                photo=photos[0],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        elif len(photos) > 1:

            media = []

            for i, photo_id in enumerate(photos):

                if i == 0:

                    media.append(
                        InputMediaPhoto(
                            media=photo_id,
                            caption=caption,
                        )
                    )

                else:

                    media.append(
                        InputMediaPhoto(
                            media=photo_id
                        )
                    )

            await update.message.reply_media_group(
                media=media
            )

            await update.message.reply_text(
                f"🆔 E'lon #{ad_id} uchun admin amali:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

# ==================================================
# DELETE APPROVED AD
# ==================================================

async def delete_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if not query:
        return

    if ADMIN_ID is None or query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Sizda admin huquqi yo‘q.",
            show_alert=True
        )
        return

    await query.answer()

    try:
        ad_id = int(
            query.data.replace("delete_yes_", "")
        )
    except ValueError:
        await query.answer(
            "❌ E'lon ID noto‘g‘ri.",
            show_alert=True
        )
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM ads WHERE id = ?",
        (ad_id,)
    )

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    if deleted:
        await query.edit_message_caption(
            caption="🗑 E'lon muvaffaqiyatli o‘chirildi."
        )
    else:
        await query.edit_message_caption(
            caption="❌ E'lon topilmadi."
        )


# ==================================================
# CANCEL DELETE
# ==================================================

async def delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    ad_id = query.data.replace(
        "delete_no_",
        ""
    )

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🗑 O‘CHIRISH",
                    callback_data=f"delete_confirm_{ad_id}"
                )
            ]
        ])
    )


# ==================================================
# BACK TO MAIN
# ==================================================
# ==================================================
# BACK TO MAIN
# ==================================================

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    await update.message.reply_text(
        "Asosiy menyuga qaytdingiz.",
        reply_markup=main_keyboard(),
    )


# ==================================================
# START AD
# ==================================================

async def start_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["photos"] = []

    keyboard = [
        ["🏠 Sotuv", "🔑 Ijara"],
        ["❌ Bekor qilish"],
    ]

    await update.message.reply_text(
        "➕ E'lon joylashtirish\n\n"
        "E'lon turini tanlang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )

    return AD_TYPE


# ==================================================
# AD TYPE
# ==================================================

async def get_ad_type(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return AD_TYPE

    text = update.message.text

    if text == "❌ Bekor qilish":
        await update.message.reply_text(
            "❌ E'lon bekor qilindi.",
            reply_markup=main_keyboard(),
        )
        return ConversationHandler.END

    if text == "🏠 Sotuv":
        context.user_data["ad_type"] = "Sotuv"

    elif text == "🔑 Ijara":
        context.user_data["ad_type"] = "Ijara"

    else:
        await update.message.reply_text(
            "Iltimos, tugmalardan birini tanlang."
        )
        return AD_TYPE

    await update.message.reply_text(
        "📍 Uy manzilini kiriting:\n\n"
        "Masalan: Zarafshon shahri, 2-mavze"
    )

    return ADDRESS


# ==================================================
# ADDRESS
# ==================================================

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return ADDRESS

    context.user_data["address"] = update.message.text

    await update.message.reply_text(
        "🏠 Uy turini kiriting:\n\n"
        "Masalan: Hovli uy, kvartira, kottej"
    )

    return HOUSE_TYPE


# ==================================================
# HOUSE TYPE
# ==================================================

async def get_house_type(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return HOUSE_TYPE

    context.user_data["house_type"] = update.message.text

    await update.message.reply_text(
        "🛏 Xonalar sonini kiriting:\n\n"
        "Masalan: 4 xona"
    )

    return ROOMS


# ==================================================
# ROOMS
# ==================================================

async def get_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return ROOMS

    context.user_data["rooms"] = update.message.text

    await update.message.reply_text(
        "💰 Uy narxini kiriting:\n\n"
        "Masalan: 350 000 000 so'm"
    )

    return PRICE_STATE


# ==================================================
# PRICE
# ==================================================

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return PRICE_STATE

    context.user_data["price"] = update.message.text

    await update.message.reply_text(
        "📝 Uy haqida qisqacha ma'lumot yozing."
    )

    return DESCRIPTION


# ==================================================
# DESCRIPTION
# ==================================================

async def get_description(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return DESCRIPTION

    context.user_data["description"] = update.message.text

    await update.message.reply_text(
        "📞 Telefon raqamingizni kiriting:"
    )

    return PHONE


# ==================================================
# PHONE
# ==================================================

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return PHONE

    context.user_data["phone"] = update.message.text

    keyboard = [
        ["✅ Tayyor"],
        ["❌ Bekor qilish"],
    ]

    await update.message.reply_text(
        "📸 Endi uy rasmlarini yuboring "
        "(maksimal 10 ta).\n\n"
        "Rasmlarni yuborib bo‘lgach, "
        "✅ Tayyor tugmasini bosing.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )

    return PHOTO


# ==================================================
# PHOTO
# ==================================================

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return PHOTO

    photos = context.user_data.setdefault("photos", [])

    # Bekor qilish
    if update.message.text == "❌ Bekor qilish":

        context.user_data.clear()

        await update.message.reply_text(
            "❌ E'lon bekor qilindi.",
            reply_markup=main_keyboard(),
        )

        return ConversationHandler.END

    # Tayyor
    if update.message.text == "✅ Tayyor":

        if not photos:
            await update.message.reply_text(
                "❗ Kamida 1 ta rasm yuboring."
            )
            return PHOTO

        data = context.user_data

        summary = (
            "📋 E'LON MA'LUMOTLARI\n\n"
            f"🏷 Turi: {data['ad_type']}\n"
            f"📍 Manzil: {data['address']}\n"
            f"🏠 Uy turi: {data['house_type']}\n"
            f"🛏 Xonalar: {data['rooms']}\n"
            f"💰 Narx: {data['price']}\n"
            f"📝 Tavsif: {data['description']}\n"
            f"📞 Telefon: {data['phone']}\n"
            f"📸 Rasmlar: {len(photos)} ta\n\n"
            "Ma'lumotlar to‘g‘rimi?"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Ha, davom etish",
                    callback_data="submit_ad",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Bekor qilish",
                    callback_data="cancel_ad",
                )
            ],
        ]

        await update.message.reply_text(
            summary,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return CONFIRM

    # Foto
    if update.message.photo:

        if len(photos) >= 10:
            await update.message.reply_text(
                "⚠️ Maksimal 10 ta rasm yuborish mumkin."
            )
            return PHOTO

        photo_id = update.message.photo[-1].file_id
        photos.append(photo_id)

        await update.message.reply_text(
            f"📸 Rasm qabul qilindi: {len(photos)}/10"
        )

        return PHOTO

    await update.message.reply_text(
        "📸 Rasm yuboring yoki ✅ Tayyor tugmasini bosing."
    )

    return PHOTO

# ==================================================
# CONFIRM AD
# ==================================================

async def confirm_ad(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return ConversationHandler.END

    await query.answer()

    # BEKOR QILISH
    if query.data == "cancel_ad":

        context.user_data.clear()

        await query.edit_message_text(
            "❌ E'lon joylashtirish bekor qilindi."
        )

        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Asosiy menyu:",
            reply_markup=main_keyboard(),
        )

        return ConversationHandler.END

    # DAVOM ETISH
    if query.data == "submit_ad":

        await query.edit_message_text(
            "💳 TO'LOV BOSQICHI\n\n"
            f"E'lon joylashtirish narxi: {PRICE:,} so'm.\n\n"
            f"Karta raqami:\n"
            f"<code>{PAYMENT_CARD}</code>\n\n"
            "To'lovni amalga oshiring va "
            "chekni rasm ko'rinishida yuboring.",
            parse_mode=constants.ParseMode.HTML,
        )

        # Eski klaviaturani olib tashlash
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="📸 To‘lov chekini rasm ko‘rinishida yuboring.",
            reply_markup=ReplyKeyboardRemove(),
        )

        return RECEIPT

    return CONFIRM
# ==================================================
# RECEIPT
# ==================================================
async def get_receipt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return RECEIPT

    # Chek rasm ekanligini tekshirish
    if not update.message.photo:

        await update.message.reply_text(
            "📸 Iltimos, chekni rasm ko‘rinishida yuboring."
        )

        return RECEIPT

    receipt_id = update.message.photo[-1].file_id

    data = context.user_data
    photos = data.get("photos", [])

    # E'lon rasmlari yo'q bo'lsa
    if not photos:

        await update.message.reply_text(
            "❌ E'lon rasmlari topilmadi.\n\n"
            "Iltimos, e'lonni qaytadan joylashtiring.",
            reply_markup=main_keyboard(),
        )

        context.user_data.clear()

        return ConversationHandler.END

    user = update.effective_user

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO ads (
            user_id,
            username,
            ad_type,
            address,
            house_type,
            rooms,
            price,
            description,
            phone,
            photo_ids,
            status,
            payment_status,
            payment_receipt_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user.id,
            user.username or "",
            data["ad_type"],
            data["address"],
            data["house_type"],
            data["rooms"],
            data["price"],
            data["description"],
            data["phone"],
            ",".join(photos),
            "pending",
            "pending",
            receipt_id,
        ),
    )

    ad_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Foydalanuvchiga xabar
    await update.message.reply_text(
        "✅ E'loningiz tasdiqlash uchun yuborildi.\n\n"
        "⏳ Admin to‘lovni va e'lonni tekshiradi.\n"
        "📌 E'lon tasdiqlangandan so‘ng botda ko‘rinadi "
        "va sizga xabar beramiz.",
        reply_markup=main_keyboard(),
    )

    # ADMINGA YUBORISH
    if ADMIN_ID:

        admin_text = (
            f"💳 YANGI TO'LOV VA E'LON #{ad_id}\n\n"
            f"💰 Summa: {PRICE:,} so'm\n"
            f"🏷 E'lon turi: {data['ad_type']}\n"
            f"📍 Manzil: {data['address']}\n"
            f"🏠 Uy turi: {data['house_type']}\n"
            f"🛏 Xonalar: {data['rooms']}\n"
            f"💰 Narx: {data['price']}\n\n"
            f"👤 @{user.username or 'yo‘q'}\n"
            f"🆔 ID: {user.id}"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ TO'LOV TASDIQ",
                    callback_data=f"pay_app_{ad_id}",
                ),
                InlineKeyboardButton(
                    "❌ TO'LOV RAD",
                    callback_data=f"pay_rej_{ad_id}",
                ),
            ]
        ]

        try:

            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=receipt_id,
                caption=admin_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        except Exception:

            logger.exception(
                "Adminga xabar yuborishda xato."
            )

    context.user_data.clear()

    return ConversationHandler.END
    
# ==================================================
# ADMIN ACTIONS
# ==================================================

async def delete_ad_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    if ADMIN_ID is None or query.from_user.id != ADMIN_ID:

        await query.answer(
            "❌ Sizda admin huquqi yo‘q.",
            show_alert=True,
        )

        return

    await query.answer()

    ad_id = int(query.data.split("_")[-1])

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ HA, O‘CHIRISH",
                callback_data=f"delete_yes_{ad_id}",
            ),
            InlineKeyboardButton(
                "❌ BEKOR QILISH",
                callback_data=f"delete_no_{ad_id}",
            ),
        ]
    ]

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
async def admin_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    if ADMIN_ID is None or query.from_user.id != ADMIN_ID:

        await query.answer(
            "❌ Sizda admin huquqi yo‘q.",
            show_alert=True,
        )

        return

    await query.answer()

    data = query.data

    # ==================================================
    # E'LONNI O'CHIRISH
    # ==================================================

    if data.startswith("delete_yes_"):

        ad_id = int(data.split("_")[-1])

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id FROM ads WHERE id=?",
            (ad_id,)
        )

        result = cursor.fetchone()

        cursor.execute(
            "DELETE FROM ads WHERE id=?",
            (ad_id,)
        )

        conn.commit()
        conn.close()

        try:
            await query.edit_message_caption(
                caption=f"🗑 E'LON #{ad_id} O‘CHIRILDI."
            )
        except Exception:
            pass

        if result:

            try:
                await context.bot.send_message(
                    chat_id=result[0],
                    text=(
                        f"⚠️ E'loningiz #{ad_id} "
                        "admin tomonidan o‘chirildi."
                    ),
                )
            except Exception:
                pass

        return

    # ==================================================
    # O'CHIRISHNI BEKOR QILISH
    # ==================================================

    if data.startswith("delete_no_"):

        ad_id = int(data.split("_")[-1])

        keyboard = [
            [
                InlineKeyboardButton(
                    "🗑 O‘CHIRISH",
                    callback_data=f"delete_confirm_{ad_id}",
                )
            ]
        ]

        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # ==================================================
    # DATABASE
    # ==================================================

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ==================================================
    # PAYMENT APPROVED
    # ==================================================

    if data.startswith("pay_app_"):

        ad_id = int(data.split("_")[-1])

        cursor.execute(
            """
            UPDATE ads
            SET payment_status='approved'
            WHERE id=?
            """,
            (ad_id,),
        )

        cursor.execute(
            """
            SELECT
                ad_type,
                address,
                house_type,
                rooms,
                price,
                description,
                phone,
                photo_ids
            FROM ads
            WHERE id=?
            """,
            (ad_id,),
        )

        ad = cursor.fetchone()

        if not ad:

            conn.commit()
            conn.close()

            await query.answer(
                "❌ E'lon topilmadi.",
                show_alert=True,
            )

            return

        (
            ad_type,
            address,
            house_type,
            rooms,
            price,
            description,
            phone,
            photo_ids,
        ) = ad

        try:
            await query.edit_message_caption(
                caption=(
                    f"✅ TO'LOV #{ad_id} TASDIQLANDI.\n\n"
                    "Endi e'lonni tekshiring."
                )
            )
        except Exception:
            pass

        review_text = (
            f"🧐 E'LONNI TEKSHIRISH #{ad_id}\n\n"
            f"🏷 Turi: {ad_type}\n"
            f"📍 Manzil: {address}\n"
            f"🏠 Uy turi: {house_type}\n"
            f"🛏 Xonalar: {rooms}\n"
            f"💰 Narx: {price}\n"
            f"📝 Tavsif: {description}\n"
            f"📞 Telefon: {phone}\n\n"
            "💳 To'lov: ✅ TASDIQLANGAN\n\n"
            "Ushbu e'lonni tasdiqlaysizmi?"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ E'LONNI TASDIQLASH",
                    callback_data=f"ad_app_{ad_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ E'LONNI RAD ETISH",
                    callback_data=f"ad_rej_{ad_id}",
                )
            ],
        ]

        photos = [p for p in photo_ids.split(",") if p]

        # Bitta rasm
        if len(photos) == 1:

            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photos[0],
                caption=review_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        # Bir nechta rasm
        elif len(photos) > 1:

            media = []

            for i, photo_id in enumerate(photos):

                if i == 0:

                    media.append(
                        InputMediaPhoto(
                            media=photo_id,
                            caption=review_text,
                        )
                    )

                else:

                    media.append(
                        InputMediaPhoto(
                            media=photo_id
                        )
                    )

            await context.bot.send_media_group(
                chat_id=ADMIN_ID,
                media=media,
            )

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"🧐 E'lon #{ad_id} uchun "
                    "amalni tanlang:"
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    # ==================================================
    # PAYMENT REJECTED
    # ==================================================

    elif data.startswith("pay_rej_"):

        ad_id = int(data.split("_")[-1])

        cursor.execute(
            "SELECT user_id FROM ads WHERE id=?",
            (ad_id,),
        )

        res = cursor.fetchone()

        cursor.execute(
            """
            UPDATE ads
            SET
                payment_status='rejected',
                status='rejected'
            WHERE id=?
            """,
            (ad_id,),
        )

        try:
            await query.edit_message_caption(
                caption=f"❌ TO'LOV #{ad_id} RAD ETILDI."
            )
        except Exception:
            pass

        if res:

            await context.bot.send_message(
                chat_id=res[0],
                text=(
                    f"❌ E'lon #{ad_id} uchun "
                    "to‘lov chekingiz rad etildi."
                ),
            )

    # ==================================================
    # AD APPROVED
    # ==================================================

    elif data.startswith("ad_app_"):

        ad_id = int(data.split("_")[-1])

        cursor.execute(
            """
            UPDATE ads
            SET status='approved'
            WHERE id=?
            """,
            (ad_id,),
        )

        cursor.execute(
            """
            SELECT user_id
            FROM ads
            WHERE id=?
            """,
            (ad_id,),
        )

        res = cursor.fetchone()

        try:
            await query.edit_message_caption(
                caption=(
                    f"✅ E'LON #{ad_id} TASDIQLANDI.\n\n"
                    "Botga joylandi."
                )
            )
        except Exception:
            pass

        if res:

            await context.bot.send_message(
                chat_id=res[0],
                text=(
                    f"🎉 Tabriklaymiz!\n\n"
                    f"E'loningiz #{ad_id} tasdiqlandi "
                    "va botga joylashtirildi."
                ),
            )

    # ==================================================
    # AD REJECTED
    # ==================================================

    elif data.startswith("ad_rej_"):

        ad_id = int(data.split("_")[-1])

        cursor.execute(
            """
            SELECT user_id
            FROM ads
            WHERE id=?
            """,
            (ad_id,),
        )

        res = cursor.fetchone()

        cursor.execute(
            """
            UPDATE ads
            SET status='rejected'
            WHERE id=?
            """,
            (ad_id,),
        )

        try:
            await query.edit_message_caption(
                caption=f"❌ E'LON #{ad_id} RAD ETILDI."
            )
        except Exception:
            pass

        if res:

            await context.bot.send_message(
                chat_id=res[0],
                text=(
                    f"❌ E'loningiz #{ad_id} rad etildi."
                ),
            )

    # ==================================================
    # SAVE
    # ==================================================

    conn.commit()
    conn.close()


# ==================================================
# SHOW ONE AD
# ==================================================

# ==================================================
# SEND AD CARD
# ==================================================

async def send_ad_card(
    chat_id,
    ad,
    context,
    show_previous=True,
    show_next=True
):

    (
        ad_id,
        address,
        house_type,
        rooms,
        price,
        description,
        phone,
        photo_ids,
    ) = ad

    photos = [p for p in photo_ids.split(",") if p]

    caption = (
        f"🏠 E'lon #{ad_id}\n\n"
        f"📍 Manzil: {address}\n"
        f"🏠 Uy turi: {house_type}\n"
        f"🛏 Xonalar: {rooms}\n"
        f"💰 Narx: {price}\n\n"
        f"📝 {description}\n\n"
        f"📞 Aloqa: {phone}"
    )

    # ==================================================
    # NAVIGATION BUTTONS
    # ==================================================

    buttons = []

    navigation = []

    if show_previous:
        navigation.append(
            InlineKeyboardButton(
                "⬅️ OLDINGI",
                callback_data=f"prev_ad_{ad_id}"
            )
        )

    if show_next:
        navigation.append(
            InlineKeyboardButton(
                "➡️ KEYINGI",
                callback_data=f"next_ad_{ad_id}"
            )
        )

    if navigation:
        buttons.append(navigation)

    reply_markup = (
        InlineKeyboardMarkup(buttons)
        if buttons
        else None
    )

    sent_message_ids = []

    # ==================================================
    # BITTA RASM
    # ==================================================

    if len(photos) == 1:

        message = await context.bot.send_photo(
            chat_id=chat_id,
            photo=photos[0],
            caption=caption,
            reply_markup=reply_markup,
        )

        sent_message_ids.append(message.message_id)

    # ==================================================
    # KO‘P RASM
    # ==================================================

    elif len(photos) > 1:

        media = []

        for i, photo_id in enumerate(photos):

            if i == 0:

                media.append(
                    InputMediaPhoto(
                        media=photo_id,
                        caption=caption,
                    )
                )

            else:

                media.append(
                    InputMediaPhoto(
                        media=photo_id
                    )
                )

        messages = await context.bot.send_media_group(
            chat_id=chat_id,
            media=media,
        )

        for message in messages:
            sent_message_ids.append(message.message_id)

        # Albomga tugma qo‘yib bo‘lmagani uchun
        # navigatsiya tugmasini alohida xabarda yuboramiz

        if reply_markup:

            button_message = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🏠 E'lon #{ad_id}",
                reply_markup=reply_markup,
            )

            sent_message_ids.append(button_message.message_id)

    # ==================================================
    # RASM BO‘LMASA
    # ==================================================

    else:

        message = await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=reply_markup,
        )

        sent_message_ids.append(message.message_id)

    return sent_message_ids


# ==================================================
# SHOW ADS
# ==================================================

async def show_ads(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    text = update.message.text

    if text == "🏠 Sotuvdagi uylar":

        ad_type = "Sotuv"
        title = "🏠 SOTUVDAGI UYLAR"

    elif text == "🔑 Ijara uchun uylar":

        ad_type = "Ijara"
        title = "🔑 IJARA UCHUN UYLAR"

    else:
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            address,
            house_type,
            rooms,
            price,
            description,
            phone,
            photo_ids
        FROM ads
        WHERE ad_type=?
        AND status='approved'
        ORDER BY id DESC
        """,
        (ad_type,),
    )

    ads = cursor.fetchall()

    conn.close()

    if not ads:

        await update.message.reply_text(
            f"{title}\n\n"
            "Hozircha tasdiqlangan e'lonlar yo‘q.",
            reply_markup=main_keyboard(),
        )

        return

    # E'lonlar ro‘yxatini saqlaymiz
    context.user_data["ad_list"] = ads
    context.user_data["ad_type"] = ad_type
    context.user_data["ad_index"] = 0

    await update.message.reply_text(
        f"{title}\n\n"
        f"Jami: {len(ads)} ta e'lon."
    )

    # Faqat BIRINCHI e'lonni chiqaramiz
    message_ids = await send_ad_card(
        chat_id=update.effective_chat.id,
        ad=ads[0],
        context=context,
        show_next=len(ads) > 1,
    )

    context.user_data["current_ad_message_ids"] = message_ids


# ==================================================
# NEXT AD
# ==================================================

async def next_ad(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    ads = context.user_data.get("ad_list", [])

    if not ads:
        await query.answer(
            "❌ E'lonlar ro‘yxati topilmadi. Qaytadan bo‘limni tanlang.",
            show_alert=True,
        )
        return

    current_index = context.user_data.get(
        "ad_index",
        0
    )

    next_index = current_index + 1

    # Oxirgi e'lon
    if next_index >= len(ads):

        await query.answer(
            "📌 Bu oxirgi e'lon.",
            show_alert=True,
        )

        return

    # Eski e'lon rasmlari va tugmasini o‘chirish
    old_message_ids = context.user_data.get(
        "current_ad_message_ids",
        []
    )

    for message_id in old_message_ids:

        try:

            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=message_id,
            )

        except Exception:
            pass

    # Yangi indeks
    context.user_data["ad_index"] = next_index

    next_ad_data = ads[next_index]

    # Keyingi e'lonni yuborish
    message_ids = await send_ad_card(
        chat_id=query.message.chat_id,
        ad=next_ad_data,
        context=context,
        show_next=next_index < len(ads) - 1,
    )

    context.user_data["current_ad_message_ids"] = message_ids

# ==================================================
# CANCEL
# ==================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    if update.message:

        await update.message.reply_text(
            "❌ E'lon joylashtirish bekor qilindi.",
            reply_markup=main_keyboard(),
        )

    return ConversationHandler.END


# ==================================================
# ERROR HANDLER
# ==================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Botda xatolik:",
        exc_info=context.error,
    )


# ==================================================
# MAIN
# ==================================================

def main():

    init_db()

    if not BOT_TOKEN:

        print(
            "XATO: Railway Variables'da "
            "BOT_TOKEN kiritilmagan!"
        )

        return

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ==================================================
    # CONVERSATION HANDLER
    # ==================================================

    ad_conv_handler = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"^➕ E'lon joylashtirish$"
                ),
                start_ad,
            )
        ],

        states={

            AD_TYPE: [
                MessageHandler(
                    filters.TEXT,
                    get_ad_type,
                )
            ],

            ADDRESS: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex(r"^❌ Bekor qilish$"),
                    get_address,
                )
            ],

            HOUSE_TYPE: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex(r"^❌ Bekor qilish$"),
                    get_house_type,
                )
            ],

            ROOMS: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex(r"^❌ Bekor qilish$"),
                    get_rooms,
                )
            ],

            PRICE_STATE: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex(r"^❌ Bekor qilish$"),
                    get_price,
                )
            ],

            DESCRIPTION: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex(r"^❌ Bekor qilish$"),
                    get_description,
                )
            ],

            PHONE: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex(r"^❌ Bekor qilish$"),
                    get_phone,
                )
            ],

            PHOTO: [
                MessageHandler(
                    filters.PHOTO | filters.Regex(
                        r"^(✅ Tayyor|❌ Bekor qilish)$"
                    ),
                    get_photo,
                )
            ],

            CONFIRM: [
                CallbackQueryHandler(
                    confirm_ad,
                    pattern=r"^(submit_ad|cancel_ad)$",
                )
            ],

            RECEIPT: [
                MessageHandler(
                    filters.PHOTO,
                    get_receipt,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            ),
            MessageHandler(
                filters.Regex(
                    r"^❌ Bekor qilish$"
                ),
                cancel,
            ),
        ],

        persistent=False,
    )

    # ==================================================
    # BASIC COMMANDS
    # ==================================================

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("myid", myid)
    )

    application.add_handler(
        CommandHandler("admin", admin_panel)
    )

    # ==================================================
    # CONVERSATION
    # ==================================================

    application.add_handler(
        ad_conv_handler
    )

    # ==================================================
    # DELETE AD CALLBACKS
    # ==================================================

    application.add_handler(
        CallbackQueryHandler(
            delete_ad_confirm,
            pattern=r"^delete_confirm_\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            delete_ad,
            pattern=r"^delete_yes_\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            delete_cancel,
            pattern=r"^delete_no_\d+$"
        )
    )

    # ==================================================
    # ADMIN BUTTONS
    # ==================================================

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^🔐 Admin Panel$"),
            admin_panel,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^📋 Kutilayotgan e'lonlar$"),
            pending_ads,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^📋 Tasdiqlangan e'lonlar$"),
            approved_ads,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^📊 Statistika$"),
            admin_statistics,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^⬅️ Asosiy menyu$"),
            back_to_main,
        )
    )

    # ==================================================
    # ADMIN CALLBACKS
    # ==================================================

    application.add_handler(
        CallbackQueryHandler(
            admin_action,
            pattern=r"^(pay_app_|pay_rej_|ad_app_|ad_rej_)"
        )
    )

    # ==================================================
    # NEXT AD CALLBACK
    # ==================================================

    application.add_handler(
        CallbackQueryHandler(
            next_ad,
                pattern=r"^next_ad_\d+$"
        )
    )
    # ==================================================
    # SHOW ADS
    # ==================================================

    application.add_handler(
        MessageHandler(
            filters.Regex(
                r"^(🏠 Sotuvdagi uylar|🔑 Ijara uchun uylar)$"
            ),
            show_ads,
        )
    )

    # ==================================================
    # ERROR
    # ==================================================

    application.add_error_handler(
        error_handler
    )

    print(
        "Zarafshon UyTop bot started..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ==================================================
# START PROGRAM
# ==================================================

if __name__ == "__main__":
    main()
