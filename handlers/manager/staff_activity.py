# handlers/manager/staff_activity.py
# Reply tugmadan: "👥 Xodimlar faoliyati" / "👥 Активность сотрудников"
# Hech qanday inline tugma yo'q — darhol matnli hisobot yuboradi (UZ/RU).

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

from filters.role_filter import RoleFilter
from database.manager.orders import fetch_staff_activity
# Foydalanuvchi tilini olish uchun (users.language) — loyihangizdagi mavjud funksiya:
from database.basic.user import get_user_by_telegram_id

router = Router()
logger = logging.getLogger(__name__)
router.message.filter(RoleFilter("manager"))

# ---------------- I18N ----------------
T = {
    "title": {
        "uz": "👥 Xodimlar faoliyati",
        "ru": "👥 Активность сотрудников",
    },
    "legend": {
        "uz": "Hisobot: menejerlar kesimi (connection/technician/aktiv)",
        "ru": "Отчёт: по менеджерам (подключение/техник/активные)",
    },
    "totals": {
        "uz": "— Jami xodimlar: {staff_cnt} | Connection: {conn_sum} ta | Technician: {tech_sum} ta | Hammasi: {total_sum} ta",
        "ru": "— Всего сотрудников: {staff_cnt} | Подключение: {conn_sum} шт. | Техник: {tech_sum} шт. | Итого: {total_sum} шт.",
    },
    "conn": {"uz": "Connection", "ru": "Connection"},
    "tech": {"uz": "Technician", "ru": "Technician"},
    "active": {"uz": "Aktiv", "ru": "Активные"},
    "role_manager": {"uz": "Menejer", "ru": "Менеджер"},
    "role_jm": {"uz": "Kichik menejer", "ru": "Младший менеджер"},
    "empty": {
        "uz": "Ma'lumot topilmadi.",
        "ru": "Данные не найдены.",
    },
}

def _norm_lang(v: str | None) -> str:
    if not v:
        return "uz"
    v = v.strip().lower()
    if v in {"ru","rus","russian","ru-ru","ru_ru"}:
        return "ru"
    return "uz"

def _t(lang: str, key: str, **fmt) -> str:
    lang = _norm_lang(lang)
    s = T.get(key, {}).get(lang, T.get(key, {}).get("uz", key))
    return s.format(**fmt) if fmt else s

def _role_label(lang: str, role: str) -> str:
    role = (role or "").lower()
    if role == "junior_manager":
        return _t(lang, "role_jm")
    return _t(lang, "role_manager")

def _medal(i: int) -> str:
    return "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "•"))

def _build_report(lang: str, items: list[dict]) -> str:
    if not items:
        return _t(lang, "empty")

    # Umumiy yig'indilar
    conn_sum = sum(x.get("conn_count", 0) for x in items)
    tech_sum = sum(x.get("tech_count", 0) for x in items)
    total_sum = sum(x.get("total_orders", 0) for x in items)

    lines = [f"{_t(lang,'title')}\n", _t(lang, "legend"), ""]
    for i, it in enumerate(items):
        name = it.get("full_name") or "—"
        role = _role_label(lang, it.get("role"))
        conn_c = it.get("conn_count", 0)
        tech_c = it.get("tech_count", 0)
        active_c = it.get("active_count", 0)

        # Ko'rinish:
        # 1. 🥇 Ism Fam (Rol)
        #    ├ Connection: 7 ta
        #    ├ Technician: 4 ta
        #    └ Aktiv: 5 ta
        head = f"{i+1}. {_medal(i)} {name} ({role})"
        # birliklarni UZ: "ta" / RU: "шт."
        unit = "ta" if _norm_lang(lang) == "uz" else "шт."
        lines.append(head)
        lines.append(f"├ {_t(lang,'conn')}: {conn_c} {unit}")
        lines.append(f"├ {_t(lang,'tech')}: {tech_c} {unit}")
        lines.append(f"└ {_t(lang,'active')}: {active_c} {unit}")

    lines.append("")
    lines.append(_t(lang, "totals",
                    staff_cnt=len(items),
                    conn_sum=conn_sum,
                    tech_sum=tech_sum,
                    total_sum=total_sum))
    return "\n".join(lines)

async def _get_lang(user_tg_id: int) -> str:
    # users jadvalidan language olib, 'uz'/'ru' ga normalize qilamiz
    user = await get_user_by_telegram_id(user_tg_id)
    lng = (user or {}).get("language")
    return _norm_lang(lng)

# ---------------- ENTRY ----------------

UZ_ENTRY_TEXT = "👥 Xodimlar faoliyati"
RU_ENTRY_TEXT = "👥 Активность сотрудников"

@router.message(F.text.in_([UZ_ENTRY_TEXT, RU_ENTRY_TEXT]))
async def staff_activity_entry(message: Message, state: FSMContext):
    lang = await _get_lang(message.from_user.id)
    items = await fetch_staff_activity()
    text = _build_report(lang, items)

    # Telegram xabar uzunligi limitidan oshmasligi uchun bo'laklab yuboramiz
    # (odatda 4096, xavfsiz chegarani 3500 olamiz)
    CHUNK = 3500
    if len(text) <= CHUNK:
        await message.answer(text)
        return

    start = 0
    while start < len(text):
        await message.answer(text[start:start+CHUNK])
        start += CHUNK
