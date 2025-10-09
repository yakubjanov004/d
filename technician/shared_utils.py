# handlers/technician/shared_utils.py
from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from database.basic.user import find_user_by_telegram_id
from loader import bot
import logging
import asyncpg
from config import settings
from datetime import datetime
import html

logger = logging.getLogger(__name__)

# =====================
# I18N
# =====================
T = {
    "title_inbox": {
        "uz": "👨‍🔧 <b>Texnik — Inbox</b>",
        "ru": "👨‍🔧 <b>Техник — Входящие</b>",
    },
    "id": {"uz": "🆔 <b>ID:</b>", "ru": "🆔 <b>ID:</b>"},
    "status": {"uz": "📌 <b>Status:</b>", "ru": "📌 <b>Статус:</b>"},
    "client": {"uz": "👤 <b>Mijoz:</b>", "ru": "👤 <b>Клиент:</b>"},
    "phone": {"uz": "📞 <b>Telefon:</b>", "ru": "📞 <b>Телефон:</b>"},
    "address": {"uz": "📍 <b>Manzil:</b>", "ru": "📍 <b>Адрес:</b>"},
    "tariff": {"uz": "📊 <b>Tarif:</b>", "ru": "📊 <b>Тариф:</b>"},
    "created": {"uz": "📅 <b>Yaratilgan:</b>", "ru": "📅 <b>Создано:</b>"},
    "desc": {"uz": "📝 <b>Tavsif:</b>", "ru": "📝 <b>Описание:</b>"},
    "jm_notes_label": {"uz": "📋 <b>JM izohi:</b>", "ru": "📋 <b>Примечание JM:</b>"},
    "media_yes": {"uz": "📎 <b>Media:</b> bor", "ru": "📎 <b>Медиа:</b> есть"},
    "pager": {"uz": "🗂️ <i>Ariza {i} / {n}</i>", "ru": "🗂️ <i>Заявка {i} / {n}</i>"},
    "staff_creator": {"uz": "👔 <b>Yaratuvchi:</b>", "ru": "👔 <b>Создатель:</b>"},
    "abonent": {"uz": "👤 <b>Abonent:</b>", "ru": "👤 <b>Абонент:</b>"},
    "req_type": {"uz": "📋 <b>Ariza turi:</b>", "ru": "📋 <b>Тип заявки:</b>"},
    "problem": {"uz": "⚠️ <b>Muammo:</b>", "ru": "⚠️ <b>Проблема:</b>"},
    "empty_connection": {"uz": "📭 Ulanish arizalari bo'sh", "ru": "📭 Заявок на подключение нет"},
    "empty_tech": {"uz": "📭 Texnik xizmat arizalari bo'sh", "ru": "📭 Заявок на техобслуживание нет"},
    "empty_staff": {"uz": "📭 Xodim arizalari bo'sh", "ru": "📭 Заявок от сотрудников нет"},
    "choose_section": {"uz": "📂 Qaysi bo'limni ko'ramiz?", "ru": "📂 Какой раздел откроем?"},
    "no_perm": {"uz": "❌ Ruxsat yo'q", "ru": "❌ Нет доступа"},
    "prev": {"uz": "⬅️ Oldingi", "ru": "⬅️ Предыдущая"},
    "next": {"uz": "Keyingi ➡️", "ru": "Следующая ➡️"},
    "cancel": {"uz": "🗑️ Bekor qilish", "ru": "🗑️ Отменить"},
    "accept": {"uz": "✅ Ishni qabul qilish", "ru": "✅ Принять работу"},
    "start": {"uz": "▶️ Ishni boshlash", "ru": "▶️ Начать работу"},
    "diagnostics": {"uz": "🩺 Diagnostika", "ru": "🩺 Диагностика"},
    "finish": {"uz": "✅ Yakunlash", "ru": "✅ Завершить"},
    "warehouse": {"uz": "📦 Ombor", "ru": "📦 Склад"},
    "review": {"uz": "📋 Yakuniy ko'rinish", "ru": "📋 Итоговый вид"},
    "reached_start": {"uz": "❗️ Boshlanishga yetib keldingiz.", "ru": "❗️ Достигли начала списка."},
    "reached_end": {"uz": "❗️ Oxiriga yetib keldingiz.", "ru": "❗️ Достигли конца списка."},
    "ok_started": {"uz": "✅ Ish boshlandi", "ru": "✅ Работа начата"},
    "ok_cancelled": {"uz": "🗑️ Ariza bekor qilindi", "ru": "🗑️ Заявка отменена"},
    "empty_inbox": {"uz": "📭 Inbox bo'sh", "ru": "📭 Входящие пусты"},
    "format_err": {"uz": "❌ Xato format", "ru": "❌ Неверный формат"},
    "not_found_mat": {"uz": "❌ Material topilmadi", "ru": "❌ Материал не найден"},
    "enter_qty": {"uz": "📦 <b>Miqdorni kiriting</b>", "ru": "📦 <b>Введите количество</b>"},
    "order_id": {"uz": "🆔 <b>Ariza ID:</b>", "ru": "🆔 <b>ID заявки:</b>"},
    "chosen_prod": {"uz": "📦 <b>Tanlangan mahsulot:</b>", "ru": "📦 <b>Выбранный товар:</b>"},
    "price": {"uz": "💰 <b>Narx:</b>", "ru": "💰 <b>Цена:</b>"},
    "assigned_left": {"uz": "📊 <b>Sizga biriktirilgan qoldiq:</b>", "ru": "📊 <b>Ваш закреплённый остаток:</b>"},
    "enter_qty_hint": {
        "uz": "📝 Iltimos, olinadigan miqdorni kiriting:\n• Faqat raqam (masalan: 2)\n\n<i>Maksimal: {max} dona</i>",
        "ru": "📝 Введите количество:\n• Только число (например: 2)\n\n<i>Максимум: {max} шт</i>",
    },
    "btn_cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена"},
    "only_int": {"uz": "❗️ Faqat butun son kiriting (masalan: 2).", "ru": "❗️ Введите целое число (например: 2)."},
    "gt_zero": {"uz": "❗️ Iltimos, 0 dan katta butun son kiriting.", "ru": "❗️ Введите целое число больше 0."},
    "max_exceeded": {
        "uz": "❗️ Sizga biriktirilgan miqdor: {max} dona. {max} dan oshiq kiritib bo'lmaydi.",
        "ru": "❗️ Ваш лимит: {max} шт. Нельзя вводить больше {max}.",
    },
    "saved_selection": {"uz": "✅ <b>Tanlov saqlandi</b>", "ru": "✅ <b>Выбор сохранён</b>"},
    "selected_products": {"uz": "📦 <b>Tanlangan mahsulotlar:</b>", "ru": "📦 <b>Выбранные материалы:</b>"},
    "add_more": {"uz": "➕ Yana material tanlash", "ru": "➕ Добавить ещё материал"},
    "final_view": {"uz": "📋 Yakuniy ko'rinish", "ru": "📋 Итоговый вид"},
    "store_header": {
        "uz": "📦 <b>Ombor jihozlari</b>\n🆔 <b>Ariza ID:</b> {id}\nKerakli jihozlarni tanlang yoki boshqa mahsulot kiriting:",
        "ru": "📦 <b>Складские позиции</b>\n🆔 <b>ID заявки:</b> {id}\nВыберите нужное или введите другой товар:",
    },
    "diag_begin_prompt": {
        "uz": "🩺 <b>Diagnostika matnini kiriting</b>\n\nMasalan: <i>Modem moslamasi ishdan chiqqan</i>.",
        "ru": "🩺 <b>Введите текст диагностики</b>\n\nНапример: <i>Неисправен модем</i>.",
    },
    "diag_saved": {"uz": "✅ <b>Diagnostika qo'yildi!</b>", "ru": "✅ <b>Диагностика сохранена!</b>"},
    "diag_text": {"uz": "🧰 <b>Diagnostika:</b>", "ru": "🧰 <b>Диагностика:</b>"},
    "go_store_q": {
        "uz": "🧑‍🏭 <b>Ombor bilan ishlaysizmi?</b>\n<i>Agar kerakli jihozlar omborda bo'lsa, ularni olish kerak.</i>",
        "ru": "🧑‍🏭 <b>Перейти к складу?</b>\n<i>Если нужны материалы — забираем со склада.</i>",
    },
    "yes": {"uz": "✅ Ha", "ru": "✅ Да"},
    "no": {"uz": "❌ Yo'q", "ru": "❌ Нет"},
    "diag_cancelled": {"uz": "ℹ️ Omborga murojaat qilinmadi. Davom etishingiz mumkin.", "ru": "ℹ️ К складу не обращались. Можно продолжать."},
    "catalog_empty": {"uz": "📦 Katalog bo'sh.", "ru": "📦 Каталог пуст."},
    "catalog_header": {"uz": "📦 <b>Mahsulot katalogi</b>\nKeraklisini tanlang:", "ru": "📦 <b>Каталог материалов</b>\nВыберите нужное:"},
    "back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "qty_title": {"uz": "✍️ <b>Miqdorni kiriting</b>", "ru": "✍️ <b>Введите количество</b>"},
    "order": {"uz": "🆔 Ariza:", "ru": "🆔 Заявка:"},
    "product": {"uz": "📦 Mahsulot:", "ru": "📦 Материал:"},
    "price_line": {"uz": "💰 Narx:", "ru": "💰 Цена:"},
    "ctx_lost": {"uz": "❗️ Kontekst yo'qolgan, qaytadan urinib ko'ring.", "ru": "❗️ Контекст потерян, попробуйте снова."},
    "req_not_found": {"uz": "❗️ Ariza aniqlanmadi.", "ru": "❗️ Заявка не найдена."},
    "x_error": {"uz": "❌ Xatolik:", "ru": "❌ Ошибка:"},
    "state_cleared": {"uz": "Bekor qilindi", "ru": "Отменено"},
    "status_mismatch": {"uz": "⚠️ Holat mos emas", "ru": "⚠️ Некорректный статус"},
    "status_mismatch_detail": {
        "uz": "⚠️ Holat mos emas (faqat 'in_technician').",
        "ru": "⚠️ Некорректный статус (только 'in_technician').",
    },
    "status_mismatch_finish": {
        "uz": "⚠️ Holat mos emas (faqat 'in_technician_work').",
        "ru": "⚠️ Некорректный статус (только 'in_technician_work').",
    },
    "work_finished": {"uz": "✅ <b>Ish yakunlandi</b>", "ru": "✅ <b>Работа завершена</b>"},
    "used_materials": {"uz": "📦 <b>Ishlatilgan mahsulotlar:</b>", "ru": "📦 <b>Использованные материалы:</b>"},
    "none": {"uz": "• (mahsulot tanlanmadi)", "ru": "• (материалы не выбраны)"},
    "akt_err_ignored": {"uz": "AKT xatoligi ishni to'xtatmaydi", "ru": "Ошибка АКТ не останавливает процесс"},
    "store_request_sent": {
        "uz": "📨 <b>Omborga so'rov yuborildi</b>",
        "ru": "📨 <b>Заявка на склад отправлена</b>",
    },
    "req_type_info": {
        "uz": "⏳ Ariza holati endi <b>in_warehouse</b>. Omborchi tasdiqlagach yana <b>in_technician_work</b> bo'ladi.",
        "ru": "⏳ Статус теперь <b>in_warehouse</b>. После подтверждения склада вернётся в <b>in_technician_work</b>.",
    },
    "sections_keyboard": {
        "uz": ["🔌 Ulanish arizalari", "🔧 Texnik xizmat arizalari", "📞 Operator arizalari"],
        "ru": ["🔌 Заявки на подключение", "🔧 Заявки на техобслуживание", "📞 Заявки от операторов"],
    },
}

