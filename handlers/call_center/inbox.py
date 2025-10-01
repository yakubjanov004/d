from typing import Dict, Any, List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from filters.role_filter import RoleFilter

from database.call_center_inbox_queries import (
    get_operator_orders,          # mavjud query: o'zgartirilmagan
    update_order_status,
    add_order_comment,
    get_any_controller_id,        # controller id olish (users.id)
    log_connection_from_operator, # controllerga yuborilganda log
    get_user_id_by_telegram_id,   # telegram_id -> users.id
    log_connection_completed_from_operator,  # ✅ YANGI: yopilganda log (pastda kodini beraman)
)

# === Router ===
router = Router()
router.message.filter(RoleFilter("callcenter_operator"))
router.callback_query.filter(RoleFilter("callcenter_operator"))

# === States (string-based, loyihangga mos) ===
class InboxStates:
    browsing = "inbox_browsing"
    adding_comment = "inbox_comment"


# === Helper: Order text ===
def get_order_text(order: dict, lang: str = "uz",
                   idx: int | None = None, total: int | None = None) -> str:
    comments = (order.get("comments") or order.get("description_operator") or "").strip()

    if lang == "uz":
        base = (f"🆔 <b>Ariza raqami:</b> {order['id']}\n"
                f"📍 <b>Region:</b> {order['region']}\n"
                f"🏠 <b>Manzil:</b> {order['address']}\n"
                f"📝 <b>Tavsif:</b> {order['description']}")
        if comments:
            base += f"\n💬 <b>Izohlar:</b> {comments}"
    else:
        base = (f"🆔 <b>Номер заявки:</b> {order['id']}\n"
                f"📍 <b>Регион:</b> {order['region']}\n"
                f"🏠 <b>Адрес:</b> {order['address']}\n"
                f"📝 <b>Описание:</b> {order['description']}")
        if comments:
            base += f"\n💬 <b>Комментарии:</b> {comments}"

    if idx is not None and total is not None:
        base += (
            f"\n\n🗂️ <i>Ariza {idx + 1} / {total}</i>"
            if lang == "uz"
            else f"\n\n🗂️ <i>Заявка {idx + 1} / {total}</i>"
        )
    return base


