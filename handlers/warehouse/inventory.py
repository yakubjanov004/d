# handlers/inventory.py
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from decimal import Decimal, InvalidOperation

from filters.role_filter import RoleFilter
from keyboards.warehouse_buttons import (
    get_warehouse_main_menu,
    get_inventory_actions_keyboard,
)
from states.warehouse_states import WarehouseStates, AddMaterialStates, UpdateMaterialStates
from database.warehouse.materials import (
    create_material,
    search_materials,
    get_all_materials,
    get_material_by_id,
    update_material_quantity,
    update_material_name_description,
    get_low_stock_materials,
    get_out_of_stock_materials
)

router = Router()
router.message.filter(RoleFilter("warehouse"))

class SearchMaterialStates(StatesGroup):
    query = State()

def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )

def fmt_sum(val: Decimal | int | float | None) -> str:
    if val is None:
        return "0"
    return f"{Decimal(val):,.0f}".replace(",", " ")

# Inventarizatsiya menyusiga kirish
@router.message(F.text.in_(["📦 Inventarizatsiya", "📦 Инвентаризация"]))
async def inventory_handler(message: Message, state: FSMContext):
    await state.set_state(WarehouseStates.inventory_menu)
    await message.answer("📦 Inventarizatsiya boshqaruvi", reply_markup=get_inventory_actions_keyboard("uz"))

# Orqaga (faqat inventarizatsiya holatida)
@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["◀️ Orqaga", "🔙 Orqaga", "◀️ Назад", "Orqaga"]))
async def inventory_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⬅️ Asosiy menyu", reply_markup=get_warehouse_main_menu("uz"))

# ============== ➕ Mahsulot qo'shish oqimi ==============

@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["➕ Mahsulot qo'shish", "➕ Добавить товар"]))
async def inv_add_start(message: Message, state: FSMContext):
    # Tanlov menyusini ko'rsatish
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 Yangi mahsulot qo'shish")],
            [KeyboardButton(text="📦 Mavjud mahsulot sonini o'zgartirish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "➕ Mahsulot qo'shish\n\n"
        "Quyidagilardan birini tanlang:",
        reply_markup=keyboard
    )

# Yangi mahsulot qo'shish
@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["🆕 Yangi mahsulot qo'shish"]))
async def inv_add_new_start(message: Message, state: FSMContext):
    await state.set_state(AddMaterialStates.name)
    await message.answer("🏷️ Mahsulot nomini kiriting:", reply_markup=cancel_kb())

# Mavjud mahsulot sonini o'zgartirish
@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["📦 Mavjud mahsulot sonini o'zgartirish"]))
async def inv_update_existing_start(message: Message, state: FSMContext):
    await state.set_state(UpdateMaterialStates.search)
    await message.answer("🔎 Miqdorini o'zgartirmoqchi bo'lgan mahsulot nomini kiriting:", reply_markup=cancel_kb())

@router.message(StateFilter(AddMaterialStates.name))
async def inv_add_name(message: Message, state: FSMContext):
    if message.text.strip().lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    name = message.text.strip()
    if len(name) < 2:
        return await message.answer("❗ Nomi juda qisqa. Qaytadan kiriting:")

    await state.update_data(name=name)
    await state.set_state(AddMaterialStates.quantity)
    await message.answer("📦 Miqdorni kiriting (butun son):")

@router.message(StateFilter(AddMaterialStates.quantity))
async def inv_add_quantity(message: Message, state: FSMContext):
    txt = message.text.strip()
    if txt.lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    if not txt.isdigit():
        return await message.answer("❗ Faqat butun son kiriting. Qayta kiriting:")

    qty = int(txt)
    if qty < 0:
        return await message.answer("❗ Miqdor manfiy bo‘lishi mumkin emas. Qayta kiriting:")

    await state.update_data(quantity=qty)
    await state.set_state(AddMaterialStates.price)
    await message.answer("💰 Narxni kiriting (so'm) — butun son yoki 100000.00 ko‘rinishida:")

@router.message(StateFilter(AddMaterialStates.price))
async def inv_add_price(message: Message, state: FSMContext):
    txt = message.text.strip()
    if txt.lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    # vergul/bo‘shliqni tozalash
    norm = txt.replace(" ", "").replace(",", ".")
    try:
        price = Decimal(norm)
        if price < 0:
            return await message.answer("❗ Narx manfiy bo‘lishi mumkin emas. Qayta kiriting:")
    except InvalidOperation:
        return await message.answer("❗ Noto‘g‘ri format. Masalan: 500000 yoki 500000.00. Qayta kiriting:")

    await state.update_data(price=price)
    await state.set_state(AddMaterialStates.description)
    await message.answer("📝 Mahsulot tavsifi kiriting (ixtiyoriy, o‘tkazib yuborish uchun “-” yozing):")

