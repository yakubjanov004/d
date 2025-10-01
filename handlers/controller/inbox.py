from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime
import html

from database.controller_inbox import (
    get_user_by_telegram_id,
    get_users_by_role,
    get_callcenter_operators,          # ✅ YANGI: aniq operatorlar uchun (qulay)
    fetch_controller_inbox,
    assign_to_technician,
    fetch_controller_inbox_tech,
    assign_to_technician_for_tech,
    get_technicians_with_load_via_history,
    fetch_controller_inbox_staff,
    assign_to_technician_for_staff,
    assign_to_operator_for_tech,
)
from filters.role_filter import RoleFilter

router = Router()
router.message.filter(RoleFilter("controller"))
router.callback_query.filter(RoleFilter("controller"))

T = {
    "title": {"uz": "🎛️ <b>Controller Inbox</b>", "ru": "🎛️ <b>Входящие контроллера</b>"},
    "id": {"uz": "🆔 <b>ID:</b>", "ru": "🆔 <b>ID:</b>"},
    "tariff": {"uz": "📊 <b>Tarif:</b>", "ru": "📊 <b>Тариф:</b>"},
    "client": {"uz": "👤 <b>Mijoz:</b>", "ru": "👤 <b>Клиент:</b>"},
    "phone": {"uz": "📞 <b>Telefon:</b>", "ru": "📞 <b>Телефон:</b>"},
    "address": {"uz": "📍 <b>Manzil:</b>", "ru": "📍 <b>Адрес:</b>"},
    "created": {"uz": "📅 <b>Yaratilgan:</b>", "ru": "📅 <b>Создано:</b>"},
    "order_idx": {"uz": "🗂️ <i>Ariza {i} / {n}</i>", "ru": "🗂️ <i>Заявка {i} / {n}</i>"},
    "choose_cat": {"uz": "📂 Qaysi bo‘limni ko‘ramiz?", "ru": "📂 Какой раздел откроем?"},
    "empty_conn": {"uz": "📭 Ulanish arizalari bo'sh", "ru": "📭 Заявок на подключение нет"},
    "empty_tech": {"uz": "📭 Texnik xizmat arizalari bo'sh", "ru": "📭 Заявок на техобслуживание нет"},
    "empty_staff": {"uz": "📭 Xodimlar yuborgan arizalar bo'sh", "ru": "📭 Заявок от сотрудников нет"},
    "btn_prev": {"uz": "⬅️ Oldingi", "ru": "⬅️ Назад"},
    "btn_next": {"uz": "Keyingi ➡️", "ru": "Вперёд ➡️"},
    "btn_assign": {"uz": "🔧 Texnikga yuborish", "ru": "🔧 Отправить технику"},
    "btn_sections_back": {"uz": "🔙 Bo‘limlarga qaytish", "ru": "🔙 Назад к разделам"},
    "cat_conn": {"uz": "🔌 Ulanish uchun arizalar", "ru": "🔌 Заявки на подключение"},
    "cat_tech": {"uz": "🔧 Texnik xizmat arizalari", "ru": "🔧 Заявки на техобслуживание"},
    "cat_staff": {"uz": "👥 Xodimlar yuborgan arizalar", "ru": "👥 Заявки от сотрудников"},
    "tech_pick_title": {"uz": "🔧 <b>Texnik tanlang</b>", "ru": "🔧 <b>Выберите техника</b>"},
    "op_pick_title": {"uz": "☎️ <b>Operator tanlang</b>", "ru": "☎️ <b>Выберите оператора</b>"},
    "btn_op_section": {"uz": "— Operatorlar —", "ru": "— Операторы —"},
    "op_not_found": {"uz": "Operatorlar topilmadi", "ru": "Операторы не найдены"},
    "back": {"uz": "🔙 Orqaga", "ru": "🔙 Назад"},
    "no_techs": {"uz": "Texniklar topilmadi ❗", "ru": "Техники не найдены ❗"},
    "bad_format": {"uz": "❌ Noto'g'ri callback format", "ru": "❌ Неверный формат callback"},
    "no_user": {"uz": "❌ Foydalanuvchi topilmadi", "ru": "❌ Пользователь не найден"},
    "no_tech_one": {"uz": "❌ Texnik topilmadi", "ru": "❌ Техник не найден"},
    "error_generic": {"uz": "❌ Xatolik yuz berdi:", "ru": "❌ Произошла ошибка:"},
    "ok_assigned_title": {"uz": "✅ <b>Ariza muvaffaqiyatli yuborildi!</b>", "ru": "✅ <b>Заявка успешно отправлена!</b>"},
    "order_id": {"uz": "🆔 <b>Ariza ID:</b>", "ru": "🆔 <b>ID заявки:</b>"},
    "tech": {"uz": "🔧 <b>Texnik:</b>", "ru": "🔧 <b>Техник:</b>"},
    "op": {"uz": "☎️ <b>Operator:</b>", "ru": "☎️ <b>Оператор:</b>"},
    "sent_time": {"uz": "📅 <b>Yuborilgan vaqt:</b>", "ru": "📅 <b>Время отправки:</b>"},
    "sender": {"uz": "🎛️ <b>Yuboruvchi:</b>", "ru": "🎛️ <b>Отправитель:</b>"},
    "req_type": {"uz": "🧾 <b>Ariza turi:</b>", "ru": "🧾 <b>Тип заявки:</b>"},
    "creator": {"uz": "👷‍♂️ <b>Xodim:</b>", "ru": "👷‍♂️ <b>Сотрудник:</b>"},
    "creator_role": {"uz": "roli", "ru": "роль"},
    "desc": {"uz": "📝 <b>Izoh:</b>", "ru": "📝 <b>Описание:</b>"},
}