def t(key: str, lang: str = "uz", **kwargs) -> str:
    val = T.get(key, {}).get(lang, "")
    return val.format(**kwargs) if kwargs else val

async def resolve_lang(user_id: int, fallback: str = "uz") -> str:
    """Foydalanuvchi tilini DB'dan olish: users.lang ('uz'|'ru') bo'lsa ishlatiladi."""
    try:
        u = await find_user_by_telegram_id(user_id)
        if u:
            lang = (u.get("lang") or u.get("user_lang") or u.get("language") or "").lower()
            if lang in ("uz", "ru"):
                return lang
    except Exception:
        pass
    return fallback

# =====================
# Helperlar
# =====================
def _preserve_mode_clear(state: FSMContext, keep_keys: list[str] | None = None):
    async def _inner():
        data = await state.get_data()
        mode = data.get("tech_mode")
        kept: dict = {}
        if keep_keys:
            for k in keep_keys:
                if k in data:
                    kept[k] = data[k]
        await state.clear()
        payload = {"tech_mode": mode}
        payload.update(kept)
        await state.update_data(**payload)
    return _inner()

def fmt_dt(dt) -> str:
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return html.escape(dt, quote=False)
    if isinstance(dt, datetime):
        return dt.strftime("%d.%m.%Y %H:%M")
    return "-"

