from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from datetime import datetime

from database.basic.user import get_user_by_telegram_id, update_user_full_name
from database.basic.language import get_user_language
from database.client.material_info import get_user_orders_with_materials, get_materials_for_user_order
from database.client.queries import get_region_display_name
from keyboards.client_buttons import get_client_main_menu, get_client_profile_reply_keyboard
from states.client_states import ProfileEditStates

router = Router()

# --- HELPERS ---
def _fmt_dt(value) -> str:
    if isinstance(value, datetime):
        return value.strftime('%d.%m.%Y %H:%M')
    try:
        return datetime.fromisoformat(str(value)).strftime('%d.%m.%Y %H:%M')
    except Exception:
        return str(value)


# === PROFILE ===
@router.message(F.text.in_(["👤 Kabinet", "👤 Кабинет"]))
async def profile_handler(message: Message):
    user_lang = await get_user_language(message.from_user.id)

    texts = {
        "uz": "🏠 <b>Shaxsiy kabinet</b>\n\n💡 Quyidagi menyudan kerakli amalni tanlang:",
        "ru": "🏠 <b>Личный кабинет</b>\n\n💡 Выберите нужное действие из меню:",
    }

    await message.answer(
        texts.get(user_lang, texts["uz"]),
        parse_mode="HTML",
        reply_markup=get_client_profile_reply_keyboard(user_lang)
    )


# === VIEW INFO ===
@router.message(F.text.in_(["👀 Ma'lumotlarni ko'rish", "👀 Просмотр информации"]))
async def view_info_handler(message: Message):
    user_lang = await get_user_language(message.from_user.id)
    telegram_id = message.from_user.id

    user_info = await get_user_by_telegram_id(telegram_id)
    if not user_info:
        text = "❌ Foydalanuvchi ma'lumotlar bazasida topilmadi." if user_lang == "uz" else "❌ Пользователь не найден в базе данных."
        await message.answer(text, parse_mode="HTML")
        return

    if user_lang == "ru":
        text = (
            "👀 <b>Просмотр информации</b>\n\n"
            f"👤 Имя: {user_info.get('full_name', 'Не указано')}\n"
            f"📱 Телефон: {user_info.get('phone', 'Не указан')}\n"
            f"📅 Дата регистрации: {_fmt_dt(user_info.get('created_at'))}\n"
        )
    else:
        text = (
            "👀 <b>Ma'lumotlarni ko'rish</b>\n\n"
            f"👤 Ism: {user_info.get('full_name', "Ko'rsatilmagan")}\n"
            f"📱 Telefon: {user_info.get('phone', "Ko'rsatilmagan")}\n"
            f"📅 Ro'yxatdan o'tgan: {_fmt_dt(user_info.get('created_at'))}\n"
        )

    if user_info.get('username'):
        text += f"📧 Username: @{user_info['username']}\n"

    await message.answer(text, parse_mode="HTML")


# === ORDERS ===
@router.message(F.text.in_(["📋 Mening arizalarim", "📋 Мои заявки"]))
async def my_orders_handler(message: Message, state: FSMContext):
    await show_orders_with_state(message, state, 0)


async def show_orders_with_state(message: Message, state: FSMContext, idx: int = 0):
    user_lang = await get_user_language(message.from_user.id)
    telegram_id = message.from_user.id
    orders = await get_user_orders_with_materials(telegram_id, offset=0, limit=1000)

    if not orders:
        text = (
            "📋 <b>Mening arizalarim</b>\n\n❌ Sizda hali arizalar yo‘q."
            if user_lang == "uz" else
            "📋 <b>Мои заявки</b>\n\n❌ У вас пока нет заявок."
        )
        await message.answer(text, parse_mode="HTML")
        return

    await state.update_data(orders=orders, idx=idx, lang=user_lang)
    await render_order_card(message, orders, idx, user_lang)


