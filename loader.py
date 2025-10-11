import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from middlewares import ErrorHandlingMiddleware
from utils.universal_error_logger import get_universal_logger

# Bot logger ni ishlatish
logger = get_universal_logger("AlfaConnectBot")

bot = Bot(
    token=settings.BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher(storage=MemoryStorage())

dp.update.middleware(ErrorHandlingMiddleware(bot=bot))
