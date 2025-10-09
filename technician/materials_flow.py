# handlers/technician/materials_flow.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from filters.role_filter import RoleFilter
from database.basic.user import find_user_by_telegram_id
from .shared_utils import (
    t, resolve_lang, esc, _fmt_price_uzs, _short, _qty_of,
    _preserve_mode_clear, get_application_number, short_view_text,
    _safe_edit
)
from .shared_states import QtyStates, CustomQtyStates
from database.technician import (
    fetch_technician_materials,
    fetch_all_materials,
    fetch_material_by_id,
    fetch_assigned_qty,
    upsert_material_selection,
    upsert_material_request_and_decrease_stock,
    create_material_issued_from_review,
    send_selection_to_warehouse,
    fetch_selected_materials_for_request,
)
import asyncpg
from config import settings
import logging

logger = logging.getLogger(__name__)

# ====== Router ======
router = Router()
router.message.filter(RoleFilter("technician"))
router.callback_query.filter(RoleFilter("technician"))

# =====================
# Keyboard Generators
# =====================
def materials_keyboard(materials: list[dict], applications_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    rows = []
    if materials:
        for mat in materials:
            name = _short(mat.get('name', 'NO NAME'))
            price = _fmt_price_uzs(mat.get('price', 0))
            stock = mat.get('stock_quantity', '0')
            title = f"📦 {name} — {price} so'm ({stock} dona)" if lang == "uz" else f"📦 {name} — {price} сум ({stock} шт)"
            rows.append([InlineKeyboardButton(
                text=title[:64],
                callback_data=f"tech_mat_select_{mat.get('material_id')}_{applications_id}"
            )])
    rows.append([InlineKeyboardButton(text=("➕ Boshqa mahsulot" if lang == "uz" else "➕ Другой материал"),
                                      callback_data=f"tech_mat_custom_{applications_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def unassigned_materials_keyboard(materials: list[dict], applications_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Texnikka biriktirilmagan materiallar uchun keyboard"""
    rows = []
    if materials:
        for mat in materials:
            name = _short(mat.get('name', 'NO NAME'))
            price = _fmt_price_uzs(mat.get('price', 0))
            stock = mat.get('stock_quantity', '0')
            title = f"📦 {name} — {price} so'm ({stock} dona)" if lang == "uz" else f"📦 {name} — {price} сум ({stock} шт)"
            rows.append([InlineKeyboardButton(
                text=title[:64],
                callback_data=f"tech_unassigned_select_{mat.get('material_id')}_{applications_id}"
            )])
    rows.append([InlineKeyboardButton(text=("⬅️ Orqaga" if lang == "uz" else "⬅️ Назад"),
                                      callback_data=f"tech_back_to_materials_{applications_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# =====================
# Material Selection Handlers
# =====================
@router.callback_query(F.data.startswith("tech_mat_select_"))
async def tech_mat_select(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        payload = cb.data[len("tech_mat_select_"):]
        parts = payload.split("_")
        if len(parts) != 2:
            raise ValueError("Invalid format")
        material_id, req_id = map(int, parts)
    except Exception:
        return await cb.answer(t("format_err", lang), show_alert=True)

    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mat = await fetch_material_by_id(material_id)
    if not mat:
        return await cb.answer(t("not_found_mat", lang), show_alert=True)

    assigned_left = await fetch_assigned_qty(user["id"], material_id)
    assigned_left = int(assigned_left or 0)

    # Source type ni aniqlash - texnikda bor yoki ombordan so'rash
    source_type = "technician_stock" if assigned_left > 0 else "warehouse"

    # Avvalgi xabardagi inline keyboard'ni tozalash
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass  # Agar edit qila olmasa, davom etamiz

    # Application number ni olish
    mode = st.get("tech_mode", "connection")
    app_number = await get_application_number(req_id, mode)
    
    text = (
        f"{t('enter_qty', lang)}\n\n"
        f"{t('order_id', lang)} {esc(app_number)}\n"
        f"{t('chosen_prod', lang)} {esc(mat['name'])}\n"
        f"{t('price', lang)} {_fmt_price_uzs(mat['price'])} {'so\'m' if lang=='uz' else 'сум'}\n"
        f"{t('assigned_left', lang)} {assigned_left} {'dona' if lang=='uz' else 'шт'}\n\n"
        + t("enter_qty_hint", lang, max=assigned_left)
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=f"tech_qty_cancel_{req_id}")]
    ])

    await state.update_data(
        qty_ctx={
            "applications_id": req_id,
            "material_id": material_id,
            "material_name": mat["name"],
            "price": mat["price"],
            "max_qty": assigned_left,
            "lang": lang,
            "qty_message_id": None,  # Miqdor xabari ID'si
            "source_type": source_type,  # Material manbai
        }
    )

    qty_message = await cb.message.answer(text, reply_markup=kb, parse_mode="HTML")
    
    # Miqdor xabari ID'sini saqlash
    await state.update_data(
        qty_ctx={
            "applications_id": req_id,
            "material_id": material_id,
            "material_name": mat["name"],
            "price": mat["price"],
            "max_qty": assigned_left,
            "lang": lang,
            "qty_message_id": qty_message.message_id,
            "source_type": source_type,  # Material manbai
        }
    )
    
    await state.set_state(QtyStates.waiting_qty)
    await cb.answer()

@router.callback_query(F.data.startswith("tech_qty_cancel_"))
async def tech_qty_cancel(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_qty_cancel_", ""))
    except Exception:
        return await cb.answer()

    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mode = st.get("tech_mode", "connection")
    
    # 🟢 YANGI YONDASHUV: To'g'ridan-to'g'ri DB'dan olish
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        if mode == "technician":
            query = """
                SELECT * FROM technician_orders 
                WHERE id = $1
            """
        elif mode == "staff":
            query = """
                SELECT * FROM staff_orders 
                WHERE id = $1
            """
        else:
            query = """
                SELECT * FROM connection_orders 
                WHERE id = $1
            """
        
        item = await conn.fetchrow(query, req_id)
        
        if not item:
            return await cb.answer(
                "❌ Ariza topilmadi" if lang == "uz" else "❌ Заявка не найдена",
                show_alert=True
            )
        
        item = dict(item)
        
    finally:
        await conn.close()
    
    # Materiallar ro'yxatini olish
    mats = await fetch_technician_materials(user_id=user["id"])
    
    # Ariza ma'lumotlarini ko'rsatish
    text = short_view_text(item, 0, 1, lang, mode)
    
    materials_text = "\n\n📦 <b>Ombor jihozlari</b>\n"
    materials_text += "Kerakli jihozlarni tanlang yoki boshqa mahsulot kiriting:\n\n"
    
    if mats:
        for mat in mats:
            name = _short(mat.get('name', 'NO NAME'))
            price = _fmt_price_uzs(mat.get('price', 0))
            stock = mat.get('stock_quantity', '0')
            materials_text += f"📦 {name} — {price} so'm ({stock} dona)\n"
    else:
        materials_text += "• Texnikda materiallar yo'q\n"
    
    full_text = text + materials_text
    kb = materials_keyboard(mats, applications_id=req_id, lang=lang)
    
    await _safe_edit(cb.message, full_text, kb)
    await _preserve_mode_clear(state)
    await cb.answer(t("state_cleared", lang))

@router.message(StateFilter(QtyStates.waiting_qty))
async def tech_qty_entered(msg: Message, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(msg.from_user.id)
    user = await find_user_by_telegram_id(msg.from_user.id)
    if not user or user.get("role") != "technician":
        return await msg.answer(t("no_perm", lang))

    ctx = st.get("qty_ctx") or {}
    req_id = int(ctx.get("applications_id", 0))
    material_id = int(ctx.get("material_id", 0))
    max_qty = int(ctx.get("max_qty", 0))
    qty_message_id = ctx.get("qty_message_id")
    source_type = ctx.get("source_type", "warehouse")

    try:
        qty = int((msg.text or "").strip())
        if qty <= 0:
            return await msg.answer(t("gt_zero", lang))
    except Exception:
        return await msg.answer(t("only_int", lang))

    if qty > max_qty:
        return await msg.answer(t("max_exceeded", lang, max=max_qty))

    # Miqdor xabari inline keyboard'ni tozalash
    if qty_message_id:
        try:
            await msg.bot.edit_message_reply_markup(
                chat_id=msg.chat.id,
                message_id=qty_message_id,
                reply_markup=None
            )
        except Exception:
            pass  # Agar edit qila olmasa, davom etamiz

    # Faqat tanlov saqlansin, material_requests ga yozilmasin
    # Yakunlashda barcha tanlangan materiallar yoziladi
    try:
        mode = st.get("tech_mode", "connection")
        await upsert_material_selection(
            user_id=user["id"],
            applications_id=req_id,
            material_id=material_id,
            qty=qty,
            request_type=mode,
            source_type=source_type
        )
    except ValueError as ve:
        return await msg.answer(f"❌ {ve}")
    except Exception as e:
        return await msg.answer(f"{t('x_error', lang)} {e}")

    # 🟢 YANGI YONDASHUV: To'g'ridan-to'g'ri DB'dan olish
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        if mode == "technician":
            query = """
                SELECT * FROM technician_orders 
                WHERE id = $1
            """
        elif mode == "staff":
            query = """
                SELECT * FROM staff_orders 
                WHERE id = $1
            """
        else:
            query = """
                SELECT * FROM connection_orders 
                WHERE id = $1
            """
        
        item = await conn.fetchrow(query, req_id)
        
        if not item:
            return await msg.answer(
                "❌ Ariza topilmadi" if lang == "uz" else "❌ Заявка не найдена"
            )
        
        item = dict(item)
        
    finally:
        await conn.close()
    
    # Build text with order details + selected materials
    original_text = short_view_text(item, 0, 1, lang, mode)
    
    selected = await fetch_selected_materials_for_request(user["id"], req_id)
    materials_text = "\n\n📦 <b>Ishlatilayotgan mahsulotlar:</b>\n"
    
    if selected:
        for it in selected:
            qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
            price_txt = f"{_fmt_price_uzs(it['price'])} {'so\'m' if lang=='uz' else 'сум'}"
            materials_text += f"• {esc(it['name'])} — {qty_txt} (💰 {price_txt})\n"
    else:
        materials_text += "• (tanlanmagan)\n"
    
    # Combine original text with materials
    full_text = original_text + materials_text

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("add_more", lang), callback_data=f"tech_add_more_{req_id}")],
        [InlineKeyboardButton(text=t("final_view", lang), callback_data=f"tech_review_{req_id}")]
    ])
    
    # Always send new message instead of editing
    await msg.answer(full_text, reply_markup=kb, parse_mode="HTML")
    
    await _preserve_mode_clear(state)

@router.callback_query(F.data.startswith("tech_back_to_materials_"))
async def tech_back_to_materials(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_back_to_materials_", ""))
    except Exception:
        return await cb.answer()
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mode = st.get("tech_mode", "connection")
    
    # 🟢 YANGI YONDASHUV: To'g'ridan-to'g'ri DB'dan olish
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        if mode == "technician":
            query = """
                SELECT * FROM technician_orders 
                WHERE id = $1
            """
        elif mode == "staff":
            query = """
                SELECT * FROM staff_orders 
                WHERE id = $1
            """
        else:
            query = """
                SELECT * FROM connection_orders 
                WHERE id = $1
            """
        
        item = await conn.fetchrow(query, req_id)
        
        if not item:
            return await cb.answer(
                "❌ Ariza topilmadi" if lang == "uz" else "❌ Заявка не найдена",
                show_alert=True
            )
        
        item = dict(item)
        
    finally:
        await conn.close()
    
    # Restore original text with [Ombor] [Yakuniy ko'rinish] buttons
    original_text = short_view_text(item, 0, 1, lang, mode)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("warehouse", lang), callback_data=f"tech_add_more_{req_id}"),
            InlineKeyboardButton(text=t("review", lang), callback_data=f"tech_review_{req_id}"),
        ]
    ])
    
    await _safe_edit(cb.message, original_text, kb)
    await cb.answer()

