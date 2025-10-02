# services/akt_service.py
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from aiogram.types import FSInputFile
from database.akt_queries import (
    get_akt_data_by_request_id, 
    get_materials_for_akt, 
    create_akt_document,
    mark_akt_sent,
    check_akt_exists
)
from utils.word_generator import AKTGenerator
from config import settings

class AKTService:
    def __init__(self):
        self.documents_dir = "documents"
        os.makedirs(self.documents_dir, exist_ok=True)

    async def post_completion_pipeline(self, bot, request_id: int, request_type: str):
        """
        Zayavka 'completed' bo'lgach AKT yaratish va yuborish.
        request_type: "connection" | "technician" | "staff"
        """
        try:
            print(f"Starting AKT pipeline for {request_type} request {request_id}")

            # 1) Idempotentlik: avval bor-yo'qligini tekshiramiz
            if await check_akt_exists(request_id, request_type):
                print(f"AKT already exists for {request_type} request {request_id}")
                return

            # 2) Ma'lumotlar
            data = await get_akt_data_by_request_id(request_id, request_type)
            if not data:
                print(f"No data found for {request_type} request {request_id}")
                return

            # (Ixtiyoriy) Qo‘shimcha rekvizitlar bo‘sh bo‘lsa, default berib yuboramiz
            data.setdefault("contract_number", "—")
            data.setdefault("service_order_number", "—")
            data.setdefault("organization_name", "___________________")

            # 3) Materiallar
            materials = await get_materials_for_akt(request_id, request_type)

            # 4) AKT raqami va fayl yo‘li
            akt_number = f"AKT-{request_id}-{datetime.now().strftime('%Y%m%d')}"
            file_path = os.path.join(self.documents_dir, f"{akt_number}.docx")

            # 5) Shablonsiz AKT yaratish
            generator = AKTGenerator()
            success = generator.generate_akt(data, materials, file_path)
            if not success:
                print(f"Failed to generate AKT for {request_type} request {request_id}")
                return

            print(f"AKT generated successfully: {file_path}")

            # 6) Hash
            file_hash = self._calculate_file_hash(file_path)

            # 7) Bazaga yozish
            await create_akt_document(request_id, request_type, akt_number, file_path, file_hash)
            print("AKT document saved to database")

            # 8) Mijozga yuborish
            await self._send_to_client(bot, request_id, request_type, file_path, akt_number, data)

        except Exception as e:
            print(f"Error in AKT pipeline for {request_type} request {request_id}: {e}")
            import traceback
            traceback.print_exc()

    async def _send_to_client(self, bot, request_id: int, request_type: str, file_path: str, akt_number: str, data: Dict[str, Any]):
        try:
            client_telegram_id = data.get('client_telegram_id')
            if client_telegram_id:
                workflow_type_text = {
                    'connection': 'Ulanish arizasi',
                    'technician': 'Texnik xizmat arizasi', 
                    'staff': 'Xodim arizasi'
                }.get(request_type, 'Zayavka')

                caption = (
                    "✅ <b>AKT hujjati tayyor!</b>\n\n"
                    f"📋 {workflow_type_text}: #{request_id}\n"
                    f"📅 Sana: {datetime.now().strftime('%d.%m.%Y')}\n"
                    f"📄 AKT raqami: {akt_number}\n\n"
                    f"<i>Iltimos, xizmatimizni baholang:</i>"
                )

                doc_path = Path(file_path)
                input_file = FSInputFile(doc_path, filename=doc_path.name)
                
                await bot.send_document(
                    chat_id=client_telegram_id,
                    document=input_file,
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=self._get_rating_keyboard(request_id, request_type)
                )

                await mark_akt_sent(request_id, request_type, datetime.now())
                print(f"AKT sent to client {client_telegram_id}")
            else:
                await self._send_to_manager_group(bot, file_path, akt_number, request_id, request_type)

        except Exception as e:
            print(f"Error sending AKT to client: {e}")
            await self._send_to_manager_group(bot, file_path, akt_number, request_id, request_type)

    async def _send_to_manager_group(self, bot, file_path: str, akt_number: str, request_id: int, request_type: str):
        try:
            manager_group_id = getattr(settings, 'MANAGER_GROUP_ID', None)
            if not manager_group_id:
                print("Manager group ID not configured")
                return

            workflow_type_text = {
                'connection': 'Ulanish arizasi',
                'technician': 'Texnik xizmat arizasi', 
                'staff': 'Xodim arizasi'
            }.get(request_type, 'Zayavka')

            caption = (
                "⚠️ <b>AKT mijozga yuborilmadi</b>\n\n"
                f"📋 {workflow_type_text}: #{request_id}\n"
                f"📄 AKT: {akt_number}\n"
                f"❌ Mijoz telegram_id topilmadi"
            )

            doc_path = Path(file_path)
            input_file = FSInputFile(doc_path, filename=doc_path.name)
            
            await bot.send_document(
                chat_id=manager_group_id,
                document=input_file,
                caption=caption,
                parse_mode='HTML'
            )

            print(f"AKT sent to manager group {manager_group_id}")
        except Exception as e:
            print(f"Error sending AKT to manager group: {e}")

    def _get_rating_keyboard(self, request_id: int, request_type: str):
        from keyboards.client_buttons import get_rating_keyboard
        return get_rating_keyboard(request_id, request_type)

    def _calculate_file_hash(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            import hashlib
            return hashlib.sha256(f.read()).hexdigest()
