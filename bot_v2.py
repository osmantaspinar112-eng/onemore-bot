#!/usr/bin/env python3
"""
🤖 Osman Taşpınar Ekibi — One More International Rehber Botu
Tüm özellikler dahil - Versiyon 2.0
"""

import logging
import json
import os
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ─── AYARLAR ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8664542819:AAHMQwogmLew38M3wcD9SYtuSv41aVoeEVg"
ADMIN_IDS = [1594240946]  # Kendi Telegram ID'ni yaz
ADMIN_NAME = "Osman Taşpınar"
DB_FILE = "data.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── FORM AŞAMALARI ─────────────────────────────────────────────────────────
(
    FORM_NAME, FORM_PHONE, FORM_CITY, FORM_DISTRICT,
    FORM_AGE, FORM_JOB, FORM_MARITAL, FORM_BIRTHDAY,
    FORM_TARGET_INCOME, FORM_DEBT, FORM_WORKING,
    FORM_DREAM, FORM_MOTIVATION, FORM_CHANGE, FORM_5YEAR,
    FORM_NM_EXPERIENCE, FORM_NM_QUIT, FORM_WEEKLY_HOURS,
    FORM_PHONE_SHY, FORM_SOCIAL_MEDIA,
    FORM_PERSONALITY, FORM_ROUTINE, FORM_BOOK, FORM_INVEST, FORM_TEAMWORK
) = range(25)

# ─── VERİTABANI ─────────────────────────────────────────────────────────────
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "banned": []}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_user(user_id: int):
    db = load_db()
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": user_id,
            "name": "",
            "phone": "",
            "city": "",
            "district": "",
            "age": "",
            "job": "",
            "marital": "",
            "birthday": "",
            "target_income": "",
            "has_debt": "",
            "is_working": "",
            "dream": "",
            "motivation_source": "",
            "want_to_change": "",
            "5year_goal": "",
            "nm_experience": "",
            "nm_quit_reason": "",
            "weekly_hours": "",
            "phone_shy": "",
            "social_media": "",
            "personality": "",
            "has_routine": "",
            "reads_books": "",
            "self_invest": "",
            "team_work": "",
            "sponsor_id": None,
            "sponsor_name": "",
            "join_date": datetime.now().isoformat(),
            "day": 1,
            "period": 1,
            "xp": 0,
            "badge": "🌱 Tohum",
            "completed_tasks": [],
            "completed_days": [],
            "score": 0,
            "score_label": "",
            "streak": 0,
            "last_active": datetime.now().isoformat(),
            "form_done": False,
            "unlocked_features": ["daily_tasks"],
            "contacts": [],
            "products_sold": [],
            "zoom_attendance": [],
            "fast_mode": False,
        }
        save_db(db)
    return db["users"][uid]

def update_user(user_id: int, data: dict):
    db = load_db()
    uid = str(user_id)
    db["users"][uid].update(data)
    save_db(db)

def is_banned(user_id: int):
    db = load_db()
    return user_id in db.get("banned", [])

# ─── ROZET SİSTEMİ ──────────────────────────────────────────────────────────
BADGES = [
    (0,    "🌱 Tohum"),
    (100,  "🕯️ Kıvılcım"),
    (300,  "🔥 Alev"),
    (600,  "⚡ Yıldırım"),
    (1000, "🌟 Parlayan"),
    (1500, "💎 Elmas"),
    (2500, "☀️ Güneş"),
]

PERIODS = {
    1: {"name": "🌱 Temsilci", "days": "1-90"},
    2: {"name": "🔥 Gelişen Lider", "days": "91-180"},
    3: {"name": "💎 Usta Lider", "days": "181-270"},
    4: {"name": "👑 Diamond Lider", "days": "271-360"},
}

def get_badge(xp: int) -> str:
    badge = BADGES[0][1]
    for threshold, name in BADGES:
        if xp >= threshold:
            badge = name
    return badge

def next_badge_info(xp: int):
    for threshold, name in BADGES:
        if xp < threshold:
            return name, threshold - xp
    return None, 0

# ─── MOTİVASYON SKORU ───────────────────────────────────────────────────────
def calculate_score(user: dict) -> tuple:
    score = 0

    # Haftalık saat (max 20 puan)
    hours = user.get("weekly_hours", "")
    if "15+" in hours or "10-15" in hours:
        score += 20
    elif "5-10" in hours:
        score += 12
    else:
        score += 5

    # Hedef gelir (max 20 puan)
    income = user.get("target_income", "")
    if "10.000" in income or "+" in income:
        score += 20
    elif "5.000" in income:
        score += 15
    elif "2.000" in income:
        score += 10
    else:
        score += 5

    # NM deneyimi (max 15 puan)
    exp = user.get("nm_experience", "")
    if "Deneyimliyim" in exp:
        score += 15
    elif "Biraz" in exp:
        score += 10
    else:
        score += 5

    # Kişilik (max 15 puan)
    if "Dışa dönük" in user.get("personality", ""):
        score += 15
    else:
        score += 8

    # Takım çalışması (max 10 puan)
    if "Evet" in user.get("team_work", ""):
        score += 10

    # Sosyal medya (max 10 puan)
    if "Aktif" in user.get("social_media", ""):
        score += 10
    elif "Biraz" in user.get("social_media", ""):
        score += 5

    # Kitap okuyor (max 5 puan)
    if "Evet" in user.get("reads_books", ""):
        score += 5

    # Kendine yatırım (max 5 puan)
    if "Evet" in user.get("self_invest", ""):
        score += 5

    # Skor etiketi
    if score >= 70:
        label = "🔴 Sıcak"
    elif score >= 40:
        label = "🟡 Ilık"
    else:
        label = "❄️ Soğuk"

    return score, label

# ─── KİLİTLİ ÖZELLİK SİSTEMİ ───────────────────────────────────────────────
def get_unlocked_features(day: int, current_features: list) -> list:
    features = list(current_features)
    if day >= 7 and "contacts" not in features:
        features.append("contacts")
    if day >= 14 and "leaderboard" not in features:
        features.append("leaderboard")
    if day >= 30 and "full_system" not in features:
        features.append("full_system")
        features.append("team_tree")
        features.append("products")
    return features

