# handlers/technician/connection_inbox.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from filters.role_filter import RoleFilter
from database.basic.user import find_user_by_telegram_id
from .shared_utils import (
    t, resolve_lang, esc, _dedup_by_id, _preserve_mode_clear,
    short_view_text_with_materials, action_keyboard, _safe_edit
)
from database.technician import (
    fetch_technician_inbox,
    cancel_technician_request,
    accept_technician_work,
    start_technician_work,
    finish_technician_work,
)
import logging

logger = logging.getLogger(__name__)

# ====== Router ======
router = Router()
router.message.filter(RoleFilter("technician"))
router.callback_query.filter(RoleFilter("technician"))

# =====================
# Connection Inbox Handlers
# =====================
@router.callback_query(F.data == "tech_inbox_cat_connection")
async def tech_cat_connection(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    items = _dedup_by_id(await fetch_technician_inbox(technician_id=user["id"], limit=50, offset=0))
    await state.update_data(tech_mode="connection", tech_inbox=items, tech_idx=0, lang=lang)
    if not items:
        return await cb.message.edit_text(t("empty_connection", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
    
    # Connection arizalarida rasmlar bo'lmaydi, shuning uchun oddiy edit
    item = items[0]; total = len(items)
    text = await short_view_text_with_materials(item, 0, total, user["id"], lang, mode="connection")
    kb = action_keyboard(item.get("id"), 0, total, item.get("status", ""), mode="connection", lang=lang)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("tech_inbox_prev_"))
async def tech_prev_connection(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    mode = st.get("tech_mode", "connection")
    if mode != "connection":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    items = _dedup_by_id(st.get("tech_inbox", []))
    if not items:
        return await cb.answer(t("empty_inbox", lang))
    total = len(items)
    idx = int(cb.data.replace("tech_inbox_prev_", "")) - 1
    if idx < 0 or idx >= total:
        return await cb.answer(t("reached_start", lang))
    await state.update_data(tech_inbox=items, tech_idx=idx)
    
    # Connection mode - rasmlar yo'q, oddiy edit
    text = await short_view_text_with_materials(items[idx], idx, total, user["id"], lang, mode)
    kb = action_keyboard(items[idx].get("id"), idx, total, items[idx].get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)

@router.callback_query(F.data.startswith("tech_inbox_next_"))
async def tech_next_connection(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    mode = st.get("tech_mode", "connection")
    if mode != "connection":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    items = _dedup_by_id(st.get("tech_inbox", []))
    if not items:
        return await cb.answer(t("empty_inbox", lang))
    total = len(items)
    idx = int(cb.data.replace("tech_inbox_next_", "")) + 1
    if idx < 0 or idx >= total:
        return await cb.answer(t("reached_end", lang))
    await state.update_data(tech_inbox=items, tech_idx=idx)
    
    # Connection mode - rasmlar yo'q, oddiy edit
    text = await short_view_text_with_materials(items[idx], idx, total, user["id"], lang, mode)
    kb = action_keyboard(items[idx].get("id"), idx, total, items[idx].get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)

@router.callback_query(F.data.startswith("tech_accept_"))
async def tech_accept_connection(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "connection":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    req_id = int(cb.data.replace("tech_accept_", ""))
    try:
        ok = await accept_technician_work(applications_id=req_id, technician_id=user["id"])
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
                    order_type="connection",
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
    
    # Connection mode - oddiy edit
    text = await short_view_text_with_materials(item, idx, total, user["id"], lang, mode)
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)
    
    await cb.answer()

@router.callback_query(F.data.startswith("tech_cancel_"))
async def tech_cancel_connection(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "connection":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)

    req_id = int(cb.data.replace("tech_cancel_", ""))
    try:
        await cancel_technician_request(applications_id=req_id, technician_id=user["id"])
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    items = _dedup_by_id(st.get("tech_inbox", []))
    idx = int(st.get("tech_idx", 0))
    items = [it for it in items if it.get("id") != req_id]

    if not items:
        await state.update_data(tech_inbox=[], tech_idx=0)
        await cb.answer(t("ok_cancelled", lang))
        return await _safe_edit(cb.message, t("empty_inbox", lang), InlineKeyboardMarkup(inline_keyboard=[]))

    if idx >= len(items):
        idx = len(items) - 1

    await state.update_data(tech_inbox=items, tech_idx=idx)
    total = len(items); item = items[idx]
    
    # Connection mode - oddiy edit
    text = await short_view_text_with_materials(item, idx, total, user["id"], lang, mode)
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)

@router.callback_query(F.data.startswith("tech_start_"))
async def tech_start_connection(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "connection":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    req_id = int(cb.data.replace("tech_start_", ""))
    try:
        ok = await start_technician_work(applications_id=req_id, technician_id=user["id"])
        if not ok:
            from .shared_utils import get_current_status
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
    
    # Connection mode - faqat mavjud xabarni yangilaydi, yangi xabar yubormaydi
    text = await short_view_text_with_materials(item, idx, total, user["id"], lang, mode)
    kb = action_keyboard(item.get("id"), idx, total, item.get("status", ""), mode=mode, lang=lang)
    await _safe_edit(cb.message, text, kb)
    await cb.answer(t("ok_started", lang))
    return

@router.callback_query(F.data.startswith("tech_finish_"))
async def tech_finish_connection(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data(); lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "connection":
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
    request_type = "connection"

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
        import asyncpg
        from config import settings
        conn = await asyncpg.connect(settings.DB_URL)
        try:
            query = "SELECT status FROM connection_orders WHERE id = $1"
            result = await conn.fetchrow(query, req_id)
            if not result:
                return await cb.answer("❌ Ariza topilmadi", show_alert=True)
            
            current_status = result['status']
            
            # Agar holat in_warehouse bo'lsa, to'g'ridan-to'g'ri completed ga o'zgartirish
            if current_status == 'in_warehouse':
                await conn.execute(
                    "UPDATE connection_orders SET status='completed'::connection_order_status, updated_at=NOW() WHERE id=$1",
                    req_id
                )
                ok = True
            else:
                # Oddiy finish_technician_work chaqirish
                ok = await finish_technician_work(applications_id=req_id, technician_id=user["id"])
        finally:
            await conn.close()
        
        if not ok:
            return await cb.answer(t("status_mismatch_finish", lang), show_alert=True)
    except Exception as e:
        return await cb.answer(f"{t('x_error', lang)} {e}", show_alert=True)

    # Application number ni olish
    from .shared_utils import get_application_number
    app_number = await get_application_number(req_id, mode)
    lines = [t("work_finished", lang) + "\n", f"{t('order_id', lang)} {esc(app_number)}", t("used_materials", lang)]
    if selected:
        from .shared_utils import _qty_of
        for it in selected:
            qty_txt = f"{_qty_of(it)} {'dona' if lang=='uz' else 'шт'}"
            lines.append(f"• {esc(it['name'])} — {qty_txt}")
    else:
        lines.append(T["none"][lang])

    await cb.message.answer("\n".join(lines), parse_mode="HTML")
    await cb.answer(t("finish", lang) + " ✅")

    try:
        # Avval clientga ariza haqida ma'lumot yuboramiz va rating so'ramiz
        from .shared_utils import send_completion_notification_to_client
        await send_completion_notification_to_client(cb.bot, req_id, request_type)
    except Exception as e:
        logger.error(f"Error sending completion notification: {e}")
        # Notification xatosi jarayonni to'xtatmaydi

@router.callback_query(F.data.startswith("tech_cancel_order_"))
async def tech_cancel_order_connection(cb: CallbackQuery, state: FSMContext):
    st = await state.get_data()
    lang = st.get("lang") or await resolve_lang(cb.from_user.id)
    mode = st.get("tech_mode", "connection")
    if mode != "connection":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    req_id = int(cb.data.replace("tech_cancel_order_", ""))
    
    user = await find_user_by_telegram_id(cb.from_user.id)
    if not user or user.get("role") != "technician":
        return await cb.answer(t("no_perm", lang), show_alert=True)
    
    # Clear material_requests (don't touch material_and_technician)
    import asyncpg
    from config import settings
    conn = await asyncpg.connect(settings.DB_URL)
    try:
        await conn.execute(
            "DELETE FROM material_requests WHERE user_id = $1 AND applications_id = $2",
            user["id"], req_id
        )
        
        # Update order status to cancelled
        await conn.execute(
            "UPDATE connection_orders SET status='cancelled'::connection_order_status, updated_at=NOW() WHERE id=$1",
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
            text = await short_view_text_with_materials(item, 0, len(items), user["id"], lang, mode)
            kb = action_keyboard(item.get("id"), 0, len(items), item.get("status", ""), mode=mode, lang=lang)
            await _safe_edit(cb.message, text, kb)
            await state.update_data(tech_idx=0)
        else:
            await cb.message.edit_text("📭 Inbox bo'sh", reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
    finally:
        await conn.close()