def esc(v) -> str:
    return "-" if v is None else html.escape(str(v), quote=False)

def _qty_of(it: dict) -> str:
    q = it.get('qty')
    if q is None:
        q = it.get('quantity', it.get('description'))
    return str(q) if q is not None else "-"

def status_emoji(s: str) -> str:
    m = {
        "between_controller_technician": "🆕",
        "in_technician": "🧰",
        "in_technician_work": "🟢",
        "in_warehouse": "📦",
        "completed": "✅",
    }
    return m.get(s, "📌")

def _short(s: str, n: int = 48) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"

def _fmt_price_uzs(val) -> str:
    try:
        s = f"{int(val):,}"
        return s.replace(",", " ")
    except Exception:
        return str(val)

def _dedup_by_id(items: list[dict]) -> list[dict]:
    seen = set(); out = []
    for it in items:
        i = it.get("id")
        if i in seen: continue
        seen.add(i); out.append(it)
    return out

# =====================
# Text Formatting
# =====================
def short_view_text(item: dict, idx: int, total: int, lang: str = "uz", mode: str = "connection") -> str:
    """Build ariza text based on mode"""
    
    # Staff arizalari uchun alohida text
    if mode == "staff":
        base = f"{t('title_inbox', lang)}\n"
        base += f"{t('id', lang)} {esc(item.get('application_number') or item.get('id'))}\n"
        base += f"{status_emoji(item.get('status',''))} {t('status', lang)} {esc(item.get('status'))}\n"
        
        # Ariza turi
        req_type = item.get('type_of_zayavka', '-')
        req_type_uz = "Ulanish" if req_type == "connection" else ("Texnik xizmat" if req_type == "technician" else req_type)
        req_type_ru = "Подключение" if req_type == "connection" else ("Техобслуживание" if req_type == "technician" else req_type)
        base += f"{t('req_type', lang)} {req_type_uz if lang=='uz' else req_type_ru}\n\n"
        
        # Abonent (mijoz) ma'lumotlari
        base += f"{t('abonent', lang)}\n"
        base += f"  • {esc(item.get('client_name'))}\n"
        base += f"  • {esc(item.get('client_phone'))}\n\n"
        
        # Yaratuvchi xodim
        base += f"{t('staff_creator', lang)}\n"
        creator_role = item.get('staff_creator_role', '-')
        base += f"  • {esc(item.get('staff_creator_name'))} ({esc(creator_role)})\n"
        base += f"  • {esc(item.get('staff_creator_phone'))}\n\n"
        
        # Manzil
        base += f"{t('address', lang)} {esc(item.get('address'))}\n"
        
        # Tariff yoki muammo
        tariff_or_problem = item.get('tariff_or_problem')
        if tariff_or_problem:
            if req_type == 'connection':
                base += f"{t('tariff', lang)} {esc(tariff_or_problem)}\n"
            else:
                base += f"{t('problem', lang)} {esc(tariff_or_problem)}\n"
        
        # Tavsif
        desc = (item.get("description") or "").strip()
        if desc:
            short_desc = (desc[:140] + "…") if len(desc) > 140 else desc
            base += f"{t('desc', lang)} {html.escape(short_desc, quote=False)}\n"
        
        # JM notes
        jm_notes = (item.get("jm_notes") or "").strip()
        if jm_notes:
            short_notes = (jm_notes[:100] + "…") if len(jm_notes) > 100 else jm_notes
            base += f"{t('jm_notes_label', lang)} {html.escape(short_notes, quote=False)}\n"
        
        if item.get("created_at"):
            base += f"{t('created', lang)} {fmt_dt(item.get('created_at'))}\n"
        
        base += "\n" + t("pager", lang, i=idx + 1, n=total)
        return base
    
    # Connection va technician arizalari uchun
    base = (
        f"{t('title_inbox', lang)}\n"
        f"{t('id', lang)} {esc(item.get('application_number') or item.get('id'))}\n"
        f"{t('client', lang)} {esc(item.get('client_name'))}\n"
        f"{t('phone', lang)} {esc(item.get('client_phone'))}\n"
        f"{t('address', lang)} {esc(item.get('address'))}\n"
    )
    
    if item.get("tariff"):
        base += f"{t('tariff', lang)} {esc(item.get('tariff'))}\n"
    
    # JM notes (faqat connection uchun)
    if mode == "connection":
        jm_notes = (item.get("jm_notes") or "").strip()
        if jm_notes:
            short_notes = (jm_notes[:100] + "…") if len(jm_notes) > 100 else jm_notes
            base += f"{t('jm_notes_label', lang)} {html.escape(short_notes, quote=False)}\n"
    
    if item.get("created_at"):
        base += f"{t('created', lang)} {fmt_dt(item.get('created_at'))}\n"
    
    desc = (item.get("description") or "").strip()
    if desc:
        short_desc = (desc[:140] + "…") if len(desc) > 140 else desc
        base += f"{t('desc', lang)} {html.escape(short_desc, quote=False)}\n"
    
    base += "\n" + t("pager", lang, i=idx + 1, n=total)
    return base