@router.callback_query(F.data.startswith("tech_add_more_"))
async def tech_add_more(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    req_id = int(cb.data.replace("tech_add_more_", ""))
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    mode = st.get("tech_mode", "connection")
    
    # 🟢 YANGI YONDASHUV: To'g'ridan-to'g'ri DB'dan olish
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        if mode == "technician":
            query = """
                SELECT * FROM technician_orders 
                WHERE id = $1
            """
        elif mode == "staff":
            query = """
                SELECT * FROM staff_orders 
                WHERE id = $1
            """
        else:
            query = """
                SELECT * FROM connection_orders 
                WHERE id = $1
            """
        
        item = await conn.fetchrow(query, req_id)
        
        if not item:
            return await cb.answer(
                "❌ Ariza topilmadi" if lang == "uz" else "❌ Заявка не найдена",
                show_alert=True
            )
        
        item = dict(item)
        
    finally:
        await conn.close()
    
    # Build text with order details + materials list
    original_text = short_view_text(item, 0, 1, lang, mode)
    
    # Get technician's materials only
    mats = await fetch_technician_materials(user_id=user["id"])
    
    # Add materials list to text
    materials_text = "\n\n📦 <b>Ombor jihozlari</b>\n"
    materials_text += "Kerakli jihozlarni tanlang yoki boshqa mahsulot kiriting:\n\n"
    
    if mats:
        for mat in mats:
            name = _short(mat.get('name', 'NO NAME'))
            price = _fmt_price_uzs(mat.get('price', 0))
            stock = mat.get('stock_quantity', '0')
            materials_text += f"📦 {name} — {price} so'm ({stock} dona)\n"
    else:
        materials_text += "• Texnikda materiallar yo'q\n"
    
    # Combine original text with materials
    full_text = original_text + materials_text
    
    # Edit existing message with materials keyboard
    kb = materials_keyboard(mats, applications_id=req_id, lang=lang)
    await _safe_edit(cb.message, full_text, kb)
    # Store message ID for later editing
    await state.update_data(original_message_id=cb.message.message_id)
    await cb.answer()

@router.callback_query(F.data.startswith("tech_review_"))
async def tech_review(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    req_id = int(cb.data.replace("tech_review_", ""))    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    # Application number ni olish
    mode = st.get("tech_mode", "connection")
    app_number = await get_application_number(req_id, mode)
    
    # Material_issued ga yozish
    try:
        await create_material_issued_from_review(user["id"], req_id, mode)
    except Exception as e:
        logger.error(f"Error creating material_issued: {e}")
    
    # 🟢 YANGI YONDASHUV: To'g'ridan-to'g'ri DB'dan olish
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        if mode == "technician":
            query = """
                SELECT * FROM technician_orders 
                WHERE id = $1
            """
        elif mode == "staff":
            query = """
                SELECT * FROM staff_orders 
                WHERE id = $1
            """
        else:
            query = """
                SELECT * FROM connection_orders 
                WHERE id = $1
            """
        
        item = await conn.fetchrow(query, req_id)
        
        if not item:
            return await cb.answer(
                "❌ Ariza topilmadi" if lang == "uz" else "❌ Заявка не найдена",
                show_alert=True
            )
        
        item = dict(item)
        
    finally:
        await conn.close()
    
    # Build text with order details + materials list
    original_text = short_view_text(item, 0, 1, lang, mode)
    
    selected = await fetch_selected_materials_for_request(user["id"], req_id)
    materials_text = "\n\n📦 <b>Ishlatilgan mahsulotlar:</b>\n"
    
    if selected:
        for it in selected:
            qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
            price_txt = f"{_fmt_price_uzs(it['price'])} {'so\'m' if lang=='uz' else 'сум'}"
            # Source indicator
            source_indicator = ""
            if it.get('source_type') == 'technician_stock':
                source_indicator = " [🧑‍🔧 O'zimda]" if lang == 'uz' else " [🧑‍🔧 У меня]"
            elif it.get('source_type') == 'warehouse':
                source_indicator = " [🏢 Ombordan]" if lang == 'uz' else " [🏢 Со склада]"
            materials_text += f"• {esc(it['name'])} — {qty_txt} (💰 {price_txt}){source_indicator}\n"
    else:
        materials_text += "• (tanlanmagan)\n"
    
    # Check if there are warehouse materials that need confirmation
    warehouse_mats = [m for m in selected if m.get('source_type') == 'warehouse']
    
    if warehouse_mats:
        # Show warehouse confirmation dialog
        warehouse_text = "\n\n🏢 <b>Ombordan so'ralgan mahsulotlar:</b>\n"
        for mat in warehouse_mats:
            qty_txt = f"{_qty_of(mat)} {'dona' if lang=='uz' else 'шт'}"
            warehouse_text += f"• {esc(mat['name'])} — {qty_txt}\n"
        warehouse_text += "\n\nOmborga yuborish tasdiqlaysizmi?"
        
        full_text = original_text + materials_text + warehouse_text
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"tech_confirm_warehouse_{req_id}")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"tech_back_to_materials_{req_id}")]
        ])
    else:
        # No warehouse materials, show regular buttons
        full_text = original_text + materials_text
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("finish", lang), callback_data=f"tech_finish_{req_id}")],
            [InlineKeyboardButton(text=t("cancel_order", lang), callback_data=f"tech_cancel_order_{req_id}")],
            [InlineKeyboardButton(text=t("back", lang), callback_data=f"tech_back_to_materials_{req_id}")]
        ])
    
    await cb.message.answer(full_text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()

@router.callback_query(F.data.startswith("tech_confirm_warehouse_"))
async def tech_confirm_warehouse(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data()
    lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    req_id = int(cb.data.replace("tech_confirm_warehouse_", ""))
    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    mode = st.get("tech_mode", "connection")
    
    # Send to warehouse
    try:
        success = await send_selection_to_warehouse(
            applications_id=req_id,
            technician_user_id=user["id"],
            request_type=mode
        )
        
        if success:
            # Show finish/cancel/back buttons
            # 🟢 YANGI YONDASHUV: To'g'ridan-to'g'ri DB'dan olish
            conn = await asyncpg.connect(settings.DB_URL)
            try:
                if mode == "technician":
                    query = """
                        SELECT * FROM technician_orders 
                        WHERE id = $1
                    """
                elif mode == "staff":
                    query = """
                        SELECT * FROM staff_orders 
                        WHERE id = $1
                    """
                else:
                    query = """
                        SELECT * FROM connection_orders 
                        WHERE id = $1
                    """
                
                item = await conn.fetchrow(query, req_id)
                
                if not item:
                    return await cb.answer(
                        "❌ Ariza topilmadi" if lang == "uz" else "❌ Заявка не найдена",
                        show_alert=True
                    )
                
                item = dict(item)
                
            finally:
                await conn.close()
            
            # Build text with order details + materials list
            original_text = short_view_text(item, 0, 1, lang, mode)
            
            selected = await fetch_selected_materials_for_request(user["id"], req_id)
            materials_text = "\n\n📦 <b>Ishlatilgan mahsulotlar:</b>\n"
            
            if selected:
                for it in selected:
                    qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
                    price_txt = f"{_fmt_price_uzs(it['price'])} {'so\'m' if lang=='uz' else 'сум'}"
                    # Source indicator
                    source_indicator = ""
                    if it.get('source_type') == 'technician_stock':
                        source_indicator = " [🧑‍🔧 O'zimda]" if lang == 'uz' else " [🧑‍🔧 У меня]"
                    elif it.get('source_type') == 'warehouse':
                        source_indicator = " [🏢 Ombordan]" if lang == 'uz' else " [🏢 Со склада]"
                    materials_text += f"• {esc(it['name'])} — {qty_txt} (💰 {price_txt}){source_indicator}\n"
            else:
                materials_text += "• (tanlanmagan)\n"
            
            full_text = original_text + materials_text + "\n\n✅ Omborga yuborildi!"
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t("finish", lang), callback_data=f"tech_finish_{req_id}")],
                [InlineKeyboardButton(text=t("cancel_order", lang), callback_data=f"tech_cancel_order_{req_id}")],
                [InlineKeyboardButton(text=t("back", lang), callback_data=f"tech_back_to_materials_{req_id}")]
            ])
            
            await cb.message.answer(full_text, reply_markup=kb, parse_mode="HTML")
            try:
                await cb.answer("✅ Omborga yuborildi!")
            except Exception:
                pass  # Ignore callback timeout errors
        else:
            try:
                await cb.answer("❌ Xatolik yuz berdi", show_alert=True)
            except Exception:
                pass  # Ignore callback timeout errors
    except Exception as e:
        logger.error(f"Error sending to warehouse: {e}")
        try:
            await cb.answer("❌ Xatolik yuz berdi", show_alert=True)
        except Exception:
            pass  # Ignore callback timeout errors