# ─── GÖREVLER ───────────────────────────────────────────────────────────────
def get_daily_tasks(day: int, period: int) -> list:
    if period == 1:
        if day <= 30:
            tasks = [
                {"id": f"d{day}_1", "text": "📖 El kitabından bugünkü bölümü oku", "type": "read"},
                {"id": f"d{day}_2", "text": "📱 5 kişiyle iletişime geç", "type": "action"},
                {"id": f"d{day}_3", "text": "🎯 1 potansiyel aday belirle ve listeye ekle", "type": "action"},
                {"id": f"d{day}_4", "text": "📹 Bugünün eğitim videosunu izle", "type": "video"},
            ]
        elif day <= 60:
            tasks = [
                {"id": f"d{day}_1", "text": "📱 10 kişiyle iletişime geç", "type": "action"},
                {"id": f"d{day}_2", "text": "🎤 1 sunum yap veya antrenman yap", "type": "action"},
                {"id": f"d{day}_3", "text": "👥 Alt ekibinden 2 kişiye destek ver", "type": "action"},
                {"id": f"d{day}_4", "text": "📹 Liderlik videosunu izle", "type": "video"},
            ]
        else:
            tasks = [
                {"id": f"d{day}_1", "text": "🚀 15 kişiyle iletişime geç", "type": "action"},
                {"id": f"d{day}_2", "text": "👑 Ekibinden 1 kişiyi mentorluk et", "type": "action"},
                {"id": f"d{day}_3", "text": "🎯 Aylık hedefini kontrol et", "type": "action"},
                {"id": f"d{day}_4", "text": "📹 Diamond lider videosunu izle", "type": "video"},
            ]
    else:
        tasks = [
            {"id": f"p{period}_d{day}_1", "text": "🚀 Günlük hedef temasını çalış", "type": "action"},
            {"id": f"p{period}_d{day}_2", "text": "👥 Ekip gelişimini takip et", "type": "action"},
            {"id": f"p{period}_d{day}_3", "text": "📹 İleri seviye video izle", "type": "video"},
            {"id": f"p{period}_d{day}_4", "text": "📊 Haftalık değerlendirme yap", "type": "action"},
        ]

    if day % 7 == 0:
        tasks.append({"id": f"d{day}_weekly", "text": "📊 Haftalık değerlendirme yap", "type": "action"})

    return tasks

# ─── KLAVYELER ──────────────────────────────────────────────────────────────
def main_menu_keyboard(user: dict):
    features = user.get("unlocked_features", ["daily_tasks"])
    day = user.get("day", 1)
    buttons = []

    buttons.append([InlineKeyboardButton("📅 Günlük Görevlerim", callback_data="daily_tasks")])
    buttons.append([
        InlineKeyboardButton("📊 İlerleme", callback_data="progress"),
        InlineKeyboardButton("🏅 Rozetim", callback_data="badge")
    ])
    buttons.append([InlineKeyboardButton("📚 Eğitim Merkezi", callback_data="training")])
    buttons.append([InlineKeyboardButton("💬 Motivasyon Al", callback_data="motivation")])

    if "contacts" in features:
        buttons.append([InlineKeyboardButton("👥 Kişi Takip", callback_data="contacts")])
    else:
        buttons.append([InlineKeyboardButton(f"👥 Kişi Takip 🔒 (7. günde açılır)", callback_data="locked")])

    if "leaderboard" in features:
        buttons.append([InlineKeyboardButton("🏆 Sıralama", callback_data="leaderboard")])
    else:
        buttons.append([InlineKeyboardButton(f"🏆 Sıralama 🔒 (14. günde açılır)", callback_data="locked")])

    if "products" in features:
        buttons.append([InlineKeyboardButton("🛒 Ürün Takibi", callback_data="products")])
    else:
        buttons.append([InlineKeyboardButton(f"🛒 Ürün Takibi 🔒 (30. günde açılır)", callback_data="locked")])

    if "team_tree" in features:
        buttons.append([InlineKeyboardButton("🌳 Ekip Ağacım", callback_data="team_tree")])

    buttons.append([InlineKeyboardButton("📞 Liderle İletişim", callback_data="contact_leader")])

    fast = user.get("fast_mode", False)
    fast_text = "🚀 Hızlı Mod: AÇIK" if fast else "🚀 Hızlı Mod: KAPALI"
    buttons.append([InlineKeyboardButton(fast_text, callback_data="toggle_fast")])

    return InlineKeyboardMarkup(buttons)

# ─── /START KOMUTU ──────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if is_banned(user.id):
        await update.message.reply_text("⛔ Bu bota erişiminiz kısıtlanmıştır.")
        return ConversationHandler.END

    # Sponsor tespiti (davet linki ile)
    sponsor_id = None
    sponsor_name = ""
    if context.args:
        ref = context.args[0]
        db = load_db()
        for uid, u in db["users"].items():
            ref_key = u.get("name", "").lower().replace(" ", "")
            if ref == ref_key or ref == uid:
                sponsor_id = int(uid)
                sponsor_name = u.get("name", "")
                break

    db_user = get_user(user.id)

    if db_user.get("form_done"):
        await update.message.reply_text(
            f"👋 Tekrar hoş geldin, *{db_user['name']}*!\n\n"
            f"📅 {db_user['day']}. Gündesin | ⚡ {db_user['xp']} XP | {db_user['badge']}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(db_user)
        )
        return ConversationHandler.END

    # Sponsor kaydet
    if sponsor_id:
        update_user(user.id, {"sponsor_id": sponsor_id, "sponsor_name": sponsor_name})

    await update.message.reply_text(
        f"🌟 *{ADMIN_NAME} Ekibine Hoş Geldin!*\n\n"
        f"One More International ailesinin bir parçası oldun! 🎉\n\n"
        f"Seni daha iyi tanımak için birkaç soru soracağım.\n"
        f"Sadece butonlara tıklaman yeterli, çok kolay! 😊\n\n"
        f"*Hazır mısın?* 🚀",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Hazırım, Başlayalım!", callback_data="start_form")
        ]])
    )
    return ConversationHandler.END

# ─── FORM SİSTEMİ ───────────────────────────────────────────────────────────
async def start_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👤 *Adın ve soyadın nedir?*\n\n_(Lütfen yaz)_",
        parse_mode="Markdown"
    )
    return FORM_NAME

async def form_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["form_name"] = update.message.text
    await update.message.reply_text(
        "📱 *Telefon numaran?*\n\n_(Örn: 05XX XXX XX XX)_",
        parse_mode="Markdown"
    )
    return FORM_PHONE

