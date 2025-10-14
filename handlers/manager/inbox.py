from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from datetime import datetime
import html
import logging

from database.manager.queries import (
    get_user_by_telegram_id,
    get_users_by_role,
    fetch_manager_inbox,
    assign_to_junior_manager,
    count_manager_inbox,
    get_juniors_with_load_via_history,
    fetch_manager_inbox_staff,
    assign_to_junior_manager_for_staff,
    assign_to_controller_for_staff,
    count_manager_inbox_staff,
    get_controllers_with_load_via_history,
)
from filters.role_filter import RoleFilter

router = Router()
router.message.filter(RoleFilter("manager"))  # 🔒 faqat Manager uchun

logger = logging.getLogger(__name__)

# ==========================
# 🔧 UTIL
# ==========================
def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")

def esc(v) -> str:
    if v is None:
        return "-"
    return html.escape(str(v), quote=False)

# ==========================
# 🧩 VIEW + KEYBOARDS
# ==========================
def short_view_text(item: dict, index: int, total: int, lang: str) -> str:
    """Bitta arizaning qisqa ko'rinishini tayyorlaydi."""
    application_number = item.get("application_number")
    if application_number:
        short_id = application_number
    else:
        # Fallback: agar application_number yo'q bo'lsa
        full_id = str(item["id"])
        short_id = f"conn-{full_id.zfill(3)}"

    created = item["created_at"]
    created_dt = datetime.fromisoformat(created) if isinstance(created, str) else created

    tariff = esc(item.get("tariff", "-"))
    client_name = esc(item.get("client_name", "-"))
    client_phone = esc(item.get("client_phone", "-"))
    address = esc(item.get("address", "-"))
    short_id_safe = esc(short_id)

    if lang == "ru":
        base = (
            f"🔌 <b>Входящие менеджера</b>\n"
            f"🆔 <b>ID:</b> {short_id_safe}\n"
            f"📊 <b>Тариф:</b> {tariff}\n"
            f"👤 <b>Клиент:</b> {client_name}\n"
            f"📞 <b>Телефон:</b> {client_phone}\n"
            f"📍 <b>Адрес:</b> {address}\n"
            f"📅 <b>Создано:</b> {fmt_dt(created_dt)}"
        )
    else:
        base = (
            f"🔌 <b>Manager Inbox</b>\n"
            f"🆔 <b>ID:</b> {short_id_safe}\n"
            f"📊 <b>Tarif:</b> {tariff}\n"
            f"👤 <b>Mijoz:</b> {client_name}\n"
            f"📞 <b>Telefon:</b> {client_phone}\n"
            f"📍 <b>Manzil:</b> {address}\n"
            f"📅 <b>Yaratilgan:</b> {fmt_dt(created_dt)}"
        )

    # Staff orders uchun qo'shimcha ma'lumotlar
    req_type = item.get("req_type")
    staff_name = item.get("staff_name")
    staff_phone = item.get("staff_phone")
    staff_role = item.get("staff_role")
    desc = item.get("description")

    if req_type:
        if lang == "ru":
            base += f"\n🧾 <b>Тип заявки:</b> {esc(req_type)}"
        else:
            base += f"\n🧾 <b>Ariza turi:</b> {esc(req_type)}"
    
    if staff_name:
        if lang == "ru":
            base += f"\n👨‍💼 <b>Создал сотрудник:</b> {esc(staff_name)}"
            if staff_role:
                base += f" ({esc(staff_role)})"
        else:
            base += f"\n👨‍💼 <b>Yaratgan xodim:</b> {esc(staff_name)}"
            if staff_role:
                base += f" ({esc(staff_role)})"
    
    if staff_phone:
        if lang == "ru":
            base += f"\n📞 <b>Телефон сотрудника:</b> {esc(staff_phone)}"
        else:
            base += f"\n📞 <b>Xodim telefoni:</b> {esc(staff_phone)}"
    
    if desc:
        if lang == "ru":
            base += f"\n📝 <b>Описание:</b> {esc(desc)}"
        else:
            base += f"\n📝 <b>Tavsif:</b> {esc(desc)}"

    # Footer
    if lang == "ru":
        base += f"\n\n📊 <b>{index + 1}/{total}</b>"
    else:
        base += f"\n\n📊 <b>{index + 1}/{total}</b>"

    return base

