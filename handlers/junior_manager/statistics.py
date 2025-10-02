# handlers/junior_manager/statistics.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from zoneinfo import ZoneInfo
from datetime import timezone, timedelta

from filters.role_filter import RoleFilter
from database.jm_inbox_queries import db_get_user_by_telegram_id

# --- import fallback: stats_queries yoki statistika_queries ---

from database.junior_manager_statistika_queries import get_jm_stats_for_telegram

router = Router()
router.message.filter(RoleFilter("junior_manager"))
router.callback_query.filter(RoleFilter("junior_manager"))

# --- I18N ---
def _norm_lang(v: str | None) -> str:
    v = (v or "uz").lower()
    return "ru" if v.startswith("ru") else "uz"

TR = {
    "title": {
        "uz": "📊 <b>Kichik menejer — Statistika</b>\n",
        "ru": "📊 <b>Младший менеджер — Статистика</b>\n",
    },
    "today": {"uz": "📅 <b>Bugun</b>", "ru": "📅 <b>Сегодня</b>"},
    "7d": {"uz": "🗓 <b>So‘nggi 7 kun</b>", "ru": "🗓 <b>Последние 7 дней</b>"},
    "10d": {"uz": "🗓 <b>So‘nggi 10 kun</b>", "ru": "🗓 <b>Последние 10 дней</b>"},
    "30d": {"uz": "🗓 <b>So‘nggi 30 kun</b>", "ru": "🗓 <b>Последние 30 дней</b>"},
    "received": {"uz": "• Qabul qilingan", "ru": "• Принято"},
    "sent_to_controller": {"uz": "• Controllerga yuborilgan", "ru": "• Отправлено контролёру"},
    "completed_from_sent": {
        "uz": "• Yuborganlaridan <code>completed</code>",
        "ru": "• Из отправленных <code>completed</code>",
    },
    # 🆕 staff_orders metrikalari:
    "created_by_me": {"uz": "• O‘zim yaratgan", "ru": "• Создано мной"},
    "created_completed": {"uz": "• O‘zim yaratganlardan <code>completed</code>",
                          "ru": "• Из созданных мной <code>completed</code>"},
    "no_user": {
        "uz": "Foydalanuvchi profili topilmadi (users jadvali bilan moslik yo‘q).",
        "ru": "Профиль пользователя не найден (нет соответствия с таблицей users).",
    },
}

def tr(lang: str, key: str) -> str:
    lang = _norm_lang(lang)
    return TR.get(key, {}).get(lang, key)

# --- Timezone ---
def _tz():
    try:
        return ZoneInfo("Asia/Tashkent")
    except Exception:
        return timezone(timedelta(hours=5))

# --- Format helpers ---
def _fmt_block(lang: str, row: dict) -> str:
    # row ichida kalitlar bo'lmasa, 0 sifatida ko'rsatamiz
    r = int(row.get("received", 0))
    s = int(row.get("sent_to_controller", 0))
    c = int(row.get("completed_from_sent", 0))
    m = int(row.get("created_by_me", 0))
    mc = int(row.get("created_completed", 0))

    return (
        f"{tr(lang,'received')}: <b>{r}</b>\n"
        f"{tr(lang,'sent_to_controller')}: <b>{s}</b>\n"
        f"{tr(lang,'completed_from_sent')}: <b>{c}</b>\n"
        f"{tr(lang,'created_by_me')}: <b>{m}</b>\n"
        f"{tr(lang,'created_completed')}: <b>{mc}</b>\n"
    )

def _fmt_stats(lang: str, stats: dict) -> str:
    return "\n".join([
        tr(lang, "title"),
        tr(lang, "today"),
        _fmt_block(lang, stats["today"]),
        tr(lang, "7d"),
        _fmt_block(lang, stats["7d"]),
        tr(lang, "10d"),
        _fmt_block(lang, stats["10d"]),
        tr(lang, "30d"),
        _fmt_block(lang, stats["30d"]),
    ])

# --- Entry (reply button) ---
ENTRY_TEXTS = [
    "📊 Statistika",  # uz
    "📊 Статистика",  # ru
]

@router.message(F.text.in_(ENTRY_TEXTS))
async def jm_stats_msg(msg: Message, state: FSMContext):
    # tilni olish uchun foydalanuvchini DBdan olamiz
    u = await db_get_user_by_telegram_id(msg.from_user.id)
    lang = _norm_lang(u.get("language") if u else "uz")

    # statistika olishda tz beramiz
    stats = await get_jm_stats_for_telegram(msg.from_user.id, tz=_tz())
    if stats is None:
        await msg.answer(tr(lang, "no_user"))
        return
    await msg.answer(_fmt_stats(lang, stats))

# --- Callback variant ---
@router.callback_query(F.data == "jm_stats")
async def jm_stats_cb(cb: CallbackQuery, state: FSMContext):
    u = await db_get_user_by_telegram_id(cb.from_user.id)
    lang = _norm_lang(u.get("language") if u else "uz")

    stats = await get_jm_stats_for_telegram(cb.from_user.id, tz=_tz())
    if stats is None:
        await cb.message.edit_text(tr(lang, "no_user"))
        return
    await cb.message.edit_text(_fmt_stats(lang, stats))