async def form_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["form_phone"] = update.message.text
    await update.message.reply_text(
        "🏙️ *Hangi ilde yaşıyorsun?*\n\n_(Örn: İstanbul, Ankara...)_",
        parse_mode="Markdown"
    )
    return FORM_CITY

async def form_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["form_city"] = update.message.text
    await update.message.reply_text(
        "📍 *Hangi ilçede yaşıyorsun?*",
        parse_mode="Markdown"
    )
    return FORM_DISTRICT

async def form_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["form_district"] = update.message.text
    await update.message.reply_text(
        "🎂 *Kaç yaşındasın?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("18-25", callback_data="age_18-25"),
             InlineKeyboardButton("26-35", callback_data="age_26-35")],
            [InlineKeyboardButton("36-45", callback_data="age_36-45"),
             InlineKeyboardButton("46+", callback_data="age_46+")],
        ])
    )
    return FORM_AGE

async def form_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_age"] = query.data.replace("age_", "")
    await query.edit_message_text(
        "💼 *Mesleğin nedir?*\n\n_(Örn: Öğretmen, Mühendis, Ev Hanımı...)_",
        parse_mode="Markdown"
    )
    return FORM_JOB

async def form_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["form_job"] = update.message.text
    await update.message.reply_text(
        "👨‍👩‍👧 *Medeni durumun?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💑 Evli", callback_data="marital_evli"),
             InlineKeyboardButton("🧑 Bekar", callback_data="marital_bekar")],
            [InlineKeyboardButton("👨‍👩‍👧 Evli + Çocuklu", callback_data="marital_evli_cocuklu")],
        ])
    )
    return FORM_MARITAL

async def form_marital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_marital"] = query.data.replace("marital_", "")
    await query.edit_message_text(
        "🎂 *Doğum günün? (Gün/Ay olarak yaz)*\n\n_(Örn: 15/03)_",
        parse_mode="Markdown"
    )
    return FORM_BIRTHDAY

async def form_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["form_birthday"] = update.message.text
    await update.message.reply_text(
        "💰 *Aylık ne kadar ek gelir hedefliyorsun?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("500-1.000₺", callback_data="inc_500"),
             InlineKeyboardButton("1.000-2.000₺", callback_data="inc_2000")],
            [InlineKeyboardButton("2.000-5.000₺", callback_data="inc_5000"),
             InlineKeyboardButton("10.000₺+", callback_data="inc_10000+")],
        ])
    )
    return FORM_TARGET_INCOME

async def form_target_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_target_income"] = query.data.replace("inc_", "")
    await query.edit_message_text(
        "💳 *Şu an finansal baskı hissediyor musun?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("😰 Evet, çok sıkışık", callback_data="debt_yes"),
             InlineKeyboardButton("😐 Biraz", callback_data="debt_some")],
            [InlineKeyboardButton("🙂 Hayır, iyi durumdayım", callback_data="debt_no")],
        ])
    )
    return FORM_DEBT

async def form_debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_debt"] = query.data.replace("debt_", "")
    await query.edit_message_text(
        "💼 *Şu an çalışıyor musun?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Evet, tam zamanlı", callback_data="work_fulltime"),
             InlineKeyboardButton("⏰ Evet, yarı zamanlı", callback_data="work_parttime")],
            [InlineKeyboardButton("🏠 Hayır", callback_data="work_no")],
        ])
    )
    return FORM_WORKING

async def form_working(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_working"] = query.data.replace("work_", "")
    await query.edit_message_text(
        "🌟 *En büyük hayalin ne?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Ev sahibi olmak", callback_data="dream_ev"),
             InlineKeyboardButton("✈️ Seyahat etmek", callback_data="dream_seyahat")],
            [InlineKeyboardButton("👨‍👩‍👧 Aile için zaman", callback_data="dream_aile"),
             InlineKeyboardButton("🚗 Araba almak", callback_data="dream_araba")],
            [InlineKeyboardButton("💰 Finansal özgürlük", callback_data="dream_ozgurluk")],
        ])
    )
    return FORM_DREAM

async def form_dream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_dream"] = query.data.replace("dream_", "")
    await query.edit_message_text(
        "💪 *Seni en çok ne motive eder?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 Başarı", callback_data="mot_basari"),
             InlineKeyboardButton("👨‍👩‍👧 Aile", callback_data="mot_aile")],
            [InlineKeyboardButton("💰 Para", callback_data="mot_para"),
             InlineKeyboardButton("🌍 Özgürlük", callback_data="mot_ozgurluk")],
        ])
    )
    return FORM_MOTIVATION

async def form_motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_motivation"] = query.data.replace("mot_", "")
    await query.edit_message_text(
        "🔄 *Hayatında en çok ne değiştirmek istersin?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Finansal durum", callback_data="chg_finans"),
             InlineKeyboardButton("⏰ Zaman özgürlüğü", callback_data="chg_zaman")],
            [InlineKeyboardButton("🏠 Yaşam standardı", callback_data="chg_yasam"),
             InlineKeyboardButton("🧘 Stres seviyesi", callback_data="chg_stres")],
        ])
    )
    return FORM_CHANGE

async def form_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_change"] = query.data.replace("chg_", "")
    await query.edit_message_text(
        "🔭 *5 yıl sonra kendini nerede görüyorsun?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Lider olarak", callback_data="5y_lider"),
             InlineKeyboardButton("💼 İş sahibi", callback_data="5y_isci")],
            [InlineKeyboardButton("🌍 Dünyayı gezerek", callback_data="5y_gezgin"),
             InlineKeyboardButton("🏠 Rahat bir yaşam", callback_data="5y_rahat")],
        ])
    )
    return FORM_5YEAR

async def form_5year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_5year"] = query.data.replace("5y_", "")
    await query.edit_message_text(
        "🤝 *Daha önce network marketing yaptın mı?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Hiç yapmadım", callback_data="nm_none"),
             InlineKeyboardButton("⚡ Biraz yaptım", callback_data="nm_some")],
            [InlineKeyboardButton("✅ Deneyimliyim", callback_data="nm_exp")],
        ])
    )
    return FORM_NM_EXPERIENCE

