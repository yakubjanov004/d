from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime
import html

from filters.role_filter import RoleFilter
from database.queries import find_user_by_telegram_id
from database.warehouse_inbox import (
    fetch_warehouse_connection_orders,
    fetch_warehouse_connection_orders_with_materials,
    count_warehouse_connection_orders_with_materials,
    fetch_materials_for_connection_order,
    confirm_materials_and_update_status_for_connection,
    confirm_materials_and_update_status_for_technician,
    confirm_materials_and_update_status_for_staff,
    fetch_warehouse_technician_orders,
    fetch_warehouse_staff_orders,
    get_all_warehouse_orders_count,
    count_warehouse_connection_orders,
    count_warehouse_technician_orders,
    count_warehouse_staff_orders
)
from keyboards.warehouse_buttons import (
    get_warehouse_main_menu,
    get_warehouse_inbox_keyboard,
    get_warehouse_inbox_navigation_keyboard,
    get_connection_inbox_controls,
    get_technician_inbox_controls,
    get_staff_inbox_controls
)

router = Router()
router.message.filter(RoleFilter("warehouse"))
router.callback_query.filter(RoleFilter("warehouse"))

# Helper functions
def fmt_dt(dt) -> str:
    """Format datetime for display"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return html.escape(dt, quote=False)
    if isinstance(dt, datetime):
        return dt.strftime("%d.%m.%Y %H:%M")
    return "-"

def esc(v) -> str:
    """Escape HTML and handle None values"""
    return "-" if v is None else html.escape(str(v), quote=False)

def format_connection_order(order: dict, index: int, total: int) -> str:
    """Format connection order for display"""
    # Fallbacks for client fields in case LEFT JOIN returns NULL or different key names are used
    client_name_value = (
        order.get('client_name')
        or order.get('full_name')
        or order.get('client_full_name')
        or order.get('name')
    )
    client_phone_value = (
        order.get('client_phone')
        or order.get('phone')
        or order.get('client_phone_number')
    )
    return (
        f"📦 <b>Ombor - Ulanish arizasi</b>\n\n"
        f"🆔 <b>ID:</b> {esc(order.get('id'))}\n"
        f"👤 <b>Mijoz:</b> {esc(client_name_value)}\n"
        f"📞 <b>Telefon:</b> {esc(client_phone_value)}\n"
        f"📍 <b>Manzil:</b> {esc(order.get('address'))}\n"
        f"🌍 <b>Hudud:</b> {esc(order.get('region'))}\n"
        f"📊 <b>Tarif:</b> {esc(order.get('tariff_name'))}\n"
        f"📝 <b>Izohlar:</b> {esc(order.get('notes'))}\n"
        f"📋 <b>JM izohi:</b> {esc(order.get('jm_notes'))}\n"
        f"📅 <b>Yaratilgan:</b> {fmt_dt(order.get('created_at'))}\n"
        f"🔄 <b>Yangilangan:</b> {fmt_dt(order.get('updated_at'))}\n\n"
        f"📄 <b>{index + 1}/{total}</b>"
    )

def format_technician_order(order: dict, index: int, total: int) -> str:
    """Format technician order for display"""
    client_name_value = (
        order.get('client_name')
        or order.get('full_name')
        or order.get('client_full_name')
        or order.get('name')
    )
    client_phone_value = (
        order.get('client_phone')
        or order.get('phone')
        or order.get('client_phone_number')
    )
    return (
        f"🔧 <b>Ombor - Texnik xizmat arizasi</b>\n\n"
        f"🆔 <b>ID:</b> {esc(order.get('id'))}\n"
        f"👤 <b>Mijoz:</b> {esc(client_name_value)}\n"
        f"📞 <b>Telefon:</b> {esc(client_phone_value)}\n"
        f"🏠 <b>Abonent ID:</b> {esc(order.get('abonent_id'))}\n"
        f"📍 <b>Manzil:</b> {esc(order.get('address'))}\n"
        f"🌍 <b>Hudud:</b> {esc(order.get('region'))}\n"
        f"📝 <b>Tavsif:</b> {esc(order.get('description'))}\n"
        f"🔧 <b>Ish tavsifi:</b> {esc(order.get('description_ish'))}\n"
        f"📋 <b>Izohlar:</b> {esc(order.get('notes'))}\n"
        f"📅 <b>Yaratilgan:</b> {fmt_dt(order.get('created_at'))}\n"
        f"🔄 <b>Yangilangan:</b> {fmt_dt(order.get('updated_at'))}\n\n"
        f"📄 <b>{index + 1}/{total}</b>"
    )

def format_staff_order(order: dict, index: int, total: int) -> str:
    """Format staff order for display"""
    client_name_value = (
        order.get('client_name')
        or order.get('full_name')
        or order.get('client_full_name')
        or order.get('name')
    )
    client_phone_value = (
        order.get('client_phone')
        or order.get('phone')
        or order.get('client_phone_number')
    )
    return (
        f"👥 <b>Ombor - Xodim arizasi</b>\n\n"
        f"🆔 <b>ID:</b> {esc(order.get('id'))}\n"
        f"👤 <b>Mijoz:</b> {esc(client_name_value)}\n"
        f"📞 <b>Telefon:</b> {esc(client_phone_value)}\n"
        f"🏠 <b>Abonent ID:</b> {esc(order.get('abonent_id'))}\n"
        f"📍 <b>Manzil:</b> {esc(order.get('address'))}\n"
        f"🌍 <b>Hudud:</b> {esc(order.get('region'))}\n"
        f"📊 <b>Tarif:</b> {esc(order.get('tariff_name'))}\n"
        f"📝 <b>Tavsif:</b> {esc(order.get('description'))}\n"
        f"🏷️ <b>Ariza turi:</b> {esc(order.get('type_of_zayavka'))}\n"
        f"📅 <b>Yaratilgan:</b> {fmt_dt(order.get('created_at'))}\n"
        f"🔄 <b>Yangilangan:</b> {fmt_dt(order.get('updated_at'))}\n\n"
        f"📄 <b>{index + 1}/{total}</b>"
    )

@router.message(F.text == "📥 Inbox")
async def inbox_handler(message: Message, state: FSMContext):
    """Main inbox handler - shows order type selection"""
    user = await find_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    
    lang = user.get("language", "uz")
    
    # Get counts for each order type
    counts = await get_all_warehouse_orders_count()
    
    text = (
        f"📦 <b>Ombor - Inbox</b>\n\n"
        f"Omborda turgan arizalar:\n\n"
        f"🔗 <b>Ulanish arizalari:</b> {counts['connection_orders']}\n"
        f"🔧 <b>Texnik xizmat:</b> {counts['technician_orders']}\n"
        f"👥 <b>Xodim arizalari:</b> {counts['staff_orders']}\n\n"
        f"📊 <b>Jami:</b> {counts['total']}\n\n"
        f"Quyidagi tugmalardan birini tanlang:"
    )
    
    keyboard = get_warehouse_inbox_keyboard(lang)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# Connection orders handlers
@router.callback_query(F.data == "warehouse_inbox_connection")
async def show_connection_orders(callback: CallbackQuery, state: FSMContext):
    """Show connection orders"""
    await state.update_data(current_order_type="connection", current_index=0)
    
    # Faqat material_requests mavjud bo'lgan connection arizalarini ko'rsatamiz
    orders = await fetch_warehouse_connection_orders_with_materials(limit=1, offset=0)
    total_count = await count_warehouse_connection_orders_with_materials()
    
    if not orders:
        await callback.message.edit_text(
            "📦 <b>Ombor - Ulanish arizalari</b>\n\n❌ Hozirda omborda ulanish arizalari yo'q.",
            parse_mode="HTML",
            reply_markup=get_warehouse_inbox_keyboard()
        )
        return
    
    order = orders[0]
    mats = await fetch_materials_for_connection_order(order.get('id'))
    mats_text = "\n".join([f"• {esc(m['material_name'])} — {esc(m['quantity'])} dona" for m in mats]) if mats else "—"
    text = format_connection_order(order, 0, total_count) + f"\n\n🧾 <b>Materiallar:</b>\n{mats_text}"
    keyboard = get_connection_inbox_controls(0, total_count, order.get('id'))
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

# Technician orders handlers
@router.callback_query(F.data == "warehouse_inbox_technician")
async def show_technician_orders(callback: CallbackQuery, state: FSMContext):
    """Show technician orders"""
    await state.update_data(current_order_type="technician", current_index=0)
    
    orders = await fetch_warehouse_technician_orders(limit=1, offset=0)
    total_count = await count_warehouse_technician_orders()
    
    if not orders:
        await callback.message.edit_text(
            "🔧 <b>Ombor - Texnik xizmat arizalari</b>\n\n❌ Hozirda omborda texnik xizmat arizalari yo'q.",
            parse_mode="HTML",
            reply_markup=get_warehouse_inbox_keyboard()
        )
        return
    
    order = orders[0]
    text = format_technician_order(order, 0, total_count)
    keyboard = get_technician_inbox_controls(0, total_count, order.get('id'))
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

# Staff orders handlers
@router.callback_query(F.data == "warehouse_inbox_staff")
async def show_staff_orders(callback: CallbackQuery, state: FSMContext):
    """Show staff orders"""
    await state.update_data(current_order_type="staff", current_index=0)
    
    orders = await fetch_warehouse_staff_orders(limit=1, offset=0)
    total_count = await count_warehouse_staff_orders()
    
    if not orders:
        await callback.message.edit_text(
            "👥 <b>Ombor - Xodim arizalari</b>\n\n❌ Hozirda omborda xodim arizalari yo'q.",
            parse_mode="HTML",
            reply_markup=get_warehouse_inbox_keyboard()
        )
        return
    
    order = orders[0]
    text = format_staff_order(order, 0, total_count)
    keyboard = get_staff_inbox_controls(0, total_count, order.get('id'))
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

# Navigation handlers
@router.callback_query(F.data.startswith("warehouse_prev_inbox_"))
async def navigate_prev(callback: CallbackQuery, state: FSMContext):
    """Navigate to previous order"""
    parts = callback.data.split("_")
    new_index = int(parts[3])
    
    await state.update_data(current_index=new_index)
    
    # Get current order type from state
    data = await state.get_data()
    current_order_type = data.get('current_order_type', 'connection')
    
    if current_order_type == "connection":
        orders = await fetch_warehouse_connection_orders_with_materials(limit=1, offset=new_index)
        total_count = await count_warehouse_connection_orders_with_materials()
        if orders:
            mats = await fetch_materials_for_connection_order(orders[0].get('id'))
            mats_text = "\n".join([f"• {esc(m['material_name'])} — {esc(m['quantity'])} dona" for m in mats]) if mats else "—"
            text = format_connection_order(orders[0], new_index, total_count) + f"\n\n🧾 <b>Materiallar:</b>\n{mats_text}"
            keyboard = get_technician_inbox_controls(new_index, total_count, orders[0].get('id'))
    elif current_order_type == "technician":
        orders = await fetch_warehouse_technician_orders(limit=1, offset=new_index)
        total_count = await count_warehouse_technician_orders()
        if orders:
            text = format_technician_order(orders[0], new_index, total_count)
            keyboard = get_connection_inbox_controls(new_index, total_count, orders[0].get('id'))
    elif current_order_type == "staff":
        orders = await fetch_warehouse_staff_orders(limit=1, offset=new_index)
        total_count = await count_warehouse_staff_orders()
        if orders:
            text = format_staff_order(orders[0], new_index, total_count)
            keyboard = get_connection_inbox_controls(new_index, total_count, orders[0].get('id'))
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("warehouse_next_inbox_"))
async def navigate_next(callback: CallbackQuery, state: FSMContext):
    """Navigate to next order"""
    parts = callback.data.split("_")
    new_index = int(parts[3])

    await state.update_data(current_index=new_index)

    # Determine current order type from state
    data = await state.get_data()
    current_order_type = data.get('current_order_type', 'connection')

    if current_order_type == "connection":
        orders = await fetch_warehouse_connection_orders_with_materials(limit=1, offset=new_index)
        total_count = await count_warehouse_connection_orders_with_materials()
        if orders:
            mats = await fetch_materials_for_connection_order(orders[0].get('id'))
            mats_text = "\n".join([f"• {esc(m['material_name'])} — {esc(m['quantity'])} dona" for m in mats]) if mats else "—"
            text = format_connection_order(orders[0], new_index, total_count) + f"\n\n🧾 <b>Materiallar:</b>\n{mats_text}"
            keyboard = get_connection_inbox_controls(new_index, total_count, orders[0].get('id'))
    elif current_order_type == "technician":
        orders = await fetch_warehouse_technician_orders(limit=1, offset=new_index)
        total_count = await count_warehouse_technician_orders()
        if orders:
            text = format_technician_order(orders[0], new_index, total_count)
            keyboard = get_connection_inbox_controls(new_index, total_count, orders[0].get('id'))
    elif current_order_type == "staff":
        orders = await fetch_warehouse_staff_orders(limit=1, offset=new_index)
        total_count = await count_warehouse_staff_orders()
        if orders:
            text = format_staff_order(orders[0], new_index, total_count)
            keyboard = get_connection_inbox_controls(new_index, total_count, orders[0].get('id'))
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "warehouse_inbox_back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Go back to order type selection"""
    await state.clear()
    
    # Get counts for each order type
    counts = await get_all_warehouse_orders_count()
    
    text = (
        f"📦 <b>Ombor - Inbox</b>\n\n"
        f"Omborda turgan arizalar:\n\n"
        f"🔗 <b>Ulanish arizalari:</b> {counts['connection_orders']}\n"
        f"🔧 <b>Texnik xizmat:</b> {counts['technician_orders']}\n"
        f"👥 <b>Xodim arizalari:</b> {counts['staff_orders']}\n\n"
        f"📊 <b>Jami:</b> {counts['total']}\n\n"
        f"Quyidagi tugmalardan birini tanlang:"
    )
    
    keyboard = get_warehouse_inbox_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("warehouse_confirm_conn_"))