async def get_selected_materials_summary(user_id: int, req_id: int, lang: str) -> str:
    """Get summary of selected materials for display in inbox"""
    try:
        from database.technician.materials import fetch_selected_materials_for_request
        selected = await fetch_selected_materials_for_request(user_id, req_id)
        if not selected:
            return ""
        
        summary = "\n\n📦 <b>Tanlangan mahsulotlar:</b>\n"
        for mat in selected:
            qty = mat['qty']
            name = mat['name']
            source = "🧑‍🔧 O'zimda" if mat.get('source_type') == 'technician_stock' else "🏢 Ombordan"
            summary += f"• {esc(name)} — {qty} dona [{source}]\n"
        return summary
    except Exception:
        return ""

async def short_view_text_with_materials(item: dict, idx: int, total: int, user_id: int, lang: str = "uz", mode: str = "connection") -> str:
    """Build ariza text with selected materials included"""
    base_text = short_view_text(item, idx, total, lang, mode)
    
    # Add selected materials if any
    req_id = item.get("id")
    if req_id:
        materials_summary = await get_selected_materials_summary(user_id, req_id, lang)
        if materials_summary:
            # Insert materials before pager
            pager_start = base_text.rfind(t("pager", lang, i=idx + 1, n=total))
            if pager_start != -1:
                base_text = base_text[:pager_start] + materials_summary + "\n" + base_text[pager_start:]
            else:
                base_text += materials_summary
    
    return base_text