async def form_nm_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    exp = query.data.replace("nm_", "")
    context.user_data["form_nm_experience"] = exp
    if exp == "none":
        context.user_data["form_nm_quit"] = "yok"
        await query.edit_message_text(
            "⏰ *Haftada kaç saat ayırabilirsin?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1-5 saat", callback_data="hrs_1-5"),
                 InlineKeyboardButton("5-10 saat", callback_data="hrs_5-10")],
                [InlineKeyboardButton("10-15 saat", callback_data="hrs_10-15"),
                 InlineKeyboardButton("15+ saat", callback_data="hrs_15+")],
            ])
        )
        return FORM_WEEKLY_HOURS
    else:
        await query.edit_message_text(
            "🤔 *Neden bıraktın veya neden yeni bir şirket seçtin?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Sistem işe yaramadı", callback_data="quit_sistem"),
                 InlineKeyboardButton("👥 Destek yoktu", callback_data="quit_destek")],
                [InlineKeyboardButton("⏰ Zaman bulamadım", callback_data="quit_zaman"),
                 InlineKeyboardButton("🌟 Daha iyisini aradım", callback_data="quit_better")],
            ])
        )
        return FORM_NM_QUIT

async def form_nm_quit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_nm_quit"] = query.data.replace("quit_", "")
    await query.edit_message_text(
        "⏰ *Haftada kaç saat ayırabilirsin?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1-5 saat", callback_data="hrs_1-5"),
             InlineKeyboardButton("5-10 saat", callback_data="hrs_5-10")],
            [InlineKeyboardButton("10-15 saat", callback_data="hrs_10-15"),
             InlineKeyboardButton("15+ saat", callback_data="hrs_15+")],
        ])
    )
    return FORM_WEEKLY_HOURS

async def form_weekly_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_weekly_hours"] = query.data.replace("hrs_", "")
    await query.edit_message_text(
        "📞 *Telefonda yabancılarla konuşmaktan çekiniyor musun?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("😰 Evet, çekiniyorum", callback_data="shy_yes"),
             InlineKeyboardButton("😐 Biraz", callback_data="shy_some")],
            [InlineKeyboardButton("💪 Hayır, rahatım", callback_data="shy_no")],
        ])
    )
    return FORM_PHONE_SHY

async def form_phone_shy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_phone_shy"] = query.data.replace("shy_", "")
    await query.edit_message_text(
        "📱 *Sosyal medyayı ne kadar aktif kullanıyorsun?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Çok aktif", callback_data="sm_active"),
             InlineKeyboardButton("😐 Biraz", callback_data="sm_some")],
            [InlineKeyboardButton("❌ Pek kullanmıyorum", callback_data="sm_no")],
        ])
    )
    return FORM_SOCIAL_MEDIA

async def form_social_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_social_media"] = query.data.replace("sm_", "")
    await query.edit_message_text(
        "🧠 *Kendini nasıl tanımlarsın?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗣️ Dışa dönük", callback_data="per_extro"),
             InlineKeyboardButton("🤫 İçe dönük", callback_data="per_intro")],
            [InlineKeyboardButton("⚖️ Her ikisi de", callback_data="per_both")],
        ])
    )
    return FORM_PERSONALITY

async def form_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_personality"] = query.data.replace("per_", "")
    await query.edit_message_text(
        "⏰ *Günlük bir rutinin var mı?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Evet, düzenli", callback_data="rut_yes"),
             InlineKeyboardButton("😅 Biraz", callback_data="rut_some")],
            [InlineKeyboardButton("❌ Hayır", callback_data="rut_no")],
        ])
    )
    return FORM_ROUTINE

async def form_routine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_routine"] = query.data.replace("rut_", "")
    await query.edit_message_text(
        "📚 *Düzenli kitap okuyor musun?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Evet", callback_data="book_yes"),
             InlineKeyboardButton("😅 Bazen", callback_data="book_some")],
            [InlineKeyboardButton("❌ Hayır", callback_data="book_no")],
        ])
    )
    return FORM_BOOK

async def form_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_book"] = query.data.replace("book_", "")
    await query.edit_message_text(
        "💡 *Kendine yatırım yapar mısın? (Eğitim, kurs vs)*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Evet, yaparım", callback_data="inv_yes"),
             InlineKeyboardButton("🤔 Düşünürüm", callback_data="inv_maybe")],
            [InlineKeyboardButton("❌ Genelde yapmam", callback_data="inv_no")],
        ])
    )
    return FORM_INVEST

async def form_invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["form_invest"] = query.data.replace("inv_", "")
    await query.edit_message_text(
        "🤝 *Takım çalışmasına açık mısın?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Evet, çok açığım", callback_data="team_yes"),
             InlineKeyboardButton("🤔 Duruma göre", callback_data="team_maybe")],
            [InlineKeyboardButton("❌ Bağımsız çalışmayı severim", callback_data="team_no")],
        ])
    )
    return FORM_TEAMWORK