def normalize_lang(v: str | None) -> str:
    if not v:
        return "uz"
    v = v.strip().lower()
    if v in {"ru", "rus", "russian", "ru-ru", "ru_ru"}:
        return "ru"
    return "uz"

def t(lang: str, key: str, **fmt) -> str:
    lang = normalize_lang(lang)
    val = T.get(key, {}).get(lang) or T.get(key, {}).get("uz", key)
    return val.format(**fmt) if fmt else val

def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")

def esc(v) -> str:
    if v is None:
        return "-"
    return html.escape(str(v), quote=False)

def detect_lang_from_message(text: str) -> str:
    return "ru" if text and "Входящие" in text else "uz"

def short_view_text(item: dict, idx: int | None, total: int | None, lang: str) -> str:
    full_id = str(item.get("id"))
    parts = full_id.split("_")
    short_id = full_id if len(parts) < 2 else f"{parts[0]}-{parts[1]}"

    created = item.get("created_at")
    if isinstance(created, str):
        try:
            created_dt = datetime.fromisoformat(created)
        except ValueError:
            created_dt = datetime.now()
    elif isinstance(created, datetime):
        created_dt = created
    else:
        created_dt = datetime.now()

    tariff = esc(item.get("tariff", "-"))
    client_name = esc(item.get("client_name", "-"))
    client_phone = esc(item.get("client_phone", "-"))
    address = esc(item.get("address", "-"))
    short_id_safe = esc(short_id)

    base = (
        f"{t(lang,'title')}\n"
        f"{t(lang,'id')} {short_id_safe}\n"
        f"{t(lang,'tariff')} {tariff}\n"
        f"{t(lang,'client')} {client_name} ({client_phone})\n"
        f"{t(lang,'address')} {address}\n"
        f"{t(lang,'created')} {fmt_dt(created_dt)}"
    )

    req_type = item.get("req_type")
    staff_name = item.get("staff_name")
    staff_phone = item.get("staff_phone")
    staff_role = item.get("staff_role")
    desc = item.get("description")

    if req_type:
        base += f"\n{t(lang,'req_type')} {esc(req_type)}"
    if staff_name or staff_phone:
        role_part = f" ({esc(staff_role)})" if staff_role else ""
        staff_line = f"{t(lang,'creator')}{role_part}: {esc(staff_name) if staff_name else '-'}"
        if staff_phone:
            staff_line += f" ({esc(staff_phone)})"
        base += f"\n{staff_line}"
    if desc:
        base += f"\n{t(lang,'desc')} {esc(desc)}"

    if idx is not None and total is not None and total > 0:
        base += "\n\n" + t(lang, "order_idx", i=idx + 1, n=total)
    return base