# === Helper: Buttons ===
def get_inbox_controls(order_id: int, lang: str = "uz",
                       idx: int = 0, total: int = 1) -> InlineKeyboardMarkup:
    buttons: List[List[InlineKeyboardButton]] = []

    # ⬅️/➡️ navigatsiya
    nav_row: List[InlineKeyboardButton] = []
    if total > 1:
        if idx > 0:
            nav_row.append(InlineKeyboardButton(
                text="⬅️ Oldingisi" if lang == "uz" else "⬅️ Предыдущая",
                callback_data=f"inbox_prev:{order_id}"
            ))
        if idx < total - 1:
            nav_row.append(InlineKeyboardButton(
                text="➡️ Keyingisi" if lang == "uz" else "➡️ Следующая",
                callback_data=f"inbox_next:{order_id}"
            ))
    if nav_row:
        buttons.append(nav_row)

    # ✍️ Izoh
    buttons.append([InlineKeyboardButton(
        text="✍️ Izoh qo‘shish" if lang == "uz" else "✍️ Добавить комментарий",
        callback_data=f"inbox_comment:{order_id}"
    )])

    # 📤 Controllerga yuborish
    buttons.append([InlineKeyboardButton(
        text="📤 Controllerga yuborish" if lang == "uz" else "📤 Отправить контроллеру",
        callback_data=f"inbox_send_control:{order_id}"
    )])

    # ✅ Arizani yopish
    buttons.append([InlineKeyboardButton(
        text="✅ Arizani yopish" if lang == "uz" else "✅ Закрыть заявку",
        callback_data=f"inbox_close:{order_id}"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# === Start Inbox ===
@router.message(F.text.in_(["📥 Inbox", "📥 Входящие"]))
async def inbox_start(message: Message, state: FSMContext):
    operator_id = message.from_user.id
    lang = "uz" if message.text == "📥 Inbox" else "ru"

    orders = await get_operator_orders(operator_id)

    if not orders:
        await message.answer("📭 Arizalar yo‘q" if lang == "uz" else "📭 Заявок нет")
        return

    await state.update_data(orders=orders, index=0, lang=lang)
    order = orders[0]
    text = get_order_text(order, lang, idx=0, total=len(orders))
    await message.answer(
        text,
        reply_markup=get_inbox_controls(order["id"], lang, idx=0, total=len(orders)),
        parse_mode="HTML",
    )
    await state.set_state(InboxStates.browsing)


# === Navigatsiya: Oldingisi ===
@router.callback_query(F.data.startswith("inbox_prev"))
async def inbox_prev(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    orders: List[Dict[str, Any]] = data["orders"]
    index: int = data["index"]
    lang: str = data["lang"]

    if index > 0:
        index -= 1
        await state.update_data(index=index)

    index = max(0, min(index, len(orders) - 1))
    order = orders[index]
    text = get_order_text(order, lang, idx=index, total=len(orders))
    await cq.message.edit_text(
        text,
        reply_markup=get_inbox_controls(order["id"], lang, idx=index, total=len(orders)),
        parse_mode="HTML",
    )
    await cq.answer()


# === Navigatsiya: Keyingisi ===
@router.callback_query(F.data.startswith("inbox_next"))
async def inbox_next(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    orders: List[Dict[str, Any]] = data["orders"]
    index: int = data["index"]
    lang: str = data["lang"]

    if index < len(orders) - 1:
        index += 1
        await state.update_data(index=index)

    index = max(0, min(index, len(orders) - 1))
    order = orders[index]
    text = get_order_text(order, lang, idx=index, total=len(orders))
    await cq.message.edit_text(
        text,
        reply_markup=get_inbox_controls(order["id"], lang, idx=index, total=len(orders)),
        parse_mode="HTML",
    )
    await cq.answer()


# === Izoh qo‘shish ===
@router.callback_query(F.data.startswith("inbox_comment"))
async def inbox_comment(cq: CallbackQuery, state: FSMContext):
    order_id = int(cq.data.split(":")[1])
    lang = (await state.get_data()).get("lang", "uz")

    await state.update_data(comment_order_id=order_id)
    await cq.message.answer(
        "✍️ Izohni yuboring:" if lang == "uz" else "✍️ Отправьте комментарий:"
    )
    await state.set_state(InboxStates.adding_comment)
    await cq.answer()


@router.message(StateFilter(InboxStates.adding_comment))
async def inbox_comment_text(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data["comment_order_id"]
    lang = data.get("lang", "uz")

    text_comment = (message.text or "").strip()
    await add_order_comment(order_id, text_comment)

    # Lokal ro'yxatni yangilash (alias + fallback)
    orders, index = data["orders"], data["index"]
    for o in orders:
        if o["id"] == order_id:
            o["comments"] = text_comment
            o["description_operator"] = text_comment
            break
    await state.update_data(orders=orders)

    order = orders[index]
    text = get_order_text(order, lang, idx=index, total=len(orders))
    await message.answer("✅ Izoh qo‘shildi" if lang == "uz" else "✅ Комментарий добавлен")
    await message.answer(
        text,
        reply_markup=get_inbox_controls(order_id, lang, idx=index, total=len(orders)),
        parse_mode="HTML",
    )
    await state.set_state(InboxStates.browsing)


# === Controllerga yuborish (status + connections log) ===
@router.callback_query(F.data.startswith("inbox_send_control"))
async def inbox_send_control(cq: CallbackQuery, state: FSMContext):
    order_id = int(cq.data.split(":")[1])
    data = await state.get_data()
    lang: str = data["lang"]
    orders = data["orders"]
    index = data["index"]

    # 0) Operatorning DB-dagi ID sini topamiz (telegram_id ➜ users.id)
    operator_db_id = await get_user_id_by_telegram_id(cq.from_user.id)
    if not operator_db_id:
        await cq.answer(
            "❌ Operator profili topilmadi (users.id). Avval tizimga ro‘yxatdan o‘tkazing."
            if lang == "uz" else
            "❌ Профиль оператора не найден (users.id). Сначала зарегистрируйте в системе.",
            show_alert=True,
        )
        return

    # 1) Controller topamiz (users.id)
    controller_id = await get_any_controller_id()
    if not controller_id:
        await cq.answer(
            "❌ Controller topilmadi. Admin bilan bog‘laning."
            if lang == "uz" else
            "❌ Не найден контроллер. Свяжитесь с админом.",
            show_alert=True,
        )
        return

    # 2) connections ga yozamiz (sender_id/recipient_id = users.id, technician_id = ariza_id)
    try:
        await log_connection_from_operator(
            sender_id=operator_db_id,
            recipient_id=controller_id,
            technician_order_id=order_id,
        )
    except Exception as e:
        await cq.answer(
            ("❌ Aloqa yozishda xatolik: " + str(e)) if lang == "uz"
            else ("❌ Ошибка записи соединения: " + str(e)),
            show_alert=True,
        )
        return

    # 3) statusni controllerga o‘tkazamiz
    await update_order_status(order_id, status="in_controller")

    # 4) ro'yxatdan chiqarish va navbatdagi arizani ko'rsatish
    orders = [o for o in orders if o["id"] != order_id]
    if not orders:
        await cq.message.edit_text("📭 Boshqa ariza yo‘q" if lang == "uz" else "📭 Заявок больше нет")
        await state.clear()
        await cq.answer()
        return

    new_index = min(index, len(orders) - 1)
    await state.update_data(orders=orders, index=new_index)
    new_order = orders[new_index]
    text = get_order_text(new_order, lang, idx=new_index, total=len(orders))
    await cq.message.edit_text(
        text,
        reply_markup=get_inbox_controls(new_order["id"], lang, idx=new_index, total=len(orders)),
        parse_mode="HTML",
    )
    await cq.answer("📤 Controllerga yuborildi" if lang == "uz" else "📤 Отправлено контроллеру", show_alert=True)


# === ✅ Arizani yopish (status + connections log: 'completed') ===
@router.callback_query(F.data.startswith("inbox_close:"))
async def inbox_close(cq: CallbackQuery, state: FSMContext):
    order_id = int(cq.data.split(":")[1])  # technician_orders.id
    data = await state.get_data()
    lang: str = data["lang"]
    orders = data["orders"]
    index = data["index"]

    # 0) Operator users.id
    operator_db_id = await get_user_id_by_telegram_id(cq.from_user.id)
    if not operator_db_id:
        await cq.answer(
            "❌ Operator profili topilmadi (users.id)." if lang == "uz"
            else "❌ Профиль оператора не найден (users.id).",
            show_alert=True,
        )
        return

    # 1) Controller users.id
    controller_id = await get_any_controller_id()
    if not controller_id:
        await cq.answer(
            "❌ Controller topilmadi." if lang == "uz" else "❌ Контроллер не найден.",
            show_alert=True,
        )
        return

    # 2) technician_orders ni 'completed' qilamiz
    try:
        await update_order_status(order_id, status="completed")
    except Exception as e:
        await cq.answer(
            ("❌ Arizani yopishda xatolik: " + str(e)) if lang == "uz"
            else ("❌ Ошибка закрытия заявки: " + str(e)),
            show_alert=True,
        )
        return

    # 3) connections ga 'completed' log yozamiz
    try:
        await log_connection_completed_from_operator(
            sender_id=operator_db_id,
            recipient_id=controller_id,
            technician_order_id=order_id,   # FK: connections.technician_id -> technician_orders.id
        )
    except Exception as e:
        await cq.answer(
            ("⚠️ Yopildi, lekin log yozilmadi: " + str(e)) if lang == "uz"
            else ("⚠️ Закрыто, но лог не записан: " + str(e)),
            show_alert=True,
        )

    # 4) ro'yxatdan chiqaramiz
    orders = [o for o in orders if o["id"] != order_id]
    if not orders:
        await cq.message.edit_text("✅ Ariza yopildi.\n\n📭 Boshqa ariza yo‘q" if lang == "uz"
                                   else "✅ Заявка закрыта.\n\n📭 Больше заявок нет")
        await state.clear()
        await cq.answer()
        return

    new_index = min(index, len(orders) - 1)
    await state.update_data(orders=orders, index=new_index)
    new_order = orders[new_index]
    text = get_order_text(new_order, lang, idx=new_index, total=len(orders))
    await cq.message.edit_text(
        "✅ Ariza yopildi.\n\n" + text if lang == "uz" else "✅ Заявка закрыта.\n\n" + text,
        reply_markup=get_inbox_controls(new_order["id"], lang, idx=new_index, total=len(orders)),
        parse_mode="HTML",
    )
    await cq.answer("✅ Yopildi" if lang == "uz" else "✅ Закрыто", show_alert=True)