async def form_teamwork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    fd = context.user_data

    # Skoru hesapla
    temp_user = {
        "weekly_hours": fd.get("form_weekly_hours", ""),
        "target_income": fd.get("form_target_income", ""),
        "nm_experience": fd.get("form_nm_experience", ""),
        "personality": fd.get("form_personality", ""),
        "team_work": query.data,
        "social_media": fd.get("form_social_media", ""),
        "reads_books": fd.get("form_book", ""),
        "self_invest": fd.get("form_invest", ""),
    }
    score, label = calculate_score(temp_user)

    # Kullanıcıyı güncelle
    name = fd.get("form_name", query.from_user.first_name)
    ref_key = name.lower().replace(" ", "")

    update_user(user_id, {
        "name": name,
        "phone": fd.get("form_phone", ""),
        "city": fd.get("form_city", ""),
        "district": fd.get("form_district", ""),
        "age": fd.get("form_age", ""),
        "job": fd.get("form_job", ""),
        "marital": fd.get("form_marital", ""),
        "birthday": fd.get("form_birthday", ""),
        "target_income": fd.get("form_target_income", ""),
        "has_debt": fd.get("form_debt", ""),
        "is_working": fd.get("form_working", ""),
        "dream": fd.get("form_dream", ""),
        "motivation_source": fd.get("form_motivation", ""),
        "want_to_change": fd.get("form_change", ""),
        "5year_goal": fd.get("form_5year", ""),
        "nm_experience": fd.get("form_nm_experience", ""),
        "nm_quit_reason": fd.get("form_nm_quit", ""),
        "weekly_hours": fd.get("form_weekly_hours", ""),
        "phone_shy": fd.get("form_phone_shy", ""),
        "social_media": fd.get("form_social_media", ""),
        "personality": fd.get("form_personality", ""),
        "has_routine": fd.get("form_routine", ""),
        "reads_books": fd.get("form_book", ""),
        "self_invest": fd.get("form_invest", ""),
        "team_work": query.data,
        "score": score,
        "score_label": label,
        "form_done": True,
        "ref_key": ref_key,
    })

    db_user = get_user(user_id)

    # Skora göre karşılama mesajı
    if label == "🔴 Sıcak":
        welcome_extra = "Profilin çok güçlü! Seninle harika işler yapacağız! 🔥"
    elif label == "🟡 Ilık":
        welcome_extra = "İyi bir başlangıç! Birlikte büyüyeceğiz! 💪"
    else:
        welcome_extra = "Her büyük yolculuk küçük bir adımla başlar! 🌱"

    # Admin'e bildirim
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🔔 *Yeni Üye Katıldı!*\n\n"
                    f"👤 {name}\n"
                    f"📍 {fd.get('form_city', '')} / {fd.get('form_district', '')}\n"
                    f"💼 {fd.get('form_job', '')}\n"
                    f"💰 Hedef: {fd.get('form_target_income', '')}₺\n"
                    f"⏰ Haftalık: {fd.get('form_weekly_hours', '')} saat\n"
                    f"📊 Motivasyon Skoru: *{score}/100 — {label}*\n"
                    f"👥 Sponsor: {db_user.get('sponsor_name', 'Doğrudan')}"
                ),
                parse_mode="Markdown"
            )
        except:
            pass

    await query.edit_message_text(
        f"🎉 *Hoş geldin, {name}!*\n\n"
        f"{welcome_extra}\n\n"
        f"📎 El kitabın hazırlandı, hemen başlayabilirsin!\n\n"
        f"🚀 *90 günlük yolculuğun başlıyor!*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📖 El Kitabını Al", url="https://www.onemoreinternational.com/temsilcinin-el-kitabi/")
        ], [
            InlineKeyboardButton("📅 İlk Görevime Başla!", callback_data="daily_tasks")
        ]])
    )
    return ConversationHandler.END

# ─── BUTON YÖNETİCİSİ ───────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if is_banned(user_id):
        await query.edit_message_text("⛔ Erişiminiz kısıtlanmıştır.")
        return

    db_user = get_user(user_id)
    data = query.data

    if data == "locked":
        await query.answer("🔒 Bu özellik henüz açılmadı! Görevlerini tamamla.", show_alert=True)
        return

    elif data == "main_menu":
        await query.edit_message_text(
            f"🏠 *Ana Menü*\n\n"
            f"Merhaba {db_user['name']}! 👋\n"
            f"📅 {db_user['day']}. Gün | ⚡ {db_user['xp']} XP | {db_user['badge']}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(db_user)
        )

    elif data == "toggle_fast":
        new_fast = not db_user.get("fast_mode", False)
        update_user(user_id, {"fast_mode": new_fast})
        db_user = get_user(user_id)
        status = "AÇIK 🚀" if new_fast else "KAPALI"
        await query.answer(f"Hızlı Mod {status}", show_alert=True)
        await query.edit_message_text(
            f"🏠 *Ana Menü*\n\n"
            f"Merhaba {db_user['name']}! 👋\n"
            f"📅 {db_user['day']}. Gün | ⚡ {db_user['xp']} XP | {db_user['badge']}",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(db_user)
        )

    elif data == "daily_tasks":
        await show_daily_tasks(query, db_user)

    elif data.startswith("complete_task_"):
        await complete_task(query, context, user_id, db_user, data)

    elif data == "progress":
        await show_progress(query, db_user)

    elif data == "badge":
        await show_badges(query, db_user)

    elif data == "training":
        await show_training(query, db_user)

    elif data == "motivation":
        await show_motivation(query)

    elif data == "leaderboard":
        await show_leaderboard(query, db_user)

    elif data == "contacts":
        await show_contacts(query, db_user)

    elif data == "products":
        await show_products(query)

    elif data == "team_tree":
        await show_team_tree(query, user_id)

    elif data == "contact_leader":
        await query.edit_message_text(
            f"📞 *{ADMIN_NAME} ile İletişim*\n\n"
            f"Herhangi bir konuda yardıma mı ihtiyacın var?\n\n"
            f"👤 Lider: *{ADMIN_NAME}*\n"
            f"📱 Telegram: @[KULLANICI_ADI]\n"
            f"📞 WhatsApp: +90 XXX XXX XX XX\n\n"
            f"💡 Soru sormak büyümenin ilk adımıdır! 💪",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]])
        )