def nav_keyboard(lang: str, current_idx: int = 0, total: int = 1, mode: str = "connection") -> InlineKeyboardMarkup:
    """Navigation tugmalari."""
    buttons = []
    
    # Orqaga/Oldinga tugmalari
    nav_buttons = []
    if current_idx > 0:  # Birinchi arizada emas
        if lang == "ru":
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_item"))
        else:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="prev_item"))
    
    if current_idx < total - 1:  # Oxirgi arizada emas
        if lang == "ru":
            nav_buttons.append(InlineKeyboardButton(text="➡️ Вперед", callback_data="next_item"))
        else:
            nav_buttons.append(InlineKeyboardButton(text="➡️ Oldinga", callback_data="next_item"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Mode'ga qarab turli tugmalar
    if mode == "connection":
        # Client arizalari uchun - Junior managerga yuborish
        if lang == "ru":
            buttons.append([InlineKeyboardButton(text="🧑‍💼 Отправить младшему менеджеру", callback_data="assign_open")])
        else:
            buttons.append([InlineKeyboardButton(text="🧑‍💼 Kichik menejerga yuborish", callback_data="assign_open")])
    elif mode == "staff":
        # Staff arizalari uchun - Controllerga yuborish
        if lang == "ru":
            buttons.append([InlineKeyboardButton(text="🎛️ Отправить контроллеру", callback_data="assign_controller_open")])
        else:
            buttons.append([InlineKeyboardButton(text="🎛️ Controllerga yuborish", callback_data="assign_controller_open")])
    
    # Yopish tugmasi
    if lang == "ru":
        buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_inbox")])
    else:
        buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="close_inbox")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def controller_list_keyboard(controllers: list, lang: str) -> InlineKeyboardMarkup:
    """Controllerlar ro'yxati tugmalari."""
    buttons = []
    
    for controller in controllers:
        name = controller.get("full_name", "Noma'lum")
        load = controller.get("current_load", 0)
        
        if lang == "ru":
            text = f"{name} ({load}шт)"
        else:
            text = f"{name} ({load}ta)"
        
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"assign_controller_{controller['id']}"
        )])
    
    # Orqaga tugmasi
    if lang == "ru":
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="assign_back")])
    else:
        buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="assign_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def category_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Kategoriya tanlash tugmalari."""
    if lang == "ru":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👤 Клиентские заявки", callback_data="cat_connection")],
                [InlineKeyboardButton(text="👨‍💼 Заявки сотрудников", callback_data="cat_staff")],
            ]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👤 Mijoz arizalari", callback_data="cat_connection")],
                [InlineKeyboardButton(text="👨‍💼 Xodim arizalari", callback_data="cat_staff")],
            ]
        )

def jm_list_keyboard(juniors: list, lang: str) -> InlineKeyboardMarkup:
    """Junior managerlar ro'yxati."""
    buttons = []
    for jm in juniors:
        name = esc(jm.get("full_name", "N/A"))
        load = jm.get("load_count", 0)
        if lang == "ru":
            text = f"👤 {name} ({load})"
        else:
            text = f"👤 {name} ({load}ta)"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"assign_jm_{jm['id']}")])
    
    if lang == "ru":
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="assign_back")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="assign_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def controller_list_keyboard(controllers: list, lang: str) -> InlineKeyboardMarkup:
    """Controllerlar ro'yxati."""
    buttons = []
    for controller in controllers:
        name = esc(controller.get("full_name", "N/A"))
        load = controller.get("load_count", 0)
        if lang == "ru":
            text = f"🎛️ {name} ({load})"
        else:
            text = f"🎛️ {name} ({load}ta)"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"assign_controller_{controller['id']}")])
    
    if lang == "ru":
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="assign_back")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="assign_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==========================
# 🎯 HANDLERS
# ==========================

@router.message(F.text.in_(["📥 Inbox", "📥 Входящие"]))
async def open_inbox(message: Message, state: FSMContext):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.get("role") not in ("manager", "controller"):
        return

    lang = user.get("language", "uz")
    if lang not in ["uz", "ru"]:
        lang = "uz"

    await state.update_data(lang=lang, inbox=[], idx=0, mode="connection")
    
    if lang == "ru":
        text = "📂 Какой раздел откроем?"
    else:
        text = "📂 Qaysi bo'limni ko'ramiz?"
    
    await message.answer(text, reply_markup=category_keyboard(lang))