@router.message(StateFilter(AddMaterialStates.description))
async def inv_add_description(message: Message, state: FSMContext):
    txt = message.text.strip()
    if txt.lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    description = None if txt in ("-", "") else txt

    data = await state.get_data()
    name = data["name"]
    qty = data["quantity"]
    price = data["price"]

    try:
        created = await create_material(
            name=name,
            quantity=qty,
            price=price,
            description=description,
            serial_number=None  # hozircha kiritmaymiz
        )
    except Exception as e:
        # DB xatosi
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer(f"❌ Xatolik: ma'lumot bazaga yozilmadi.\nDetails: {e}\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    # Muvaffaqiyat
    await state.set_state(WarehouseStates.inventory_menu)
    await message.answer(
        "✅ Mahsulot muvaffaqiyatli qo‘shildi!\n"
        f"🏷️ Nom: <b>{created['name']}</b>\n"
        f"📦 Miqdor: <b>{created['quantity']}</b>\n"
        f"💰 Narx: <b>{fmt_sum(created['price'])} so'm</b>",
        parse_mode="HTML",
    )
    await message.answer("📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

# ============== ✏️ Mahsulotni yangilash oqimi ==============

@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["✏️ Mahsulotni yangilash", "✏️ Обновить товар"]))
async def inv_update_start(message: Message, state: FSMContext):
    await state.set_state(UpdateMaterialStates.search)
    await message.answer("🔎 Yangilamoqchi bo'lgan mahsulot nomini kiriting:", reply_markup=cancel_kb())

@router.message(StateFilter(UpdateMaterialStates.search))
async def inv_update_search(message: Message, state: FSMContext):
    if message.text.strip().lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    search_term = message.text.strip()
    if len(search_term) < 2:
        return await message.answer("❗ Qidiruv so'zi juda qisqa. Qaytadan kiriting:")

    try:
        materials = await search_materials(search_term)
        if not materials:
            return await message.answer("❌ Hech qanday mahsulot topilmadi. Boshqa nom bilan qidiring:")

        # Mahsulotlar ro'yxatini ko'rsatish
        text = "📋 Topilgan mahsulotlar:\n\n"
        keyboard_buttons = []
        
        for i, material in enumerate(materials[:10], 1):  # faqat 10 tasini ko'rsatamiz
            text += f"{i}. <b>{material['name']}</b>\n"
            text += f"   📦 Miqdor: {material['quantity']}\n"
            text += f"   💰 Narx: {fmt_sum(material['price'])} so'm\n\n"
            keyboard_buttons.append([KeyboardButton(text=f"{i}. {material['name']}")])
        
        keyboard_buttons.append([KeyboardButton(text="❌ Bekor qilish")])
        keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
        
        await state.update_data(materials=materials)
        await state.set_state(UpdateMaterialStates.select)
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        await message.answer("👆 Yuqoridagi ro'yxatdan kerakli mahsulotni tanlang:")
        
    except Exception as e:
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer(f"❌ Xatolik: {e}\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

# ============== 📄 Barcha mahsulotlar ==============

@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["📄 Barcha mahsulotlar", "📄 Все товары"]))
async def inv_all_materials(message: Message, state: FSMContext):
    try:
        materials = await get_all_materials()
        if not materials:
            return await message.answer("📄 Hozircha hech qanday mahsulot yo'q.")
        
        # Paginatsiya uchun ma'lumotlarni saqlash
        await state.update_data(all_materials=materials, current_page=0)
        
        # Birinchi sahifani ko'rsatish
        await show_materials_page(message, materials, 0, state)
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