# ─── GÜNLÜK GÖREVLER ────────────────────────────────────────────────────────
async def show_daily_tasks(query, db_user):
    day = db_user["day"]
    period = db_user.get("period", 1)
    tasks = get_daily_tasks(day, period)
    completed = db_user.get("completed_tasks", [])
    completed_days = db_user.get("completed_days", [])

    # Önceki gün tamamlandı mı kontrol et
    if day > 1 and (day - 1) not in completed_days:
        if not db_user.get("fast_mode", False):
            await query.edit_message_text(
                f"🔒 *{day}. Gün Kilitli*\n\n"
                f"⚠️ {day - 1}. günün görevlerini tamamlamadan ilerleyemezsin!\n\n"
                f"Geri dön ve önceki günü tamamla. 💪",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]])
            )
            return

    task_text = f"📅 *{day}. Gün Görevlerin* — {PERIODS.get(period, {}).get('name', '')}\n\n"
    buttons = []
    all_done = True

    for task in tasks:
        done = task["id"] in completed
        if not done:
            all_done = False
        icon = "✅" if done else "⬜"
        type_icon = {"read": "📖", "video": "📹", "action": "🎯"}.get(task["type"], "🎯")
        task_text += f"{icon} {type_icon} {task['text']}\n"
        if not done:
            buttons.append([InlineKeyboardButton(
                f"✅ Tamamla",
                callback_data=f"complete_task_{task['id']}"
            )])

    task_text += f"\n⚡ XP: *{db_user['xp']}* | 🏅 *{db_user['badge']}*"

    if all_done:
        task_text += "\n\n🎉 *Tüm görevler tamamlandı!*"

    buttons.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")])

    await query.edit_message_text(
        task_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def complete_task(query, context, user_id, db_user, data):
    task_id = data.replace("complete_task_", "")
    completed = db_user.get("completed_tasks", [])

    if task_id in completed:
        await query.answer("Bu görevi zaten tamamladın!", show_alert=True)
        return

    # Video görev ise onay sor
    if "_4" in task_id or "video" in task_id:
        await query.answer("📹 Videoyu izledin mi? Tamamlandı olarak işaretleniyor...", show_alert=False)

    completed.append(task_id)
    new_xp = db_user["xp"] + 25
    new_badge = get_badge(new_xp)

    # Gün tamamlandı mı?
    day = db_user["day"]
    period = db_user.get("period", 1)
    tasks = get_daily_tasks(day, period)
    all_done = all(t["id"] in completed for t in tasks)

    completed_days = db_user.get("completed_days", [])
    new_day = day
    new_period = period

    if all_done:
        if day not in completed_days:
            completed_days.append(day)
        new_day = day + 1

        # Dönem geçişi
        if new_day > 90 and period == 1:
            new_period = 2
            new_day = 1
        elif new_day > 90 and period < 4:
            new_period = period + 1
            new_day = 1

    # Özellikleri aç
    new_features = get_unlocked_features(new_day, db_user.get("unlocked_features", ["daily_tasks"]))

    update_user(user_id, {
        "completed_tasks": completed,
        "xp": new_xp,
        "badge": new_badge,
        "day": new_day,
        "period": new_period,
        "completed_days": completed_days,
        "unlocked_features": new_features,
        "last_active": datetime.now().isoformat(),
    })

    if all_done:
        msg = f"🎉 *{day}. Günü Tamamladın!* +25 XP\n{new_day}. Güne geçtin! ⚡ Toplam: {new_xp} XP"

        # Yeni özellik açıldı mı?
        if "contacts" in new_features and "contacts" not in db_user.get("unlocked_features", []):
            msg += "\n\n🔓 *Yeni Özellik Açıldı: Kişi Takip Sistemi!*"
        if "leaderboard" in new_features and "leaderboard" not in db_user.get("unlocked_features", []):
            msg += "\n\n🔓 *Yeni Özellik Açıldı: Liderboard!*"

        await query.answer(msg[:200], show_alert=True)
    else:
        await query.answer(f"✅ +25 XP! Toplam: {new_xp} XP", show_alert=False)

    db_user = get_user(user_id)
    await show_daily_tasks(query, db_user)

# ─── İLERLEME ───────────────────────────────────────────────────────────────
async def show_progress(query, db_user):
    day = db_user["day"]
    xp = db_user["xp"]
    period = db_user.get("period", 1)
    period_name = PERIODS.get(period, {}).get("name", "")
    next_b, needed = next_badge_info(xp)
    total_day = (period - 1) * 90 + day

    text = (
        f"📊 *İlerleme Durumun*\n\n"
        f"🗓️ *{period_name}*\n"
        f"📅 {day}. Gün (Toplam: {total_day}. gün)\n\n"
        f"⚡ XP: *{xp}*\n"
        f"🏅 Rozet: *{db_user['badge']}*\n"
    )
    if next_b:
        text += f"🎯 Sonraki: {next_b} (kalan {needed} XP)\n"

    text += f"\n✅ Tamamlanan gün: {len(db_user.get('completed_days', []))}"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]])
    )

# ─── ROZETLER ───────────────────────────────────────────────────────────────
async def show_badges(query, db_user):
    xp = db_user["xp"]
    text = "🏅 *Rozet Yolculuğun*\n\n"
    for threshold, name in BADGES:
        icon = "✅" if xp >= threshold else "🔒"
        text += f"{icon} {name} — {threshold} XP\n"
    text += f"\n⚡ Şu anki XP: *{xp}*"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]])
    )

# ─── EĞİTİM ─────────────────────────────────────────────────────────────────
async def show_training(query, db_user):
    score_label = db_user.get("score_label", "❄️ Soğuk")

    text = "📚 *Eğitim Merkezi*\n\n"
    if "Sıcak" in score_label:
        text += "🔴 *İleri Seviye Eğitimler*\n"
    elif "Ilık" in score_label:
        text += "🟡 *Orta Seviye Eğitimler*\n"
    else:
        text += "🌱 *Temel Eğitimler*\n"

    await query.edit_message_text(
        text + "\nHangi konuda eğitim almak istersin?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 90 Günlük Plan", callback_data="train_90day")],
            [InlineKeyboardButton("📣 Sunum Yapma", callback_data="train_presentation"),
             InlineKeyboardButton("🤝 Üye Alma", callback_data="train_recruit")],
            [InlineKeyboardButton("💰 Gelir Sistemi", callback_data="train_income"),
             InlineKeyboardButton("📱 Sosyal Medya", callback_data="train_social")],
            [InlineKeyboardButton("📖 Kitap Önerileri", callback_data="train_books")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")],
        ])
    )

# ─── MOTİVASYON ─────────────────────────────────────────────────────────────
async def show_motivation(query):
    quotes = [
        "🔥 *'Başarı bir olay değil, bir alışkanlıktır.'*\nHer gün küçük adımlar büyük sonuçlar doğurur!",
        "💎 *'Kömür baskı altında elmasa dönüşür.'*\nZorluklardan kaç değil, onları yakıt yap!",
        "🚀 *'Başkalarının yapamadığını yaparsan,\nbaşkalarının sahip olmadığına sahip olursun.'*",
        "🌟 *'Dün bittiğinde bugün başlar. Fırsatlar seni bekliyor!'*",
        "⚡ *'Küçük günlük kazanımlar büyük hayatları inşa eder.'*",
        "🏆 *'Hayallerinle değil, eylemlerinle tanınırsın.'*",
        "💪 *'En zorlu yollar en güzel manzaralara çıkar.'*",
    ]

    await query.edit_message_text(
        f"💬 *Günün Motivasyonu*\n\n{random.choice(quotes)}\n\n"
        f"— {ADMIN_NAME} Ekibinden, sevgiyle 🌟",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Başka Bir Tane", callback_data="motivation")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
        ])
    )

# ─── LİDERBOARD ─────────────────────────────────────────────────────────────
async def show_leaderboard(query, db_user):
    db = load_db()
    users = [(u["name"], u["xp"], u["badge"]) for u in db["users"].values() if u.get("form_done")]
    users.sort(key=lambda x: x[1], reverse=True)

    text = "🏆 *Bu Haftanın Sıralaması*\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, (name, xp, badge) in enumerate(users[:10]):
        rank = medals[i] if i < 3 else f"{i+1}."
        marker = " ◄ Sen" if name == db_user.get("name") else ""
        text += f"{rank} {badge} {name} — {xp} XP{marker}\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]])
    )