@router.callback_query(F.data == "cat_connection")
async def cat_connection_flow(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    
    await callback.message.edit_reply_markup()
    
    # Client arizalarini olamiz
    inbox_items = await fetch_manager_inbox()
    total = await count_manager_inbox()
    
    if not inbox_items:
        if lang == "ru":
            text = "📭 Нет клиентских заявок"
        else:
            text = "📭 Mijoz arizalari yo'q"
        await callback.message.answer(text)
        return
    
    await state.update_data(inbox=inbox_items, idx=0, mode="connection")
    
    # Birinchi arizani ko'rsatamiz
    text = short_view_text(inbox_items[0], 0, total, lang)
    await callback.message.answer(text, reply_markup=nav_keyboard(lang, 0, total, "connection"), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "cat_staff")
async def cat_staff_flow(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    
    await callback.message.edit_reply_markup()
    
    # Staff arizalarini olamiz
    inbox_items = await fetch_manager_inbox_staff()
    total = await count_manager_inbox_staff()
    
    if not inbox_items:
        if lang == "ru":
            text = "📭 Нет заявок сотрудников"
        else:
            text = "📭 Xodim arizalari yo'q"
        await callback.message.answer(text)
        return
    
    await state.update_data(inbox=inbox_items, idx=0, mode="staff")
    
    # Birinchi arizani ko'rsatamiz
    text = short_view_text(inbox_items[0], 0, total, lang)
    await callback.message.answer(text, reply_markup=nav_keyboard(lang, 0, total, "staff"), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "prev_item")
async def prev_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    inbox = data.get("inbox", [])
    idx = data.get("idx", 0)
    mode = data.get("mode", "connection")
    lang = data.get("lang", "uz")
    
    if not inbox:
        await callback.answer("❌ Нет данных" if lang == "ru" else "❌ Ma'lumot yo'q")
        return
    
    new_idx = (idx - 1) % len(inbox)
    await state.update_data(idx=new_idx)
    
    text = short_view_text(inbox[new_idx], new_idx, len(inbox), lang)
    await callback.message.edit_text(text, reply_markup=nav_keyboard(lang, new_idx, len(inbox), mode), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "next_item")
async def next_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    inbox = data.get("inbox", [])
    idx = data.get("idx", 0)
    mode = data.get("mode", "connection")
    lang = data.get("lang", "uz")
    
    if not inbox:
        await callback.answer("❌ Нет данных" if lang == "ru" else "❌ Ma'lumot yo'q")
        return
    
    new_idx = (idx + 1) % len(inbox)
    await state.update_data(idx=new_idx)
    
    text = short_view_text(inbox[new_idx], new_idx, len(inbox), lang)
    await callback.message.edit_text(text, reply_markup=nav_keyboard(lang, new_idx, len(inbox), mode), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "assign_open")
async def assign_open(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    inbox = data.get("inbox", [])
    idx = data.get("idx", 0)
    mode = data.get("mode", "connection")
    lang = data.get("lang", "uz")
    
    if not inbox or idx >= len(inbox):
        await callback.answer("❌ Нет данных" if lang == "ru" else "❌ Ma'lumot yo'q")
        return
    
    current_item = inbox[idx]
    
    # Eski message'ni o'chirib tashlaymiz
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    if mode == "connection":
        # Client arizasi -> Junior Manager
        juniors = await get_juniors_with_load_via_history()
        if not juniors:
            if lang == "ru":
                text = "❌ Нет доступных младших менеджеров"
            else:
                text = "❌ Mavjud junior manager yo'q"
            await callback.message.answer(text)
            return
        
        if lang == "ru":
            text = "👤 Выберите младшего менеджера:"
        else:
            text = "👤 Junior managerni tanlang:"
        
        await callback.message.answer(text, reply_markup=jm_list_keyboard(juniors, lang))
    
    elif mode == "staff":
        # Staff ariza -> Controller
        controllers = await get_controllers_with_load_via_history()
        if not controllers:
            if lang == "ru":
                text = "❌ Нет доступных контроллеров"
            else:
                text = "❌ Mavjud controller yo'q"
            await callback.message.answer(text)
            return
        
        if lang == "ru":
            text = "🎛️ Выберите контроллера:"
        else:
            text = "🎛️ Controllerni tanlang:"
        
        await callback.message.answer(text, reply_markup=controller_list_keyboard(controllers, lang))
    
    await callback.answer()

@router.callback_query(F.data == "assign_controller_open")
async def assign_controller_open(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    inbox = data.get("inbox", [])
    idx = data.get("idx", 0)
    mode = data.get("mode", "staff")
    lang = data.get("lang", "uz")
    
    if not inbox or idx >= len(inbox):
        await callback.answer("❌ Нет данных" if lang == "ru" else "❌ Ma'lumot yo'q")
        return
    
    current_item = inbox[idx]
    
    # Eski message'ni o'chirib tashlaymiz
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    if mode == "staff":
        # Staff ariza -> Controller
        controllers = await get_controllers_with_load_via_history()
        if not controllers:
            if lang == "ru":
                text = "❌ Нет доступных контроллеров"
            else:
                text = "❌ Mavjud controller yo'q"
            await callback.message.answer(text)
            return
        
        if lang == "ru":
            text = "🎛️ Выберите контроллера:"
        else:
            text = "🎛️ Controllerni tanlang:"
        
        await callback.message.answer(text, reply_markup=controller_list_keyboard(controllers, lang))
    
        await callback.answer()

@router.callback_query(F.data.startswith("assign_controller_"))
async def assign_controller_pick(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    inbox = data.get("inbox", [])
    idx = data.get("idx", 0)
    mode = data.get("mode", "staff")
    lang = data.get("lang", "uz")
    
    if not inbox or idx >= len(inbox):
        await callback.answer("❌ Нет данных" if lang == "ru" else "❌ Ma'lumot yo'q")
        return
    
    current_item = inbox[idx]
    controller_id = int(callback.data.split("_")[-1])
    
    try:
        if mode == "staff":
            # Manager'ning database ID'sini olamiz
            manager_user = await get_user_by_telegram_id(callback.from_user.id)
            if not manager_user:
                await callback.answer("❌ Manager topilmadi!" if lang == "uz" else "❌ Manager не найден!", show_alert=True)
                return
            
            manager_db_id = manager_user["id"]
            
            # Staff ariza -> Controller
            await assign_to_controller_for_staff(current_item["id"], controller_id, manager_db_id)
            
            if lang == "ru":
                text = f"✅ Заявка назначена контроллеру"
            else:
                text = f"✅ Ariza controllerga tayinlandi"
        
        # Inline klaviatura o'chirib, xabarni edit qilamiz
        await callback.message.edit_text(text, reply_markup=None)
        await callback.answer()
        
        # Controller'ga notification yuboramiz (state'ga ta'sir qilmaydi)
        if mode == "staff":
            try:
                from loader import bot
                import asyncpg
                from config import settings
                
                conn = await asyncpg.connect(settings.DB_URL)
                try:
                    controller_info = await conn.fetchrow(
                        "SELECT id, telegram_id, language, full_name FROM users WHERE id = $1 AND role = 'controller'",
                        controller_id
                    )
                    if controller_info:
                        # Notification xabari
                        if controller_info.get("language") == "ru":
                            notification = f"📬 <b>Новая заявка сотрудника</b>\n\n🆔 {current_item.get('application_number', 'N/A')}\n\n📊 У вас теперь новая заявка"
                        else:
                            notification = f"📬 <b>Yangi xodim arizasi</b>\n\n🆔 {current_item.get('application_number', 'N/A')}\n\n📊 Sizda yangi ariza bor"
                        
                        # Notification yuborish
                        await bot.send_message(
                            chat_id=controller_info["telegram_id"],
                            text=notification,
                            parse_mode="HTML"
                        )
                        logger.info(f"Notification sent to controller {controller_id} for staff order {current_item.get('id')}")
                finally:
                    await conn.close()
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")
                # Notification xatosi asosiy jarayonga ta'sir qilmaydi
        
        # Inboxni yangilaymiz
        if mode == "connection":
            inbox_items = await fetch_manager_inbox()
        else:
            inbox_items = await fetch_manager_inbox_staff()
        
        if not inbox_items:
            if lang == "ru":
                text = "📭 Нет заявок"
            else:
                text = "📭 Arizalar yo'q"
            await callback.message.answer(text)
            return
        
        new_idx = min(idx, len(inbox_items) - 1)
        await state.update_data(inbox=inbox_items, idx=new_idx)
        
        text = short_view_text(inbox_items[new_idx], new_idx, len(inbox_items), lang)
        await callback.message.answer(text, reply_markup=nav_keyboard(lang, new_idx, len(inbox_items), mode), parse_mode="HTML")
        
    except Exception as e:
        if lang == "ru":
            text = f"❌ Ошибка: {str(e)}"
        else:
            text = f"❌ Xatolik: {str(e)}"
        await callback.message.answer(text)
        await callback.answer()

@router.callback_query(F.data == "close_inbox")
async def close_inbox(callback: CallbackQuery, state: FSMContext):
    """Inbox yopish."""
    data = await state.get_data()
    lang = data.get("lang", "uz")
    
    # State ni tozalaymiz
    await state.clear()
    
    # Xabarni o'chirib tashlaymiz
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    if lang == "ru":
        text = "✅ Inbox закрыт"
    else:
        text = "✅ Inbox yopildi"
    
    await callback.answer(text)

@router.callback_query(F.data == "assign_back")
async def assign_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    inbox = data.get("inbox", [])
    idx = data.get("idx", 0)
    lang = data.get("lang", "uz")
    
    if not inbox or idx >= len(inbox):
        await callback.answer("❌ Нет данных" if lang == "ru" else "❌ Ma'lumot yo'q")
        return
    
    # Eski message'ni o'chirib tashlaymiz
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Yangi message yuboramiz
    text = short_view_text(inbox[idx], idx, len(inbox), lang)
    await callback.message.answer(text, reply_markup=nav_keyboard(lang, idx, len(inbox), mode), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("assign_jm_"))
async def assign_pick(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    inbox = data.get("inbox", [])
    idx = data.get("idx", 0)
    mode = data.get("mode", "connection")
    lang = data.get("lang", "uz")
    
    if not inbox or idx >= len(inbox):
        await callback.answer("❌ Нет данных" if lang == "ru" else "❌ Ma'lumot yo'q")
        return
    
    current_item = inbox[idx]
    jm_id = int(callback.data.split("_")[-1])
    
    try:
        if mode == "connection":
            # Manager'ning database ID'sini olamiz
            manager_user = await get_user_by_telegram_id(callback.from_user.id)
            if not manager_user:
                await callback.answer("❌ Manager topilmadi!" if lang == "uz" else "❌ Manager не найден!", show_alert=True)
                return
            
            manager_db_id = manager_user["id"]
            
            # Client ariza -> Junior Manager (notification info qaytaradi)
            recipient_info = await assign_to_junior_manager(current_item["id"], jm_id, manager_db_id)
            
            # Junior manager nomini olamiz
            jm_name = recipient_info.get("jm_name", "Noma'lum")
            app_number = recipient_info.get("application_number", "N/A")
            
            if lang == "ru":
                text = f"✅ Заявка {app_number} назначена младшему менеджеру {jm_name}"
            else:
                text = f"✅ Ariza {app_number} junior manager {jm_name}ga tayinlandi"
        
        # Inline klaviatura o'chirib, xabarni edit qilamiz
        await callback.message.edit_text(text, reply_markup=None)
        await callback.answer()
        
        # Junior Manager'ga notification yuboramiz (state'ga ta'sir qilmaydi)
        if mode == "connection":
            try:
                from loader import bot
                
                # Notification matnini tayyorlash
                app_num = recipient_info["application_number"]
                current_load = recipient_info["current_load"]
                recipient_lang = recipient_info["language"]
                
                # Notification xabari
                if recipient_lang == "ru":
                    notification = f"📬 <b>Новая заявка подключения</b>\n\n🆔 {app_num}\n\n📊 У вас теперь <b>{current_load}</b> активных заявок"
                else:
                    notification = f"📬 <b>Yangi ulanish arizasi</b>\n\n🆔 {app_num}\n\n📊 Sizda yana <b>{current_load}ta</b> ariza bor"
                
                # Notification yuborish
                await bot.send_message(
                    chat_id=recipient_info["telegram_id"],
                    text=notification,
                    parse_mode="HTML"
                )
                logger.info(f"Notification sent to junior manager {jm_id} for order {app_num}")
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")
                # Notification xatosi asosiy jarayonga ta'sir qilmaydi
        
        # Inboxni yangilaymiz
        if mode == "connection":
            inbox_items = await fetch_manager_inbox()
        else:
            inbox_items = await fetch_manager_inbox_staff()
        
        if not inbox_items:
            if lang == "ru":
                text = "📭 Нет заявок"
            else:
                text = "📭 Arizalar yo'q"
            await callback.message.answer(text)
            return
        
        new_idx = min(idx, len(inbox_items) - 1)
        await state.update_data(inbox=inbox_items, idx=new_idx)
        
        text = short_view_text(inbox_items[new_idx], new_idx, len(inbox_items), lang)
        await callback.message.answer(text, reply_markup=nav_keyboard(lang, new_idx, len(inbox_items), mode), parse_mode="HTML")
        
    except Exception as e:
        if lang == "ru":
            text = f"❌ Ошибка: {str(e)}"
        else:
            text = f"❌ Xatolik: {str(e)}"
        await callback.message.answer(text)
        await callback.answer()

@router.callback_query(F.data.startswith("assign_controller_"))
async def assign_controller_pick(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    inbox = data.get("inbox", [])
    idx = data.get("idx", 0)
    mode = data.get("mode", "staff")
    lang = data.get("lang", "uz")
    
    if not inbox or idx >= len(inbox):
        await callback.answer("❌ Нет данных" if lang == "ru" else "❌ Ma'lumot yo'q")
        return
    
    current_item = inbox[idx]
    controller_id = int(callback.data.split("_")[-1])
    
    try:
        if mode == "staff":
            # Manager'ning database ID'sini olamiz
            manager_user = await get_user_by_telegram_id(callback.from_user.id)
            if not manager_user:
                await callback.answer("❌ Manager topilmadi!" if lang == "uz" else "❌ Manager не найден!", show_alert=True)
                return
            
            manager_db_id = manager_user["id"]
            
            # Staff ariza -> Controller (connections yozamiz va notification info qaytaradi)
            recipient_info = await assign_to_controller_for_staff(current_item["id"], controller_id, manager_db_id)
            
            # Controller nomini olamiz
            controller_name = "Controller"  # Default name
            
            # Mavjud message'ni edit qilamiz - faqat ariza ma'lumotlari bilan (inline buttons yo'q)
            original_text = short_view_text(current_item, idx, len(inbox), lang)
            
            # Edit text bilan ariza ma'lumotlarini ko'rsatamiz va inline buttonsni o'chirib tashlaymiz
            await callback.message.edit_text(
                original_text,
                reply_markup=None,  # Inline buttonsni to'liq o'chirib tashlaymiz
                parse_mode="HTML"
            )
            
            # Keyin yangi xabar yuboramiz - assignment haqida ma'lumot bilan
            if lang == "ru":
                assignment_text = f"✅ Заявка отправлена контроллеру: {controller_name}"
            else:
                assignment_text = f"✅ Ariza controller'ga yuborildi: {controller_name}"
            
            await callback.message.answer(assignment_text)
            await callback.answer(assignment_text)
            
            # Controller'ga notification yuboramiz (state'ga ta'sir qilmaydi)
            try:
                from loader import bot
                
                # Notification matnini tayyorlash
                app_num = recipient_info["application_number"]
                current_load = recipient_info["current_load"]
                recipient_lang = recipient_info["language"]
                order_type = recipient_info.get("order_type", "staff")
                
                # Ariza turini formatlash
                if recipient_lang == "ru":
                    if order_type == "connection":
                        order_type_text = "подключения"
                    elif order_type == "technician":
                        order_type_text = "технической"
                    else:
                        order_type_text = "сотрудника"
                else:
                    if order_type == "connection":
                        order_type_text = "ulanish"
                    elif order_type == "technician":
                        order_type_text = "texnik xizmat"
                    else:
                        order_type_text = "xodim"
                
                # Notification xabari
                if recipient_lang == "ru":
                    notification = f"📬 <b>Новая заявка {order_type_text}</b>\n\n🆔 {app_num}\n\n📊 У вас теперь <b>{current_load}</b> активных заявок"
                else:
                    notification = f"📬 <b>Yangi {order_type_text} arizasi</b>\n\n🆔 {app_num}\n\n📊 Sizda yana <b>{current_load}ta</b> ariza bor"
                
                # Notification yuborish
                await bot.send_message(
                    chat_id=recipient_info["telegram_id"],
                    text=notification,
                    parse_mode="HTML"
                )
                logger.info(f"Notification sent to controller {controller_id} for order {app_num}")
            except Exception as notif_error:
                logger.error(f"Failed to send notification: {notif_error}")
                # Notification xatosi asosiy jarayonga ta'sir qilmaydi
        
    except Exception as e:
        logger.exception("Controller assign error: %s", e)
        await callback.answer("❌ Xatolik yuz berdi!" if lang == "uz" else "❌ Произошла ошибка!", show_alert=True)