async def confirm_connection_materials(callback: CallbackQuery, state: FSMContext):
    """Ulanish arizasi uchun materiallarni tasdiqlash"""
    try:
        order_id = int(callback.data.replace("warehouse_confirm_conn_", ""))
    except ValueError:
        return await callback.answer("❌ Noto'g'ri ID", show_alert=True)

    # Get the user from database to get the internal user ID
    user = await find_user_by_telegram_id(callback.from_user.id)
    if not user:
        return await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
    
    try:
        ok = await confirm_materials_and_update_status_for_connection(order_id, user['id'])
        if not ok:
            return await callback.answer("❌ Tasdiqlashda xato", show_alert=True)
            
        await callback.answer("✅ Tasdiqlandi")
    except ValueError as e:
        return await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    except Exception as e:
        return await callback.answer(f"❌ Tasdiqlashda xato yuz berdi: {str(e)}", show_alert=True)
    # After confirming, go back to list starting at current index
    data = await state.get_data()
    idx = int(data.get('current_index', 0))
    # Reload current selection
    orders = await fetch_warehouse_connection_orders_with_materials(limit=1, offset=idx)
    total_count = await count_warehouse_connection_orders_with_materials()
    if not orders:
        # Nothing left, go back to categories
        return await back_to_categories(callback, state)

    order = orders[0]
    mats = await fetch_materials_for_connection_order(order.get('id'))
    mats_text = "\n".join([f"• {esc(m['material_name'])} — {esc(m['quantity'])} dona" for m in mats]) if mats else "—"
    text = format_connection_order(order, idx, total_count) + f"\n\n🧾 <b>Materiallar:</b>\n{mats_text}"
    keyboard = get_staff_inbox_controls(idx, total_count, order.get('id'))
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("warehouse_confirm_tech_"))
async def confirm_technician_materials(callback: CallbackQuery, state: FSMContext):
    """Texnik xizmat arizasi uchun materiallarni tasdiqlash"""
    try:
        order_id = int(callback.data.replace("warehouse_confirm_tech_", ""))
    except ValueError:
        return await callback.answer("❌ Noto'g'ri ID", show_alert=True)

    # Get the user from database to get the internal user ID
    user = await find_user_by_telegram_id(callback.from_user.id)
    if not user:
        return await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
    
    try:
        ok = await confirm_materials_and_update_status_for_technician(order_id, user['id'])
        if not ok:
            return await callback.answer("❌ Tasdiqlashda xato", show_alert=True)
            
        await callback.answer("✅ Tasdiqlandi")
    except ValueError as e:
        return await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    except Exception as e:
        return await callback.answer(f"❌ Tasdiqlashda xato yuz berdi: {str(e)}", show_alert=True)
    
    # After confirming, go back to list starting at current index
    data = await state.get_data()
    idx = int(data.get('current_index', 0))
    
    # Reload current selection
    orders = await fetch_warehouse_technician_orders(limit=1, offset=idx)
    total_count = await count_warehouse_technician_orders()
    
    if not orders:
        # Nothing left, go back to categories
        return await back_to_categories(callback, state)

    order = orders[0]
    text = format_technician_order(order, idx, total_count)
    keyboard = get_connection_inbox_controls(idx, total_count, order.get('id'))
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("warehouse_confirm_staff_"))
async def confirm_staff_materials(callback: CallbackQuery, state: FSMContext):
    """Xodim arizasi uchun materiallarni tasdiqlash"""
    try:
        order_id = int(callback.data.replace("warehouse_confirm_staff_", ""))
    except ValueError:
        return await callback.answer("❌ Noto'g'ri ID", show_alert=True)

    # Get the user from database to get the internal user ID
    user = await find_user_by_telegram_id(callback.from_user.id)
    if not user:
        return await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
    
    try:
        ok = await confirm_materials_and_update_status_for_staff(order_id, user['id'])
        if not ok:
            return await callback.answer("❌ Tasdiqlashda xato", show_alert=True)
            
        await callback.answer("✅ Tasdiqlandi")
    except ValueError as e:
        return await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
    except Exception as e:
        return await callback.answer(f"❌ Tasdiqlashda xato yuz berdi: {str(e)}", show_alert=True)
    
    # After confirming, go back to list starting at current index
    data = await state.get_data()
    idx = int(data.get('current_index', 0))
    
    # Reload current selection
    orders = await fetch_warehouse_staff_orders(limit=1, offset=idx)
    total_count = await count_warehouse_staff_orders()
    
    if not orders:
        # Nothing left, go back to categories
        return await back_to_categories(callback, state)

    order = orders[0]
    text = format_staff_order(order, idx, total_count)
    keyboard = get_connection_inbox_controls(idx, total_count, order.get('id'))
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "warehouse_inbox_back")
async def inbox_back(callback: CallbackQuery, state: FSMContext):
    """Handle back button from main inbox"""
    await state.clear()
    await callback.message.delete()

@router.callback_query(F.data == "warehouse_page_info")
async def page_info(callback: CallbackQuery):
    """Handle page info button (no action needed)"""
    await callback.answer()
