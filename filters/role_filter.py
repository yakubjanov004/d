# filters/role_filter.py
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Union
from database.jm_inbox_queries import db_get_user_by_telegram_id

class RoleFilter(BaseFilter):
    def __init__(self, role: str):
        self.role = role

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user = await db_get_user_by_telegram_id(event.from_user.id)
        if not user or user.get("is_blocked"):
            return False
        return (user.get("role") or "").strip() == self.role