# =====================
# Render Functions
# =====================
async def _safe_edit(message, text: str, kb: InlineKeyboardMarkup):
    try:
        if message.text == text:
            try:
                await message.edit_reply_markup(reply_markup=kb)
                return
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    return
                raise
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        raise

async def render_item(message, item: dict, idx: int, total: int, lang: str, mode: str, user_id: int = None):
    """Arizani rasm bilan yoki rasmsiz ko'rsatish"""
    if user_id:
        text = await short_view_text_with_materials(item, idx, total, user_id, lang, mode)
    else:
        text = short_view_text(item, idx, total, lang, mode)
    
    from .shared_utils import action_keyboard
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    
    media_file_id = item.get("media_file_id")
    media_type = item.get("media_type")
    
    try:
        # Eski xabarni o'chirish (inline tugmalar qolmasligi uchun)
        try:
            await message.delete()
        except:
            pass
        
        # Yangi xabar yuborish
        if media_file_id and media_type:
            try:
                if media_type == 'photo':
                    await bot.send_photo(
                        chat_id=message.chat.id,
                        photo=media_file_id,
                        caption=text,
                        parse_mode='HTML',
                        reply_markup=kb
                    )
                elif media_type == 'video':
                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=media_file_id,
                        caption=text,
                        parse_mode='HTML',
                        reply_markup=kb
                    )
                else:
                    await bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=kb)
            except Exception:
                # Agar media yuborishda xatolik bo'lsa, faqat matn yuboramiz
                await bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=kb)
        else:
            await bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=kb)
    except Exception:
        # Agar delete ishlamasa ham, matn yuborishga harakat qilamiz
        try:
            await bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=kb)
        except:
            pass