@router.callback_query(F.data.startswith("tech_mat_custom_"))
async def tech_mat_custom(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_mat_custom_", ""))
    except Exception:
        return
    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    # Get all materials (25 total) and filter out technician's materials (7 items)
    # Result: 18 materials from warehouse only
    all_mats = await fetch_all_materials(limit=200, offset=0)
    tech_mats = await fetch_technician_materials(user_id=user["id"])
    
    # Get technician's material IDs
    tech_material_ids = {mat['material_id'] for mat in tech_mats}
    
    # Filter out materials that technician already has
    warehouse_mats = [mat for mat in all_mats if mat['material_id'] not in tech_material_ids]
    
    if not warehouse_mats:
        return await cb.message.answer(
            ("📦 Ombordan qo'shimcha materiallar yo'q" if lang == "uz" else "📦 Нет дополнительных материалов на складе"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t("back", lang), callback_data=f"tech_back_to_materials_{req_id}")]
            ])
        )

    # Application number ni olish
    mode = st.get("tech_mode", "connection")
    app_number = await get_application_number(req_id, mode)
    
    header_text = ("📦 <b>Ombordan qo'shimcha materiallar</b>\n🆔 <b>Ariza ID:</b> {id}\nKerakli materialni tanlang:" if lang == "uz" else "📦 <b>Дополнительные материалы со склада</b>\n🆔 <b>ID заявки:</b> {id}\nВыберите нужный материал:")
    
    # Edit existing message instead of sending new one
    await _safe_edit(
        cb.message, 
        header_text.format(id=app_number), 
        unassigned_materials_keyboard(warehouse_mats, applications_id=req_id, lang=lang)
    )