# ─── KİŞİ TAKİP ─────────────────────────────────────────────────────────────
async def show_contacts(query, db_user):
    contacts = db_user.get("contacts", [])

    text = "👥 *Kişi Takip Listesi*\n\n"
    if not contacts:
        text += "Henüz kişi eklemedin.\n"
    else:
        for c in contacts[:10]:
            status_icon = {"arandı": "🟢", "cevap_yok": "🔴", "dusunuyor": "🟡", "olumsuz": "⚫"}.get(c.get("status", ""), "⚪")
            text += f"{status_icon} *{c['name']}* — {c.get('status', 'Yeni')}\n"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yeni Kişi Ekle", callback_data="add_contact")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
        ])
    )

# ─── ÜRÜNLER ─────────────────────────────────────────────────────────────────
async def show_products(query):
    text = (
        "🛒 *One More International Ürünleri*\n\n"
        "💊 *Sağlık & Takviye*\n"
        "Painless Night GLU, B12 Plus, Dekamin,\nOmevia, Melatonin Plus, Glutamore\n\n"
        "☕ *İçecek*\n"
        "Omicoff Classic/Mocha/Latte,\nFit&More Chocolate/Vanilla Shake\n\n"
        "💄 *Cilt & Güzellik*\n"
        "Lumiere Beauty Set, Collagen Patch,\nAnti-Aging Mask, Face Lifting Mask, Sunscreen\n\n"
        "💇 *Saç & Kişisel Bakım*\n"
        "Hair Repair Shampoo/Mask, Shower Gel\n\n"
        "🦷 *Ağız Bakımı*\n"
        "Omiprodent Toothpaste, Omiprodent Set\n\n"
        "🐾 *Evcil Hayvan*\n"
        "Pawsy Nano Spray, Towel, Wipes\n\n"
        "🧹 *Temizlik*\n"
        "Omiclean Wipes, Omiclean Powder"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ One More Market", url="https://onemoremarket.com/products")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
        ])
    )

# ─── EKİP AĞACI ─────────────────────────────────────────────────────────────
async def show_team_tree(query, user_id):
    db = load_db()
    uid = str(user_id)

    # Bu kullanıcının getirdiklerini bul
    children = [(u["name"], u["xp"], u["badge"], u.get("day", 1))
                for u in db["users"].values()
                if str(u.get("sponsor_id", "")) == uid and u.get("form_done")]

    text = "🌳 *Ekip Ağacım*\n\n"
    if not children:
        text += "Henüz ekibine kimse katılmadı.\n\nDavet linkini paylaş ve ekibini büyüt! 🚀"
    else:
        text += f"Toplam ekip: *{len(children)} kişi*\n\n"
        for name, xp, badge, day in children:
            text += f"├── {badge} *{name}* — Gün {day} — {xp} XP\n"

    db_user = get_user(user_id)
    ref_key = db_user.get("ref_key", str(user_id))
    invite_link = f"t.me/{(await query.bot.get_me()).username}?start={ref_key}"

    await query.edit_message_text(
        text + f"\n\n🔗 *Davet Linkin:*\n`{invite_link}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]])
    )

# ─── ADMİN KOMUTLARI ────────────────────────────────────────────────────────
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /broadcast mesaj")
        return
    msg = " ".join(context.args)
    db = load_db()
    count = 0
    for uid in db["users"]:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *{ADMIN_NAME}'dan Mesaj:*\n\n{msg}",
                parse_mode="Markdown"
            )
            count += 1
        except:
            pass
    await update.message.reply_text(f"✅ {count} kişiye gönderildi!")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    db = load_db()
    users = db["users"]
    total = len(users)
    active_today = sum(1 for u in users.values()
                      if (datetime.now() - datetime.fromisoformat(u.get("last_active", datetime.now().isoformat()))).days < 1)

    score_dist = {"🔴 Sıcak": 0, "🟡 Ilık": 0, "❄️ Soğuk": 0}
    for u in users.values():
        label = u.get("score_label", "❄️ Soğuk")
        if label in score_dist:
            score_dist[label] += 1

    text = (
        f"📊 *Ekip İstatistikleri*\n\n"
        f"👥 Toplam: *{total}* üye\n"
        f"⚡ Bugün aktif: *{active_today}*\n\n"
        f"*Motivasyon Dağılımı:*\n"
        f"🔴 Sıcak: {score_dist['🔴 Sıcak']}\n"
        f"🟡 Ilık: {score_dist['🟡 Ilık']}\n"
        f"❄️ Soğuk: {score_dist['❄️ Soğuk']}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    db = load_db()
    text = "👥 *Ekip Listesi*\n\n"
    for u in db["users"].values():
        if u.get("form_done"):
            text += f"• {u['name']} | {u.get('city','')} | Gün {u.get('day',1)} | {u.get('badge','')} | {u.get('score_label','')}\n"
    if len(text) > 4000:
        text = text[:4000] + "..."
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /ban [user_id]")
        return
    db = load_db()
    ban_id = int(context.args[0])
    if ban_id not in db.get("banned", []):
        db.setdefault("banned", []).append(ban_id)
        save_db(db)
        await update.message.reply_text(f"⛔ {ban_id} engellendi.")
    else:
        await update.message.reply_text("Bu kişi zaten engelli.")

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /unban [user_id]")
        return
    db = load_db()
    ban_id = int(context.args[0])
    if ban_id in db.get("banned", []):
        db["banned"].remove(ban_id)
        save_db(db)
        await update.message.reply_text(f"✅ {ban_id} engeli kaldırıldı.")

async def admin_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kişiye özel davet linki oluştur: /invite [user_id]"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /invite [user_id]")
        return
    db = load_db()
    uid = context.args[0]
    if uid in db["users"]:
        u = db["users"][uid]
        bot = await context.bot.get_me()
        ref_key = u.get("ref_key", uid)
        link = f"t.me/{bot.username}?start={ref_key}"
        await update.message.reply_text(
            f"🔗 *{u['name']}'ın Davet Linki:*\n`{link}`",
            parse_mode="Markdown"
        )

