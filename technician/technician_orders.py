# handlers/technician/technician_orders.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from filters.role_filter import RoleFilter
from database.basic.user import find_user_by_telegram_id
from .shared_utils import (
    t, resolve_lang, esc, _dedup_by_id, _preserve_mode_clear,
    short_view_text_with_materials, action_keyboard, render_item,
    get_current_status, get_application_number, 
    send_completion_notification_to_client
)
from .materials_flow import materials_keyboard
from .shared_states import DiagStates
from database.technician import (
    fetch_technician_inbox_tech,
    accept_technician_work_for_tech,
    start_technician_work_for_tech,
    save_technician_diagnosis,
    finish_technician_work_for_tech,
    fetch_technician_materials,
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
# Technician Orders Handlers
# =====================
@router.callback_query(F.data == "tech_inbox_cat_tech")
async def tech_cat_tech(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    items = _dedup_by_id(await fetch_technician_inbox_tech(technician_id=user["id"], limit=50, offset=0))
    await state.update_data(tech_mode="technician", tech_inbox=items, tech_idx=0, lang=lang)
    if not items:
        return await cb.message.edit_text(t("empty_tech", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
    
    await render_item(cb.message, items[0], 0, len(items), lang, "technician", user["id"])

@router.callback_query(F.data.startswith("tech_inbox_prev_"))
async def tech_prev_tech(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    mode = st.get("tech_mode", "connection")
    if mode != "technician":
        return  # Faqat technician mode uchun ishlaydi`
    
    items = _dedup_by_id(st.get("tech_inbox", []))
    if not items:
        return await cb.answer(t("empty_inbox", lang))
    total = len(items)
    idx = int(cb.data.replace("tech_inbox_prev_", "")) - 1
    if idx < 0 or idx >= total:
        return await cb.answer(t("reached_start", lang))
    await state.update_data(tech_inbox=items, tech_idx=idx)
    
    # Technician mode - rasmlar bor, render_item
    await render_item(cb.message, items[idx], idx, total, lang, mode, user["id"])

@router.callback_query(F.data.startswith("tech_inbox_next_"))
async def tech_next_tech(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    mode = st.get("tech_mode", "connection")
    if mode != "technician":
        return  # Faqat technician mode uchun ishlaydi
    
    items = _dedup_by_id(st.get("tech_inbox", []))
    if not items:
        return await cb.answer(t("empty_inbox", lang))
    total = len(items)
    idx = int(cb.data.replace("tech_inbox_next_", "")) + 1
    if idx < 0 or idx >= total:
        return await cb.answer(t("reached_end", lang))
    await state.update_data(tech_inbox=items, tech_idx=idx)
    
    # Technician mode - rasmlar bor, render_item
    await render_item(cb.message, items[idx], idx, total, lang, mode, user["id"])

@router.callback_query(F.data.startswith("tech_accept_"))
async def tech_accept_tech(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    req_id = int(cb.data.replace("tech_accept_", ""))
    try:
        ok = await accept_technician_work_for_tech(applications_id=req_id, technician_id=user["id"])
        if not ok:
            return await cb.answer(t("status_mismatch", lang), show_alert=True)
        
        # Controller'ga notification yuboramiz (texnik qabul qildi)
        try:
            from utils.notification_service import send_role_notification
            from database.basic.user import get_user_by_telegram_id
            
            # Controller'ning telegram_id ni olamiz
            controller_user = await get_user_by_telegram_id(cb.from_user.id)  # Technician ID
            if controller_user and controller_user.get('telegram_id'):
                # Notification yuborish
                await send_role_notification(
                    bot=cb.bot,
                    recipient_telegram_id=controller_user['telegram_id'],
                    order_id=f"#{req_id}",
                    order_type="technician",
                    current_load=1,  # Controller'ning hozirgi yuklamasi
                    lang=controller_user.get('language', 'uz')
                )
                logger.info(f"Notification sent to controller - technician accepted order {req_id}")
        except Exception as notif_error:
            logger.error(f"Failed to send notification to controller: {notif_error}")
            # Notification xatosi asosiy jarayonga ta'sir qilmaydi
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    items = _dedup_by_id((await state.get_data()).get("tech_inbox", []))
    idx = int((await state.get_data()).get("tech_idx", 0))
    for it in items:
        if it.get("id") == req_id:
            it["status"] = "in_technician"
            break
    await state.update_data(tech_inbox=items)
    total = len(items)
    item = items[idx] if 0 <= idx < total else items[0]
    
    # Technician mode - render_item
    await render_item(cb.message, item, idx, total, lang, mode, user["id"])
    
    await cb.answer()

@router.callback_query(F.data.startswith("tech_start_"))
async def tech_start_tech(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    req_id = int(cb.data.replace("tech_start_", ""))
    try:
        ok = await start_technician_work_for_tech(applications_id=req_id, technician_id=user["id"])
        if not ok:
            current_status = await get_current_status(req_id, mode)
            error_msg = f"⚠️ Xatolik! Avval 'Qabul qilish' tugmasini bosing.\n\n"
            error_msg += f"Joriy holat: {current_status or 'noma\'lum'}\n"
            error_msg += "Kerakli holat: in_technician"
            return await cb.answer(error_msg, show_alert=True)
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    items = _dedup_by_id((await state.get_data()).get("tech_inbox", []))
    idx = int((await state.get_data()).get("tech_idx", 0))
    for it in items:
        if it.get("id") == req_id:
            it["status"] = "in_technician_work"
            break
    await state.update_data(tech_inbox=items)

    total = len(items)
    item = items[idx] if 0 <= idx < total else items[0]
    
    # Technician mode - render_item
    await render_item(cb.message, item, idx, total, lang, mode, user["id"])
    
    # Technician mode uchun alohida diagnostics xabari
    diag_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("diagnostics", lang), callback_data=f"tech_diag_begin_{req_id}")]
    ])
    await cb.message.answer(
        t("ok_started", lang) + "\n\n" + t("diag_begin_prompt", lang),
        reply_markup=diag_kb
    )

    # Application number ni olish (faqat technician mode uchun)
    app_number = await get_application_number(req_id, mode)
    
    mats = await fetch_technician_materials()
    header_text = t("store_header", lang, id=app_number)
    await cb.message.answer(header_text, reply_markup=materials_keyboard(mats, applications_id=req_id, lang=lang), parse_mode="HTML")

# =====================
# Diagnostics Handlers
# =====================
@router.callback_query(F.data.startswith("tech_diag_begin_"))
async def tech_diag_begin(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_diag_begin_", ""))
    except Exception:
        return
    await state.update_data(diag_req_id=req_id, lang=lang)
    
    # Avvalgi xabardagi inline keyboard'ni tozalash
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass  # Agar edit qila olmasa, davom etamiz
    
    await cb.message.answer(t("diag_begin_prompt", lang), parse_mode="HTML")
    await state.set_state(DiagStates.waiting_text)

@router.message(StateFilter(DiagStates.waiting_text))
async def tech_diag_text(msg: Message, state: FSMContext):
    user = await find_user_by_telegram_id(msg.from_user.id)
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(msg.from_user.id)
    if not user or user.get("role") != "technician":
        return await msg.answer(t("no_perm", lang))

    data = await state.get_data()
    req_id = int(data.get("diag_req_id", 0))
    if req_id <= 0:
        await _preserve_mode_clear(state)
        return await msg.answer(t("req_not_found", lang))

    text = (msg.text or "").strip()
    if not text:
        return await msg.answer(t("only_int", lang))  # qisqa validatsiya xabari sifatida qayta ishlatildi

    try:
        # Mode'ga qarab to'g'ri jadvalga diagnostika yozish
        mode = st.get("tech_mode", "connection")
        if mode == "technician":
            # Technician arizalar uchun technician_orders jadvaliga yozish
            await save_technician_diagnosis(applications_id=req_id, technician_id=user["id"], text=text)
    except Exception as e:
        await _preserve_mode_clear(state)
        return await msg.answer(f"{t('x_error', lang)} {e}")

    # Mode ni olish
    mode = st.get("tech_mode", "connection")
    
    await _preserve_mode_clear(state)

    # Diagnostika xabarini o'chirish
    try:
        await msg.delete()
    except Exception:
        pass  # Agar o'chirishda xatolik bo'lsa, davom etamiz

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("yes", lang),  callback_data=f"tech_diag_go_store_{req_id}")],
        [InlineKeyboardButton(text=t("no", lang), callback_data=f"tech_diag_cancel_{req_id}")],
    ])
    # Application number ni olish
    app_number = await get_application_number(req_id, mode)
    
    await msg.answer(
        f"{t('diag_saved', lang)}\n\n"
        f"{t('order_id', lang)} {esc(app_number)}\n"
        f"{t('diag_text', lang)}\n<code>{html.escape(text, quote=False)}</code>\n\n"
        f"{t('go_store_q', lang)}",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("tech_diag_go_store_"))
async def tech_diag_go_store(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    try:
        req_id = int(cb.data.replace("tech_diag_go_store_", ""))
    except Exception:
        return
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    # Inline keyboard'ni tozalash
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass  # Agar tozalashda xatolik bo'lsa, davom etamiz

    # Application number ni olish
    mode = st.get("tech_mode", "connection")
    app_number = await get_application_number(req_id, mode)
    
    mats = await fetch_technician_materials()
    header_text = t("store_header", lang, id=app_number)
    await cb.message.answer(header_text, reply_markup=materials_keyboard(mats, applications_id=req_id, lang=lang), parse_mode="HTML")

@router.callback_query(F.data.startswith("tech_diag_cancel_"))
async def tech_diag_cancel(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    await cb.answer(t("state_cleared", lang))
    
    try:
        req_id = int(cb.data.replace("tech_diag_cancel_", ""))
    except Exception:
        await _preserve_mode_clear(state)
        await cb.message.answer(t("diag_cancelled", lang))
        return
    
    # Inline keyboard'ni tozalash
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass  # Agar tozalashda xatolik bo'lsa, davom etamiz
    
    # Continue button qo'shamiz
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("finish", lang), callback_data=f"tech_finish_{req_id}")]
    ])
    
    await _preserve_mode_clear(state)
    await cb.message.answer(t("diag_cancelled", lang), reply_markup=kb)