@router.callback_query(F.data.startswith("tech_unassigned_select_"))
async def tech_unassigned_select(cb: CallbackQuery, state: FSMContext):
    """Texnikka biriktirilmagan materialni tanlash"""
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        payload = cb.data[len("tech_unassigned_select_"):]
        material_id, req_id = map(int, payload.split("_", 1))
    except Exception:
        return

    mat = await fetch_material_by_id(material_id)
    if not mat:
        return await cb.answer(t("not_found_mat", lang), show_alert=True)

    mode = st.get("tech_mode", "connection")
    app_number = await get_application_number(req_id, mode)
    
    text = (
        f"📦 <b>{t('product', lang)}:</b> {esc(mat['name'])}\n"
        f"💰 <b>{t('price_line', lang)}:</b> {_fmt_price_uzs(mat.get('price',0))} {'so\'m' if lang=='uz' else 'сум'}\n"
        f"🆔 <b>{t('order', lang)}:</b> {esc(app_number)}\n\n"
        f"{'Miqdorini kiriting:' if lang=='uz' else 'Введите количество:'}"
    )
    
    await state.update_data(
        qty_ctx={
            "applications_id": req_id,
            "material_id": material_id,
            "material_name": mat["name"],
            "price": mat["price"],
            "max_qty": 999,  
            "lang": lang,
            "source_type": "warehouse",
            "qty_message_id": cb.message.message_id  
        }
    )
    
    # Show quantity input prompt with cancel button
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=f"tech_qty_cancel_{req_id}")]
    ])
    
    await cb.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(QtyStates.waiting_qty)