async def build_assign_keyboard(full_id: str, lang: str, mode: str) -> InlineKeyboardMarkup:
    rows = []
    unit = "ta" if lang == "uz" else "шт."

    # texniklar
    technicians = await get_technicians_with_load_via_history(mode=("staff" if mode == "staff" else mode))
    for tech in (technicians or []):
        load = tech.get("load_count", 0) or 0
        title = f"🔧 {tech.get('full_name', '—')} • {load} {unit}"
        rows.append([InlineKeyboardButton(
            text=title, callback_data=f"ctrl_inbox_pick_{full_id}_{tech['id']}")])

    # operatorlar — faqat technician bo‘limida
    if mode == "technician":
        rows.append([InlineKeyboardButton(text=t(lang, "btn_op_section"), callback_data="noop")])

        # ✅ aniq funksiya orqali olayapmiz (ENUM cast muammosi yo‘q)
        operators = await get_callcenter_operators()
        if operators:
            for op in operators:
                rows.append([InlineKeyboardButton(
                    text=f"☎️ {op.get('full_name','—')}",
                    callback_data=f"ctrl_inbox_pickop_{full_id}_{op['id']}")])
        else:
            rows.append([InlineKeyboardButton(text=t(lang, "op_not_found"), callback_data="noop")])

    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data=f"ctrl_inbox_back_{full_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def nav_keyboard(index: int, total: int, current_id: str, lang: str) -> InlineKeyboardMarkup:
    rows = []
    if index > 0:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data=f"ctrl_inbox_prev_{index}")])

    row2 = [InlineKeyboardButton(text=t(lang, "btn_assign"), callback_data=f"ctrl_inbox_assign_{current_id}")]
    if index < total - 1:
        row2.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"ctrl_inbox_next_{index}"))
    rows.append(row2)

    rows.append([InlineKeyboardButton(text=t(lang, "btn_sections_back"), callback_data="ctrl_inbox_cat_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def category_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "cat_conn"), callback_data="ctrl_inbox_cat_connection")],
            [InlineKeyboardButton(text=t(lang, "cat_tech"), callback_data="ctrl_inbox_cat_tech")],
            [InlineKeyboardButton(text=t(lang, "cat_staff"), callback_data="ctrl_inbox_cat_staff")],
        ]
    )

@router.message(F.text.in_(["📥 Inbox", "📥 Входящие"]))
async def open_inbox(message: Message, state: FSMContext):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.get("role") != "controller":
        return
    lang = detect_lang_from_message(message.text)
    await state.update_data(lang=lang, inbox=[], idx=0, mode="connection")
    await message.answer(t(lang, "choose_cat"), reply_markup=category_keyboard(lang))

@router.callback_query(F.data == "ctrl_inbox_cat_connection")
async def cat_connection_flow(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    lang = normalize_lang(data.get("lang"))
    items = await fetch_controller_inbox(limit=50, offset=0)
    if not items:
        try:
            await cb.message.edit_text(t(lang, "empty_conn"), reply_markup=category_keyboard(lang))
        except TelegramBadRequest:
            pass
        return
    await state.update_data(mode="connection", inbox=items, idx=0)
    text = short_view_text(items[0], idx=0, total=len(items), lang=lang)
    kb = nav_keyboard(0, len(items), str(items[0]["id"]), lang)
    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "ctrl_inbox_cat_tech")
async def cat_tech_flow(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    lang = normalize_lang(data.get("lang"))
    items = await fetch_controller_inbox_tech(limit=50, offset=0)
    if not items:
        try:
            await cb.message.edit_text(t(lang, "empty_tech"), reply_markup=category_keyboard(lang))
        except TelegramBadRequest:
            pass
        return
    await state.update_data(mode="technician", inbox=items, idx=0)
    text = short_view_text(items[0], idx=0, total=len(items), lang=lang)
    kb = nav_keyboard(0, len(items), str(items[0]["id"]), lang)
    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "ctrl_inbox_cat_staff")
async def cat_staff_flow(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    lang = normalize_lang(data.get("lang"))
    items = await fetch_controller_inbox_staff(limit=50, offset=0)
    if not items:
        try:
            await cb.message.edit_text(t(lang, "empty_staff"), reply_markup=category_keyboard(lang))
        except TelegramBadRequest:
            pass
        return
    await state.update_data(mode="staff", inbox=items, idx=0)
    text = short_view_text(items[0], idx=0, total=len(items), lang=lang)
    kb = nav_keyboard(0, len(items), str(items[0]["id"]), lang)
    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("ctrl_inbox_prev_"))
async def prev_item(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    items = data.get("inbox", []) or []
    lang = normalize_lang(data.get("lang"))
    try:
        cur = int(cb.data.replace("ctrl_inbox_prev_", ""))
    except ValueError:
        return
    idx = max(0, min(cur - 1, len(items) - 1))
    if not items or idx < 0 or idx >= len(items):
        return
    await state.update_data(idx=idx)
    text = short_view_text(items[idx], idx=idx, total=len(items), lang=lang)
    kb = nav_keyboard(idx, len(items), str(items[idx]["id"]), lang)
    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("ctrl_inbox_next_"))
async def next_item(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    items = data.get("inbox", []) or []
    lang = normalize_lang(data.get("lang"))
    try:
        cur = int(cb.data.replace("ctrl_inbox_next_", ""))
    except ValueError:
        return
    idx = max(0, min(cur + 1, len(items) - 1))
    if not items or idx < 0 or idx >= len(items):
        return
    await state.update_data(idx=idx)
    text = short_view_text(items[idx], idx=idx, total=len(items), lang=lang)
    kb = nav_keyboard(idx, len(items), str(items[idx]["id"]), lang)
    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("ctrl_inbox_assign_"))
async def assign_open(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    full_id = cb.data.replace("ctrl_inbox_assign_", "")
    data = await state.get_data()
    lang = normalize_lang(data.get("lang"))
    mode = data.get("mode", "connection")

    kb = await build_assign_keyboard(full_id, lang, mode)
    text = f"{t(lang,'tech_pick_title')}\n🆔 {esc(full_id)}"
    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("ctrl_inbox_pick_"))
async def assign_pick(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = normalize_lang(data.get("lang"))
    items = data.get("inbox", []) or []

    try:
        raw = cb.data.replace("ctrl_inbox_pick_", "")
        full_id, tech_id_str = raw.rsplit("_", 1)
        tech_id = int(tech_id_str)
    except ValueError:
        await cb.answer(t(lang, "bad_format"), show_alert=True)
        return

    user = await get_user_by_telegram_id(cb.from_user.id)
    if not user:
        await cb.answer(t(lang, "no_user"), show_alert=True)
        return

    technicians = await get_users_by_role("technician")
    selected_tech = next((tech for tech in technicians if tech.get("id") == tech_id), None)
    if not selected_tech:
        await cb.answer(t(lang, "no_tech_one"), show_alert=True)
        return

    mode = data.get("mode", "connection")
    try:
        parts = full_id.split("_")
        request_id = int(parts[0]) if parts and parts[0].isdigit() else int(full_id)

        if mode == "staff":
            await assign_to_technician_for_staff(request_id=request_id, tech_id=tech_id, actor_id=user["id"])
        elif mode == "technician":
            await assign_to_technician_for_tech(request_id=request_id, tech_id=tech_id, actor_id=user["id"])
        else:
            await assign_to_technician(request_id=request_id, tech_id=tech_id, actor_id=user["id"])
    except Exception as e:
        await cb.answer(f"{t(lang,'error_generic')} {str(e)}", show_alert=True)
        return

    parts = full_id.split("_")
    short_id = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else full_id

    confirmation_text = (
        f"{t(lang,'ok_assigned_title')}\n\n"
        f"{t(lang,'order_id')} {esc(short_id)}\n"
        f"{t(lang,'tech')} {esc(selected_tech.get('full_name','—'))}\n"
        f"{t(lang,'sent_time')} {esc(fmt_dt(datetime.now()))}\n"
        f"{t(lang,'sender')} {esc(user.get('full_name', 'Controller'))}"
    )
    try:
        await cb.message.edit_text(confirmation_text, parse_mode="HTML")
    except TelegramBadRequest:
        pass

    items = [it for it in items if str(it.get("id")) != full_id]
    await state.update_data(inbox=items)
    await cb.answer()

@router.callback_query(F.data.startswith("ctrl_inbox_pickop_"))
async def assign_pick_operator(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = normalize_lang(data.get("lang"))
    mode = data.get("mode", "connection")
    items = data.get("inbox", []) or []

    try:
        raw = cb.data.replace("ctrl_inbox_pickop_", "")
        full_id, op_id_str = raw.rsplit("_", 1)
        operator_id = int(op_id_str)
    except ValueError:
        await cb.answer(t(lang, "bad_format"), show_alert=True)
        return

    if mode != "technician":
        await cb.answer("❗️ Operatorga biriktirish faqat Texnik arizalar bo‘limida mavjud.", show_alert=True)
        return

    user = await get_user_by_telegram_id(cb.from_user.id)
    if not user:
        await cb.answer(t(lang, "no_user"), show_alert=True)
        return

    # aniq operatorlar
    operators = await get_callcenter_operators()
    selected_op = next((op for op in operators if op.get("id") == operator_id), None)
    if not selected_op:
        await cb.answer("❌ Operator topilmadi", show_alert=True)
        return

    try:
        request_id = int(full_id.split("_")[0]) if "_" in full_id else int(full_id)
        await assign_to_operator_for_tech(request_id=request_id, operator_id=operator_id, actor_id=user["id"])
    except Exception as e:
        await cb.answer(f"{t(lang,'error_generic')} {str(e)}", show_alert=True)
        return

    short_id = f"{full_id.split('_')[0]}-{full_id.split('_')[1]}" if "_" in full_id else full_id
    confirmation_text = (
        f"{t(lang,'ok_assigned_title')}\n\n"
        f"{t(lang,'order_id')} {esc(short_id)}\n"
        f"{t(lang,'op')} {esc(selected_op.get('full_name','—'))}\n"
        f"{t(lang,'sent_time')} {esc(fmt_dt(datetime.now()))}\n"
        f"{t(lang,'sender')} {esc(user.get('full_name','Controller'))}"
    )
    try:
        await cb.message.edit_text(confirmation_text, parse_mode="HTML")
    except TelegramBadRequest:
        pass

    items = [it for it in items if str(it.get("id")) != full_id]
    await state.update_data(inbox=items)
    await cb.answer()

@router.callback_query(F.data == "ctrl_inbox_back_")
async def _legacy_back_guard(cb: CallbackQuery):
    await cb.answer()

@router.callback_query(F.data.startswith("ctrl_inbox_back_"))
async def assign_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    full_id = cb.data.replace("ctrl_inbox_back_", "")
    data = await state.get_data()
    items = data.get("inbox", []) or []
    lang = normalize_lang(data.get("lang"))
    idx = int(data.get("idx", 0))

    if not items:
        try:
            await cb.message.edit_text(t(lang, "choose_cat"), reply_markup=category_keyboard(lang))
        except TelegramBadRequest:
            pass
        return

    try:
        idx = next(i for i, it in enumerate(items) if str(it.get("id")) == full_id)
    except StopIteration:
        idx = max(0, min(idx, len(items) - 1))

    await state.update_data(idx=idx)
    current = items[idx]
    text = short_view_text(current, idx=idx, total=len(items), lang=lang)
    kb = nav_keyboard(idx, len(items), str(current.get("id")), lang)
    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "ctrl_inbox_cat_back")
async def cat_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    lang = normalize_lang(data.get("lang"))
    await state.update_data(inbox=[], idx=0)
    try:
        await cb.message.edit_text(t(lang, "choose_cat"), reply_markup=category_keyboard(lang))
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()