async def show_materials_page(message: Message, materials: list, page: int, state: FSMContext):
    """Mahsulotlarni sahifa bo'yicha ko'rsatish"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    items_per_page = 7
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_materials = materials[start_idx:end_idx]
    
    total_pages = (len(materials) + items_per_page - 1) // items_per_page
    
    text = f"📄 Barcha mahsulotlar (Sahifa {page + 1}/{total_pages}):\n\n"
    
    for i, material in enumerate(page_materials, start=start_idx + 1):
        text += f"{i}. <b>{material['name']}</b>\n"
        text += f"   📦 Miqdor: {material['quantity']}\n"
        text += f"   💰 Narx: {fmt_sum(material['price'])} so'm\n"
        if material.get('description'):
            text += f"   📝 Tavsif: {material['description']}\n"
        text += "\n"
    
    # Paginatsiya tugmalari
    buttons = []
    
    if len(materials) > items_per_page:
        if page > 0:
            buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"materials_page_{page-1}"))
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"materials_page_{page+1}"))
    
    keyboard_rows = []
    if buttons:
        keyboard_rows.append(buttons)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    try:
        await message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except:
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# Paginatsiya callback handlerlari

@router.callback_query(F.data.startswith('materials_page_'))
async def materials_pagination_handler(callback_query: CallbackQuery, state: FSMContext):
    """Paginatsiya tugmalarini boshqarish"""
    try:
        page = int(callback_query.data.split('_')[-1])
        data = await state.get_data()
        materials = data.get('all_materials', [])
        
        await state.update_data(current_page=page)
        await show_materials_page(callback_query.message, materials, page, state)
        await callback_query.answer()
        
    except Exception as e:
        await callback_query.answer("❌ Xatolik yuz berdi")

# ============== 🔎 Qidirish ==============

@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["🔎 Qidirish", "🔎 Поиск"]))
async def inv_search_start(message: Message, state: FSMContext):
    # Alhida state — boshqa tugmalar bilan to‘qnashmaydi
    await state.set_state(SearchMaterialStates.query)
    await message.answer("🔎 Qidirmoqchi bo'lgan mahsulot nomini kiriting:", reply_markup=cancel_kb())

@router.message(StateFilter(SearchMaterialStates.query))
async def inv_search_query(message: Message, state: FSMContext):
    text = message.text.strip()
    
    # Agar bekor qilish tugmasi bosilsa
    if text.lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))
    
    if len(text) < 2:
        return await message.answer("❗ Qidiruv so'zi juda qisqa. Qaytadan kiriting:")
    
    try:
        materials = await search_materials(text)
        if not materials:
            # Avvalgi xulq-atvorga mos: menyuga qaytarmaymiz, foydalanuvchi yana yozsin
            return await message.answer("❌ Hech qanday mahsulot topilmadi. Boshqa nom bilan qidiring:")
        
        result_text = f"🔎 '{text}' bo'yicha topilgan mahsulotlar:\n\n"
        for i, material in enumerate(materials, 1):
            result_text += f"{i}. <b>{material['name']}</b>\n"
            result_text += f"   📦 Miqdor: {material['quantity']}\n"
            result_text += f"   💰 Narx: {fmt_sum(material['price'])} so'm\n\n"
        
        await message.answer(result_text, parse_mode="HTML")
        await state.set_state(WarehouseStates.inventory_menu)
        await message.answer("📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
        await state.set_state(WarehouseStates.inventory_menu)
        await message.answer("📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

# ============== ⚠️ Kam zaxira ==============

@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["⚠️ Kam zaxira", "⚠️ Низкий запас"]))
async def inv_low_stock(message: Message, state: FSMContext):
    try:
        materials = await get_low_stock_materials(10)  
        
        if not materials:
            return await message.answer("✅ Barcha mahsulotlar yetarli miqdorda mavjud.")
        
        text = "⚠️ <b>Kam zaxirali mahsulotlar (10 dan kam):</b>\n\n"
        
        for i, material in enumerate(materials, 1):
            if material['quantity'] == 0:
                status_icon = "🔴"  # Tugagan
            elif material['quantity'] <= 3:
                status_icon = "🟠"  # Juda kam
            elif material['quantity'] <= 7:
                status_icon = "🟡"  # Kam
            else:
                status_icon = "⚠️"  # Ogohlantirish
            
            text += f"{status_icon} <b>{i}. {material['name']}</b>\n"
            text += f"   📦 Miqdor: <b>{material['quantity']}</b>\n"
            text += f"   💰 Narx: {fmt_sum(material['price'])} so'm\n"
            
            if material.get('description'):
                text += f"   📝 Tavsif: {material['description'][:50]}{'...' if len(material['description']) > 50 else ''}\n"
            
            text += "\n"
        
        text += f"\n📊 <b>Jami:</b> {len(materials)} ta mahsulot kam zaxiraga ega\n"
        text += "\n💡 <i>Maslahat: Ushbu mahsulotlarni tezroq to'ldiring!</i>"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

# ============== ❌ Tugagan mahsulotlar ==============

@router.message(StateFilter(WarehouseStates.inventory_menu), F.text.in_(["❌ Tugagan mahsulotlar", "❌ Закончились"]))
async def inv_out_of_stock(message: Message, state: FSMContext):
    try:
        materials = await get_out_of_stock_materials()
        if not materials:
            return await message.answer("✅ Hech qanday mahsulot tugamagan.")
        
        text = "❌ Tugagan mahsulotlar:\n\n"
        for i, material in enumerate(materials, 1):
            text += f"{i}. <b>{material['name']}</b>\n"
            text += f"   💰 Narx: {fmt_sum(material['price'])} so'm\n\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

@router.message(StateFilter(UpdateMaterialStates.select))
async def inv_update_select(message: Message, state: FSMContext):
    if message.text.strip().lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    data = await state.get_data()
    materials = data.get('materials', [])
    
    selected_material = None
    text = message.text.strip()
    
    if text.startswith(tuple(f"{i}." for i in range(1, 11))):
        try:
            index = int(text.split('.')[0]) - 1
            if 0 <= index < len(materials):
                selected_material = materials[index]
        except (ValueError, IndexError):
            pass
    
    if not selected_material:
        return await message.answer("❗ Noto'g'ri tanlov. Ro'yxatdan birini tanlang:")
    
    await state.update_data(selected_material=selected_material)
    await state.set_state(UpdateMaterialStates.quantity)
    
    await message.answer(
        f"📦 Tanlangan mahsulot: <b>{selected_material['name']}</b>\n"
        f"📊 Joriy miqdor: <b>{selected_material['quantity']}</b> dona\n\n"
        f"➕ Qo'shiladigan miqdorni kiriting (faqat musbat son):",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(StateFilter(UpdateMaterialStates.quantity))
async def inv_update_quantity(message: Message, state: FSMContext):
    if message.text.strip().lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    try:
        additional_quantity = int(message.text.strip())
        if additional_quantity <= 0:
            return await message.answer("❗ Faqat musbat son kiriting (0 dan katta):")
    except ValueError:
        return await message.answer("❗ Noto'g'ri format. Faqat son kiriting:")

    data = await state.get_data()
    selected_material = data['selected_material']
    
    try:
        updated_material = await update_material_quantity(selected_material['id'], additional_quantity)
        
        await state.set_state(WarehouseStates.inventory_menu)
        await message.answer(
            f"✅ Mahsulot miqdori muvaffaqiyatli yangilandi!\n\n"
            f"📦 Mahsulot: <b>{selected_material['name']}</b>\n"
            f"📊 Avvalgi miqdor: <b>{selected_material['quantity']}</b> dona\n"
            f"➕ Qo'shilgan: <b>{additional_quantity}</b> dona\n"
            f"📊 Yangi miqdor: <b>{updated_material['quantity']}</b> dona\n\n"
            f"📦 Inventarizatsiya menyusi:",
            parse_mode="HTML",
            reply_markup=get_inventory_actions_keyboard("uz")
        )
    except Exception as e:
        await state.set_state(WarehouseStates.inventory_menu)
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n📦 Inventarizatsiya menyusi:",
            reply_markup=get_inventory_actions_keyboard("uz")
        )

@router.message(StateFilter(UpdateMaterialStates.name))
async def inv_update_name(message: Message, state: FSMContext):
    if message.text.strip().lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    new_name = message.text.strip()
    if len(new_name) < 2:
        return await message.answer("❗ Mahsulot nomi juda qisqa. Qayta kiriting:")

    await state.update_data(new_name=new_name)
    await state.set_state(UpdateMaterialStates.description)
    
    data = await state.get_data()
    selected_material = data['selected_material']
    
    await message.answer(
        f"✏️ Yangi nom: <b>{new_name}</b>\n\n"
        f"📝 Joriy tavsif: <b>{selected_material.get('description', 'Tavsif yo\'q')}</b>\n\n"
        f"📝 Yangi tavsif kiriting (yoki 'o\'tkazib yuborish' deb yozing):",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(StateFilter(UpdateMaterialStates.description))
async def inv_update_description(message: Message, state: FSMContext):
    if message.text.strip().lower() in ("❌ bekor qilish", "bekor", "cancel"):
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer("❌ Bekor qilindi.\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))

    new_description = message.text.strip()
    if new_description.lower() in ("o'tkazib yuborish", "otkazib yuborish", "skip", "-"):
        new_description = None

    data = await state.get_data()
    selected_material = data['selected_material']
    new_name = data['new_name']
    
    try:
        updated_material = await update_material_name_description(selected_material['id'], new_name, new_description)
        
        await state.set_state(WarehouseStates.inventory_menu)
        await message.answer(
            "✅ Mahsulot ma'lumotlari muvaffaqiyatli yangilandi!\n"
            f"🏷️ Eski nom: <b>{selected_material['name']}</b>\n"
            f"🏷️ Yangi nom: <b>{updated_material['name']}</b>\n"
            f"📝 Eski tavsif: <b>{selected_material.get('description', 'Tavsif yo\'q')}</b>\n"
            f"📝 Yangi tavsif: <b>{updated_material.get('description', 'Tavsif yo\'q')}</b>\n\n"
            "📦 Inventarizatsiya menyusi:",
            parse_mode="HTML",
            reply_markup=get_inventory_actions_keyboard("uz")
        )
        
    except Exception as e:
        await state.set_state(WarehouseStates.inventory_menu)
        return await message.answer(f"❌ Xatolik: {e}\n\n📦 Inventarizatsiya menyusi:", reply_markup=get_inventory_actions_keyboard("uz"))
