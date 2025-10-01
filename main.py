import asyncio
import sys
import logging
from loader import dp, bot
from handlers import router as handlers_router

logger = logging.getLogger(__name__)

async def main():
    dp.include_router(handlers_router)
    
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        pass
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user (KeyboardInterrupt)")
        sys.exit(0)