@router.callback_query(F.data.startswith("tech_finish_"))
async def tech_finish_tech(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    try:
        req_id = int(cb.data.replace("tech_finish_", ""))
    except Exception:
        return await cb.answer()

    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    from database.technician.materials import fetch_selected_materials_for_request
    selected = await fetch_selected_materials_for_request(user["id"], req_id)

    # Request type ni avval aniqlash
    request_type = "technician"

    # Yakunlashda barcha tanlangan materiallarni material_requests ga yozish
    # Ombor yuborish allaqachon tech_confirm_warehouse da amalga oshirilgan
    if selected:
        try:
            # Faqat material_requests ga yozish
            from database.technician.materials import upsert_material_request_and_decrease_stock
            for material in selected:
                await upsert_material_request_and_decrease_stock(
                    user_id=user["id"],
                    applications_id=req_id,
                    material_id=material['material_id'],
                    add_qty=material['qty'],
                    request_type=request_type
                )
        except Exception as e:
            logger.error(f"Error creating material requests: {e}")

    try:
        # Ariza holatini tekshirish
        conn = await asyncpg.connect(settings.DB_URL)
        try:
            query = "SELECT status FROM technician_orders WHERE id = $1"
            result = await conn.fetchrow(query, req_id)
            if not result:
                return await cb.answer("❌ Ariza topilmadi", show_alert=True)
            
            current_status = result['status']
            
            # Agar holat in_warehouse bo'lsa, to'g'ridan-to'g'ri completed ga o'zgartirish
            if current_status == 'in_warehouse':
                await conn.execute(
                    "UPDATE technician_orders SET status='completed', updated_at=NOW() WHERE id=$1",
                    req_id
                )
                ok = True
            else:
                # Oddiy finish_technician_work chaqirish
                ok = await finish_technician_work_for_tech(applications_id=req_id, technician_id=user["id"])
        finally:
            await conn.close()
        
        if not ok:
            return await cb.answer(t("status_mismatch_finish", lang), show_alert=True)
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    # Application number ni olish
    app_number = await get_application_number(req_id, mode)
    lines = [t("work_finished", lang) + "\n", f"{t('order_id', lang)} {esc(app_number)}", t("used_materials", lang)]
    if selected:
        from .shared_utils import _qty_of
        for it in selected:
            qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
            lines.append(f"• {esc(it['name'])} — {qty_txt}")
    else:
        lines.append(t("none", lang))

    await cb.message.answer("\n".join(lines), parse_mode="HTML")
    await cb.answer(t("finish", lang) + " ✅")

    try:
        # Avval clientga ariza haqida ma'lumot yuboramiz va rating so'ramiz
        await send_completion_notification_to_client(cb.bot, req_id, request_type)
    except Exception as e:
        logger.error(f"Error sending completion notification: {e}")
        # Notification xatosi jarayonni to'xtatmaydi

@router.callback_query(F.data.startswith("tech_cancel_order_"))
async def tech_cancel_order_tech(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data()
    lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    req_id = int(cb.data.replace("tech_cancel_order_", ""))
    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    # Clear material_requests (don't touch material_and_technician)
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute(
            "DELETE FROM material_requests WHERE user_id = $1 AND applications_id = $2",
            user["id"], req_id
        )
        
        # Update order status to cancelled
        await conn.execute(
            "UPDATE technician_orders SET status='cancelled', updated_at=NOW() WHERE id=$1",
            req_id
        )
        
        await cb.answer("✅ Ariza bekor qilindi", show_alert=True)
        
        # Remove from inbox
        items = _dedup_by_id((await state.get_data()).get("tech_inbox", []))
        items = [it for it in items if it.get("id") != req_id]
        await state.update_data(tech_inbox=items)
        
        # Show next item or empty message
        if items:
            # Show first item
            item = items[0]
            await render_item(cb.message, item, 0, len(items), lang, mode, user["id"])
            await state.update_data(tech_idx=0)
        else:
            await cb.message.edit_text("📭 Inbox bo'sh", reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
    finally:
        await conn.close()