@router.message(StateFilter(CustomQtyStates.waiting_qty))
async def custom_qty_entered(msg: Message, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(msg.from_user.id)
    user = await find_user_by_telegram_id(msg.from_user.id)
    if not user or user.get("role") != "technician":
        return await msg.answer(t("no_perm", lang))

    # Texnikka biriktirilmagan materiallar uchun alohida kontekst
    unassigned_ctx = st.get("unassigned_ctx")
    if unassigned_ctx:
        req_id = int(unassigned_ctx.get("applications_id", 0))
        material_id = int(unassigned_ctx.get("material_id", 0))
        material_name = unassigned_ctx.get("material_name", "")
        
        try:
            qty = int((msg.text or "").strip())
            if qty <= 0:
                return await msg.answer(t("gt_zero", lang))
        except Exception:
            return await msg.answer(t("only_int", lang))

        # Texnikka biriktirilmagan material uchun faqat tanlov saqlash
        try:
            mode = st.get("tech_mode", "connection")
            await upsert_material_selection(
                user_id=user["id"],
                applications_id=req_id,
                material_id=material_id,
                qty=qty,
                request_type=mode,
                source_type="warehouse"  # Unassigned materials are from warehouse
            )
        except Exception as e:
            return await msg.answer(f"{t('x_error', lang)} {e}")

        # Application number ni olish
        mode = st.get("tech_mode", "connection")
        app_number = await get_application_number(req_id, mode)
        
        # Xabar yuborish
        await msg.answer(
            f"✅ <b>Material omborga so'rov yuborildi</b>\n\n"
            f"📦 <b>Material:</b> {esc(material_name)}\n"
            f"📊 <b>Miqdor:</b> {qty} {'dona' if lang=='uz' else 'шт'}\n"
            f"🆔 <b>Ariza ID:</b> {esc(app_number)}\n\n"
            f"{'Omborchi tasdiqlagandan so\'ng material texnikka biriktiriladi' if lang=='uz' else 'После подтверждения склада материал будет привязан к технику'}\n\n"
            f"{'Yana material qo\'shish uchun \"Ombor\" tugmasini bosing' if lang=='uz' else 'Для добавления ещё материалов нажмите кнопку \"Склад\"'}",
            parse_mode="HTML"
        )
        
        await _preserve_mode_clear(state)
        return

    # Oddiy custom materiallar uchun eski mantiq
    ctx  = st.get("custom_ctx") or {}
    req_id      = int(ctx.get("applications_id", 0))
    material_id = int(ctx.get("material_id", 0))
    if not (req_id and material_id):
        await _preserve_mode_clear(state)
        return await msg.answer(t("ctx_lost", lang))

    try:
        qty = int((msg.text or "").strip())
        if qty <= 0:
            return await msg.answer(t("gt_zero", lang))
    except Exception:
        return await msg.answer(t("only_int", lang))

    mode = st.get("tech_mode", "connection")
    request_type = "technician" if mode == "technician" else ("staff" if mode == "staff" else "connection")

    # Faqat tanlov saqlansin, omborga yuborilmasin
    # Yakunlashda barcha materiallar omborga yuboriladi
    try:
        mode = st.get("tech_mode", "connection")
        await upsert_material_selection(
            user_id=user["id"],
            applications_id=req_id,
            material_id=material_id,
            qty=qty,
            request_type=mode,
            source_type="warehouse"  # Custom materials are from warehouse
        )
    except Exception as e:
        return await msg.answer(f"{t('x_error', lang)} {e}")

    # Application number ni olish
    mode = st.get("tech_mode", "connection")
    app_number = await get_application_number(req_id, mode)
    
    # Tanlangan materiallarni ko'rsatish
    selected = await fetch_selected_materials_for_request(user["id"], req_id)
    lines = [t("saved_selection", lang) + "\n", f"{t('order_id', lang)} {esc(app_number)}", t("selected_products", lang)]
    for it in selected:
        qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
        price_txt = f"{_fmt_price_uzs(it['price'])} {'so\'m' if lang=='uz' else 'сум'}"
        lines.append(f"• {esc(it['name'])} — {qty_txt} (💰 {price_txt})")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("add_more", lang), callback_data=f"tech_add_more_{req_id}")],
        [InlineKeyboardButton(text=t("final_view", lang), callback_data=f"tech_review_{req_id}")]
    ])
    
    await _preserve_mode_clear(state)
    await msg.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")