# ─── OTOMATİK MESAJLAR ──────────────────────────────────────────────────────
async def send_daily_motivation(context: ContextTypes.DEFAULT_TYPE):
    quotes = [
        "🌅 Günaydın! Bugün yeni bir fırsat. Görevlerini tamamlamayı unutma! 💪",
        "🔥 Günaydın! Her gün bir adım daha ileri. Hadi başlayalım! 🚀",
        "⭐ Günaydın! Başarı bir günde gelmiyor ama her gün yaklaşıyorsun! 🏆",
    ]
    db = load_db()
    for uid, user in db["users"].items():
        if not user.get("form_done"):
            continue
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=random.choice(quotes) + "\n\n👉 /start ile bota gir!"
            )
        except:
            pass

async def send_weekly_reminder(context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    for uid, user in db["users"].items():
        if not user.get("form_done"):
            continue
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    f"📊 *Haftalık Hatırlatma!*\n\n"
                    f"Merhaba {user.get('name', '')}! 👋\n\n"
                    f"📅 {user.get('day', 1)}. gündesin\n"
                    f"⚡ {user.get('xp', 0)} XP | {user.get('badge', '')}\n\n"
                    f"Bu hafta:\n"
                    f"✅ Her gün görevlerini tamamla\n"
                    f"✅ En az 3 kişiyle görüş\n"
                    f"✅ Ekibini motive et 🚀"
                ),
                parse_mode="Markdown"
            )
        except:
            pass

async def send_inactivity_warning(context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    now = datetime.now()
    for uid, user in db["users"].items():
        if not user.get("form_done"):
            continue
        last = user.get("last_active")
        if last:
            diff = (now - datetime.fromisoformat(last)).total_seconds()
            if diff > 86400:
                try:
                    await context.bot.send_message(
                        chat_id=int(uid),
                        text=f"⚠️ {user.get('name', '')}! 24 saattir aktif değilsin.\nGörevlerin seni bekliyor! 👉 /start"
                    )
                except:
                    pass

async def check_birthdays(context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    today = datetime.now().strftime("%d/%m")
    for uid, user in db["users"].items():
        birthday = user.get("birthday", "")
        if birthday and birthday.startswith(today[:5]):
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=(
                        f"🎂 *Doğum Günün Kutlu Olsun, {user['name']}!*\n\n"
                        f"Bu özel günde {ADMIN_NAME} olarak yanındayım! 🌟\n"
                        f"Bu yıl birlikte çok güzel şeyler başaracağız!\n\n"
                        f"Seni ekibimizde görmekten mutluluk duyuyoruz! 💎"
                    ),
                    parse_mode="Markdown"
                )
                # Admin'e de bildir
                for admin_id in ADMIN_IDS:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"🎂 Bugün *{user['name']}'ın* doğum günü! Tebrik mesajı gönderildi.",
                        parse_mode="Markdown"
                    )
            except:
                pass

async def check_critical_days(context: ContextTypes.DEFAULT_TYPE):
    """7. 14. 21. günlerde özel mesaj"""
    db = load_db()
    critical_days = {
        7: "7. gündesin! Bu kritik bir dönüm noktası. Devam etmek güç ama sen yapabilirsin! 💪",
        14: "14. gündesin! 2 haftayı geride bıraktın. Ekibinin en kararlısısın! 🔥",
        21: "21. gündesin! 21 gün bir alışkanlık oluşturur. Sen artık farklısın! ⭐",
    }
    for uid, user in db["users"].items():
        day = user.get("day", 1)
        if day in critical_days and user.get("form_done"):
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=f"🎯 *Kritik Gün!*\n\n{critical_days[day]}\n\n— {ADMIN_NAME} 🌟",
                    parse_mode="Markdown"
                )
            except:
                pass

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(start_form, pattern="^start_form$"),
        ],
        states={
            FORM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_name)],
            FORM_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_phone)],
            FORM_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_city)],
            FORM_DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_district)],
            FORM_AGE: [CallbackQueryHandler(form_age, pattern="^age_")],
            FORM_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_job)],
            FORM_MARITAL: [CallbackQueryHandler(form_marital, pattern="^marital_")],
            FORM_BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_birthday)],
            FORM_TARGET_INCOME: [CallbackQueryHandler(form_target_income, pattern="^inc_")],
            FORM_DEBT: [CallbackQueryHandler(form_debt, pattern="^debt_")],
            FORM_WORKING: [CallbackQueryHandler(form_working, pattern="^work_")],
            FORM_DREAM: [CallbackQueryHandler(form_dream, pattern="^dream_")],
            FORM_MOTIVATION: [CallbackQueryHandler(form_motivation, pattern="^mot_")],
            FORM_CHANGE: [CallbackQueryHandler(form_change, pattern="^chg_")],
            FORM_5YEAR: [CallbackQueryHandler(form_5year, pattern="^5y_")],
            FORM_NM_EXPERIENCE: [CallbackQueryHandler(form_nm_experience, pattern="^nm_")],
            FORM_NM_QUIT: [CallbackQueryHandler(form_nm_quit, pattern="^quit_")],
            FORM_WEEKLY_HOURS: [CallbackQueryHandler(form_weekly_hours, pattern="^hrs_")],
            FORM_PHONE_SHY: [CallbackQueryHandler(form_phone_shy, pattern="^shy_")],
            FORM_SOCIAL_MEDIA: [CallbackQueryHandler(form_social_media, pattern="^sm_")],
            FORM_PERSONALITY: [CallbackQueryHandler(form_personality, pattern="^per_")],
            FORM_ROUTINE: [CallbackQueryHandler(form_routine, pattern="^rut_")],
            FORM_BOOK: [CallbackQueryHandler(form_book, pattern="^book_")],
            FORM_INVEST: [CallbackQueryHandler(form_invest, pattern="^inv_")],
            FORM_TEAMWORK: [CallbackQueryHandler(form_teamwork, pattern="^team_")],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("list", admin_list))
    app.add_handler(CommandHandler("ban", admin_ban))
    app.add_handler(CommandHandler("unban", admin_unban))
    app.add_handler(CommandHandler("invite", admin_invite))

    scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")
    scheduler.add_job(send_daily_motivation, "cron", hour=8, minute=0, args=[app])
    scheduler.add_job(send_weekly_reminder, "cron", day_of_week="mon", hour=9, args=[app])
    scheduler.add_job(send_inactivity_warning, "cron", hour=20, args=[app])
    scheduler.add_job(check_birthdays, "cron", hour=9, minute=0, args=[app])
    scheduler.add_job(check_critical_days, "cron", hour=8, minute=30, args=[app])
    scheduler.start()

    logger.info("🚀 Bot başlatıldı!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