# =====================
# Keyboard Generators
# =====================
def tech_category_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    a, b, c = T["sections_keyboard"][lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data="tech_inbox_cat_connection")],
        [InlineKeyboardButton(text=b, callback_data="tech_inbox_cat_tech")],
        [InlineKeyboardButton(text=c, callback_data="tech_inbox_cat_operator")],
    ])

def action_keyboard(item_id: int, index: int, total: int, status: str, mode: str = "connection", lang: str = "uz") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if total > 1:
        nav = []
        if index > 0:
            nav.append(InlineKeyboardButton(text=t("prev", lang), callback_data=f"tech_inbox_prev_{index}"))
        if index < total - 1:
            nav.append(InlineKeyboardButton(text=t("next", lang), callback_data=f"tech_inbox_next_{index}"))
        if nav:
            rows.append(nav)
    if status == "between_controller_technician":
        rows.append([
            InlineKeyboardButton(text=t("cancel", lang), callback_data=f"tech_cancel_{item_id}"),
            InlineKeyboardButton(text=t("accept", lang), callback_data=f"tech_accept_{item_id}"),
        ])
    elif status == "in_technician":
        rows.append([InlineKeyboardButton(text=t("start", lang), callback_data=f"tech_start_{item_id}")])
    elif status == "in_technician_work":
        if mode == "technician":
            rows.append([InlineKeyboardButton(text=t("diagnostics", lang), callback_data=f"tech_diag_begin_{item_id}")])
            rows.append([InlineKeyboardButton(text=t("finish", lang), callback_data=f"tech_finish_{item_id}")])
        else:
            rows.append([
                InlineKeyboardButton(text=t("warehouse", lang), callback_data=f"tech_add_more_{item_id}"),
                InlineKeyboardButton(text=t("review", lang), callback_data=f"tech_review_{item_id}"),
            ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# =====================
# Notification Functions
# =====================
async def send_completion_notification_to_client(bot, request_id: int, request_type: str):
    """
    Texnik ishni yakunlagandan so'ng clientga ariza haqida to'liq ma'lumot yuborish va rating so'rash.
    AKT yuborilmaydi - faqat ma'lumot va rating tizimi.
    """
    try:
        # Client ma'lumotlarini olish
        client_data = await get_client_data_for_notification(request_id, request_type)
        if not client_data or not client_data.get('client_telegram_id'):
            logger.warning(f"No client data found for {request_type} request {request_id}")
            return

        client_telegram_id = client_data['client_telegram_id']
        client_lang = client_data.get('client_lang', 'uz')
        
        # Ariza turini til bo'yicha formatlash
        if client_lang == "ru":
            if request_type == "connection":
                order_type_text = "подключения"
            elif request_type == "technician":
                order_type_text = "технической"
            else:
                order_type_text = "сотрудника"
        else:
            if request_type == "connection":
                order_type_text = "ulanish"
            elif request_type == "technician":
                order_type_text = "texnik xizmat"
            else:
                order_type_text = "xodim"

        # Ishlatilgan materiallarni olish
        materials_info = await get_used_materials_info(request_id, request_type, client_lang)
        
        # Diagnostika ma'lumotini olish (texnik xizmat uchun)
        diagnosis_info = await get_diagnosis_info(request_id, request_type, client_lang)

        # Notification matnini tayyorlash
        if client_lang == "ru":
            message = (
                "✅ <b>Работа завершена!</b>\n\n"
                f"📋 Заявка {order_type_text}: #{request_id}\n"
                f"📅 Дата завершения: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            )
            
            if diagnosis_info:
                message += f"🔧 <b>Выполненные работы:</b>\n{diagnosis_info}\n\n"
            
            if materials_info:
                message += f"📦 <b>Использованные материалы:</b>\n{materials_info}\n\n"
            
            message += "<i>Пожалуйста, оцените качество нашей работы:</i>"
        else:
            message = (
                "✅ <b>Ish yakunlandi!</b>\n\n"
                f"📋 {order_type_text} arizasi: #{request_id}\n"
                f"📅 Yakunlangan sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            )
            
            if diagnosis_info:
                message += f"🔧 <b>Bajarilgan ishlar:</b>\n{diagnosis_info}\n\n"
            
            if materials_info:
                message += f"📦 <b>Ishlatilgan materiallar:</b>\n{materials_info}\n\n"
            
            message += "<i>Iltimos, xizmatimizni baholang:</i>"

        # Rating keyboard yaratish
        from keyboards.client_buttons import get_rating_keyboard
        rating_keyboard = get_rating_keyboard(request_id, request_type)
        
        # Xabarni yuborish
        await bot.send_message(
            chat_id=client_telegram_id,
            text=message,
            parse_mode='HTML',
            reply_markup=rating_keyboard
        )
        
        logger.info(f"Completion notification sent to client {client_telegram_id} for {request_type} request {request_id}")
        
    except Exception as e:
        logger.error(f"Error sending completion notification to client: {e}")
        raise

async def get_client_data_for_notification(request_id: int, request_type: str):
    """
    Client ma'lumotlarini olish notification uchun.
    """
    from database.connections import get_connection_url
    import asyncpg
    
    try:
        conn = await asyncpg.connect(get_connection_url())
        try:
            if request_type == "connection":
                query = """
                    SELECT 
                        co.client_telegram_id,
                        u.lang as client_lang,
                        co.client_name,
                        co.client_phone,
                        co.address
                    FROM connection_orders co
                    LEFT JOIN users u ON u.telegram_id = co.client_telegram_id
                    WHERE co.id = $1
                """
            elif request_type == "technician":
                query = """
                    SELECT 
                        to.client_telegram_id,
                        u.lang as client_lang,
                        to.client_name,
                        to.client_phone,
                        to.address
                    FROM technician_orders to
                    LEFT JOIN users u ON u.telegram_id = to.client_telegram_id
                    WHERE to.id = $1
                """
            elif request_type == "staff":
                query = """
                    SELECT 
                        so.client_telegram_id,
                        u.lang as client_lang,
                        so.client_name,
                        so.client_phone,
                        so.address
                    FROM staff_orders so
                    LEFT JOIN users u ON u.telegram_id = so.client_telegram_id
                    WHERE so.id = $1
                """
            else:
                return None
                
            result = await conn.fetchrow(query, request_id)
            return dict(result) if result else None
            
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error getting client data: {e}")
        return None

async def get_used_materials_info(request_id: int, request_type: str, client_lang: str = "uz"):
    """
    Ishlatilgan materiallar haqida ma'lumot olish.
    """
    try:
        from database.connections import get_connection_url
        import asyncpg
        
        conn = await asyncpg.connect(get_connection_url())
        try:
            if request_type == "connection":
                query = """
                    SELECT 
                        m.name as material_name,
                        mr.quantity,
                        mr.price
                    FROM material_requests mr
                    JOIN materials m ON m.id = mr.material_id
                    WHERE mr.applications_id = $1
                    ORDER BY mr.created_at
                """
            elif request_type == "technician":
                query = """
                    SELECT 
                        m.name as material_name,
                        mr.quantity,
                        mr.price
                    FROM material_requests mr
                    JOIN materials m ON m.id = mr.material_id
                    WHERE mr.applications_id = $1
                    ORDER BY mr.created_at
                """
            elif request_type == "staff":
                query = """
                    SELECT 
                        m.name as material_name,
                        mr.quantity,
                        mr.price
                    FROM material_requests mr
                    JOIN materials m ON m.id = mr.material_id
                    WHERE mr.applications_id = $1
                    ORDER BY mr.created_at
                """
            else:
                return ""
                
            materials = await conn.fetch(query, request_id)
            
            if not materials:
                return "• Hech qanday material ishlatilmagan" if client_lang == "uz" else "• Материалы не использовались"
            
            materials_text = []
            for mat in materials:
                name = mat['material_name'] or "Noma'lum"
                qty = mat['quantity'] or 0
                price = mat['price'] or 0
                total_price = qty * price
                
                if client_lang == "ru":
                    materials_text.append(f"• {name} — {qty} шт. (💰 {_fmt_price_uzs(total_price)} сум)")
                else:
                    materials_text.append(f"• {name} — {qty} dona (💰 {_fmt_price_uzs(total_price)} so'm)")
            
            return "\n".join(materials_text)
            
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error getting materials info: {e}")
        return ""

async def get_diagnosis_info(request_id: int, request_type: str, client_lang: str = "uz"):
    """
    Diagnostika ma'lumotini olish (faqat texnik xizmat uchun).
    """
    try:
        if request_type != "technician":
            return ""
            
        from database.connections import get_connection_url
        import asyncpg
        
        conn = await asyncpg.connect(get_connection_url())
        try:
            query = """
                SELECT description
                FROM technician_orders
                WHERE id = $1 AND description IS NOT NULL
            """
            
            result = await conn.fetchval(query, request_id)
            
            if not result:
                return ""
            
            # Diagnostika matnini qisqartirish
            diagnosis = result.strip()
            if len(diagnosis) > 200:
                diagnosis = diagnosis[:200] + "..."
            
            return diagnosis
            
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error getting diagnosis info: {e}")
        return ""

# =====================
# DB Helper Functions
# =====================
async def get_current_status(application_id: int, mode: str = "connection") -> str:
    """Get current status of an application"""
    from database.technician.materials import _conn
    conn = None
    try:
        conn = await _conn()
        if mode == "technician":
            query = """
                SELECT status FROM technician_orders 
                WHERE id = $1
            """
        else:  # connection mode
            query = """
                SELECT status FROM connection_orders 
                WHERE id = $1
            """
        result = await conn.fetchval(query, application_id)
        return result or "noma'lum"
    except Exception as e:
        print(f"Error getting status: {e}")
        return "noma'lum"
    finally:
        if conn:
            await conn.close()

async def get_application_number(application_id: int, mode: str = "connection") -> str:
    """Get application_number from database"""
    from database.technician.materials import _conn
    conn = None
    try:
        conn = await _conn()
        if mode == "technician":
            query = """
                SELECT application_number FROM technician_orders 
                WHERE id = $1
            """
        elif mode == "staff":
            query = """
                SELECT application_number FROM staff_orders 
                WHERE id = $1
            """
        else:  # connection mode
            query = """
                SELECT application_number FROM connection_orders 
                WHERE id = $1
            """
        result = await conn.fetchval(query, application_id)
        return result or str(application_id)
    except Exception as e:
        print(f"Error getting application_number: {e}")
        return str(application_id)
    finally:
        if conn:
            await conn.close()