async def render_order_card(target, orders: list, idx: int, user_lang: str, edit_message: bool = False):
    if idx < 0 or idx >= len(orders):
        return

    order = orders[idx]
    otype = (order.get('order_type') or '').lower()
    is_conn = otype in ('connection', 'connection_request')
    
    # Application number ni olish
    application_number = order.get('application_number') or f"#{order['id']}"
    
    # Media faylini tekshirish
    media_file_id = order.get('media_file_id')
    media_type = order.get('media_type')

    if user_lang == "ru":
        order_type_text = "🔗 Подключение" if is_conn else "🔧 Техническая заявка"
        text = (
            f"📋 <b>Мои заявки</b>\n\n"
            f"<b>Заявка {application_number}</b>\n"
            f"📝 Тип: {order_type_text}\n"
            f"📍 Регион: {get_region_display_name(order.get('region', '-'))}\n"
            f"🏠 Адрес: {order.get('address','-')}\n"
        )
        if order.get('abonent_id'):
            text += f"🆔 ID абонента: {order['abonent_id']}\n"
        if order.get('description'):
            text += f"📄 Описание: {order['description']}\n"
        text += f"📅 Создана: {_fmt_dt(order.get('created_at'))}\n"
        
        # Material ma'lumotlarini qo'shish
        has_materials = order.get('has_materials_used', False)
        materials_count = order.get('materials_count', 0)
        materials_cost = order.get('materials_total_cost', 0)
        
        if has_materials and materials_count > 0:
            text += f"📦 Использовано материалов: {materials_count}\n"
            if materials_cost:
                text += f"💰 Стоимость материалов: {materials_cost:,.0f} сум\n"
        
        text += f"\n🗂️ <i>Заявка {idx + 1} / {len(orders)}</i>"
    else:
        order_type_text = "🔗 Ulanish" if is_conn else "🔧 Texnik ariza"
        text = (
            f"📋 <b>Mening arizalarim</b>\n\n"
            f"<b>Ariza {application_number}</b>\n"
            f"📝 Turi: {order_type_text}\n"
            f"📍 Hudud: {get_region_display_name(order.get('region', '-'))}\n"
            f"🏠 Manzil: {order.get('address','-')}\n"
        )
        if order.get('abonent_id'):
            text += f"🆔 Abonent ID: {order['abonent_id']}\n"
        if order.get('description'):
            text += f"📄 Tavsif: {order['description']}\n"
        text += f"📅 Yaratildi: {_fmt_dt(order.get('created_at'))}\n"
        
        # Material ma'lumotlarini qo'shish
    has_materials = order.get('has_materials_used', False)
    materials_count = order.get('materials_count', 0)
    materials_cost = order.get('materials_total_cost', 0)
    
    if has_materials and materials_count > 0:
        if user_lang == "ru":
            text += f"📦 Использовано материалов: {materials_count}\n"
            if materials_cost:
                text += f"💰 Стоимость материалов: {materials_cost:,.0f} сум\n"
        else:
            text += f"📦 Ishlatilgan materiallar: {materials_count}\n"
            if materials_cost:
                text += f"💰 Materiallar narxi: {materials_cost:,.0f} so'm\n"
    
    text += f"\n🗂️ <i>Ariza {idx + 1} / {len(orders)}</i>"

    # navigation
    keyboard = []
    nav_buttons = []
    if idx > 0:
        prev_text = "⬅️ Oldingi" if user_lang == "uz" else "⬅️ Предыдущая"
        nav_buttons.append(InlineKeyboardButton(text=prev_text, callback_data=f"client_orders_prev_{idx}"))
    if idx < len(orders) - 1:
        next_text = "Keyingi ➡️" if user_lang == "uz" else "Следующая ➡️"
        nav_buttons.append(InlineKeyboardButton(text=next_text, callback_data=f"client_orders_next_{idx}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Material details button
    if has_materials and materials_count > 0:
        material_details_text = "📦 Materiallar tafsiloti" if user_lang == "uz" else "📦 Детали материалов"
        keyboard.append([InlineKeyboardButton(
            text=material_details_text, 
            callback_data=f"client_material_details_{application_number}_{otype}"
        )])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    # Helper function to detect media type from Telegram file ID
    def detect_media_type_from_file_id(file_id: str) -> str:
        """Detect media type from Telegram file ID prefix"""
        if not file_id:
            return None
        
        # Telegram file ID prefixes for different media types
        if file_id.startswith('BAADBAAD'):  # Video note
            return 'video'
        elif file_id.startswith('BAACAgI'):  # Video
            return 'video'
        elif file_id.startswith('BAAgAgI'):  # Video
            return 'video'
        elif file_id.startswith('AgACAgI'):  # Photo
            return 'photo'
        elif file_id.startswith('CAAQAgI'):  # Photo
            return 'photo'
        else:
            return None

    # Media faylini yuborish
    if isinstance(target, CallbackQuery) or edit_message:
        # Callback query uchun yoki edit_message=True bo'lsa - faqat matn yuborish
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await target.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        # Message uchun - media bilan yuborish
        if media_file_id:
            # Detect actual media type from file ID if database type is wrong
            actual_media_type = detect_media_type_from_file_id(media_file_id)
            effective_media_type = actual_media_type or media_type
            
            print(f"Media file_id: {media_file_id}, db_type: {media_type}, detected_type: {actual_media_type}, effective_type: {effective_media_type}")
            
            try:
                if effective_media_type == 'video':
                    try:
                        await target.answer_video(
                            video=media_file_id,
                            caption=text,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    except Exception as e:
                        print(f"Video send failed, retrying as photo: {e}")
                        try:
                            await target.answer_photo(
                                photo=media_file_id,
                                caption=text,
                                parse_mode='HTML',
                                reply_markup=reply_markup
                            )
                        except Exception as e2:
                            print(f"Photo send also failed: {e2}")
                            await target.answer(text, parse_mode='HTML', reply_markup=reply_markup)
                elif effective_media_type == 'photo':
                    try:
                        await target.answer_photo(
                            photo=media_file_id,
                            caption=text,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    except Exception as e:
                        print(f"Photo send failed: {e}")
                        await target.answer(text, parse_mode='HTML', reply_markup=reply_markup)
                else:
                    # Aniq turi noma'lum bo'lsa, video sifatida sinab ko'ramiz
                    try:
                        await target.answer_video(
                            video=media_file_id,
                            caption=text,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    except Exception as e:
                        print(f"Video send failed, retrying as photo: {e}")
                        try:
                            await target.answer_photo(
                                photo=media_file_id,
                                caption=text,
                                parse_mode='HTML',
                                reply_markup=reply_markup
                            )
                        except Exception as e2:
                            print(f"Photo send also failed: {e2}")
                            await target.answer(text, parse_mode='HTML', reply_markup=reply_markup)
            except Exception as e:
                print(f"All media attempts failed: {e}")
                await target.answer(text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await target.answer(text, parse_mode='HTML', reply_markup=reply_markup)


@router.callback_query(F.data.startswith("client_orders_prev_"))
async def prev_order_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    orders = data.get("orders", [])
    idx = int(callback.data.replace("client_orders_prev_", "")) - 1
    if 0 <= idx < len(orders):
        await state.update_data(idx=idx)
        # Try to edit the existing message instead of deleting and sending new one
        try:
            await render_order_card(callback.message, orders, idx, data.get("lang", "uz"), edit_message=True)
        except Exception:
            # If editing fails, fallback to delete and send new message
            try:
                await callback.message.delete()
            except:
                pass
            await render_order_card(callback.message, orders, idx, data.get("lang", "uz"), edit_message=False)


@router.callback_query(F.data.startswith("client_orders_next_"))
async def next_order_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    orders = data.get("orders", [])
    idx = int(callback.data.replace("client_orders_next_", "")) + 1
    if 0 <= idx < len(orders):
        await state.update_data(idx=idx)
        # Try to edit the existing message instead of deleting and sending new one
        try:
            await render_order_card(callback.message, orders, idx, data.get("lang", "uz"), edit_message=True)
        except Exception:
            # If editing fails, fallback to delete and send new message
            try:
                await callback.message.delete()
            except:
                pass
            await render_order_card(callback.message, orders, idx, data.get("lang", "uz"), edit_message=False)


@router.callback_query(F.data.startswith("client_material_details_"))
async def material_details_handler(callback: CallbackQuery):
    await callback.answer()
    
    # Parse callback data: client_material_details_{application_number}_{order_type}
    parts = callback.data.replace("client_material_details_", "").split("_", 1)
    if len(parts) != 2:
        await callback.message.answer("❌ Xatolik yuz berdi.")
        return
    
    application_number = parts[0]
    order_type = parts[1]
    
    user_lang = await get_user_language(callback.from_user.id)
    
    # Get material details
    materials = await get_materials_for_user_order(application_number, order_type)
    
    if not materials:
        text = "❌ Materiallar topilmadi." if user_lang == "uz" else "❌ Материалы не найдены."
        await callback.message.answer(text)
        return
    
    # Format material details
    if user_lang == "ru":
        text = f"📦 <b>Детали материалов</b>\n\n<b>Заявка: {application_number}</b>\n\n"
        total_cost = 0
        for i, material in enumerate(materials, 1):
            text += f"{i}. <b>{material['material_name']}</b>\n"
            text += f"   📊 Количество: {material['quantity']}\n"
            text += f"   💰 Цена за единицу: {material['price']:,.0f} сум\n"
            text += f"   💵 Общая стоимость: {material['total_price']:,.0f} сум\n"
            text += f"   👤 Выдал: {material['technician_name']}\n"
            text += f"   📅 Дата выдачи: {_fmt_dt(material['issued_at'])}\n\n"
            total_cost += material['total_price']
        
        text += f"💰 <b>Общая стоимость: {total_cost:,.0f} сум</b>"
    else:
        text = f"📦 <b>Materiallar tafsiloti</b>\n\n<b>Ariza: {application_number}</b>\n\n"
        total_cost = 0
        for i, material in enumerate(materials, 1):
            text += f"{i}. <b>{material['material_name']}</b>\n"
            text += f"   📊 Miqdori: {material['quantity']}\n"
            text += f"   💰 Birlik narxi: {material['price']:,.0f} so'm\n"
            text += f"   💵 Jami narx: {material['total_price']:,.0f} so'm\n"
            text += f"   👤 Bergan: {material['technician_name']}\n"
            text += f"   📅 Berilgan sana: {_fmt_dt(material['issued_at'])}\n\n"
            total_cost += material['total_price']
        
        text += f"💰 <b>Jami narx: {total_cost:,.0f} so'm</b>"
    
    # Add back button
    back_text = "◀️ Orqaga" if user_lang == "uz" else "◀️ Назад"
    keyboard = [[InlineKeyboardButton(text=back_text, callback_data="client_back_to_orders")]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Edit the existing message instead of sending a new one
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception:
        # If editing fails (e.g., due to media conflicts), send new message as fallback
        await callback.message.answer(text, parse_mode="HTML", reply_markup=reply_markup)


@router.callback_query(F.data == "client_back_to_orders")
async def back_to_orders_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    orders = data.get("orders", [])
    idx = data.get("idx", 0)
    user_lang = data.get("lang", "uz")
    
    if orders and 0 <= idx < len(orders):
        # Try to edit the existing message first, fallback to new message if needed
        try:
            await render_order_card(callback.message, orders, idx, user_lang, edit_message=True)
        except Exception:
            # If editing fails, send new message as fallback
            await render_order_card(callback.message, orders, idx, user_lang, edit_message=False)


# === EDIT NAME ===
@router.message(F.text.in_(["✏️ Ismni o'zgartirish", "✏️ Изменить имя"]))
async def edit_name_handler(message: Message, state: FSMContext):
    user_lang = await get_user_language(message.from_user.id)
    telegram_id = message.from_user.id
    user_info = await get_user_by_telegram_id(telegram_id)

    if not user_info:
        text = "❌ Foydalanuvchi topilmadi." if user_lang == "uz" else "❌ Пользователь не найден."
        await message.answer(text, parse_mode="HTML")
        return

    current_name = user_info.get('full_name', '—')
    if user_lang == "ru":
        text = (
            f"✏️ <b>Изменить имя</b>\n\n"
            f"👤 Текущее имя: <b>{current_name}</b>\n\n"
            "📝 Введите новое имя (минимум 3 символа):"
        )
    else:
        text = (
            f"✏️ <b>Ismni o‘zgartirish</b>\n\n"
            f"👤 Hozirgi ism: <b>{current_name}</b>\n\n"
            "📝 Yangi ismni kiriting (kamida 3 ta belgi):"
        )

    await state.set_state(ProfileEditStates.waiting_for_new_name)
    await message.answer(text, parse_mode="HTML")


@router.message(ProfileEditStates.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    user_lang = await get_user_language(message.from_user.id)
    new_name = message.text.strip()

    if len(new_name) < 3:
        text = "❌ Ism kamida 3 ta belgidan iborat bo‘lishi kerak." if user_lang == "uz" else "❌ Имя должно содержать минимум 3 символа."
        await message.answer(text, parse_mode="HTML")
        return

    try:
        await update_user_full_name(message.from_user.id, new_name)
        await state.clear()
        text = (
            f"✅ <b>Ism muvaffaqiyatli o‘zgartirildi!</b>\n\n👤 Yangi ism: <b>{new_name}</b>"
            if user_lang == "uz" else
            f"✅ <b>Имя успешно изменено!</b>\n\n👤 Новое имя: <b>{new_name}</b>"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=get_client_profile_reply_keyboard(user_lang))
    except Exception:
        text = "❌ Xatolik yuz berdi, keyinroq urinib ko‘ring." if user_lang == "uz" else "❌ Ошибка при сохранении имени."
        await message.answer(text, parse_mode="HTML")
        await state.clear()


# === BACK TO MAIN ===
@router.message(F.text.in_(["◀️ Orqaga", "◀️ Назад"]))
async def back_to_main_menu_handler(message: Message):
    user_lang = await get_user_language(message.from_user.id)
    text = "🏠 Bosh menyuga xush kelibsiz!" if user_lang == "uz" else "🏠 Добро пожаловать в главное меню!"
    await message.answer(text, reply_markup=get_client_main_menu(user_lang))
