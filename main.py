import asyncio
import sys
import logging
from loader import dp, bot
from handlers import router as handlers_router
from utils.directory_utils import setup_media_structure, setup_static_structure

# Logger'ni olish
logger = logging.getLogger(__name__)

# Setup media and static directory structures
try:
    setup_media_structure()
    setup_static_structure()
    logger.info("Media va static papkalar muvaffaqiyatli yaratildi")
except Exception as e:
    logger.exception("Directory setup failed", exc_info=True)
    sys.exit(1)

async def main():
    dp.include_router(handlers_router)
    
    try:
        logger.info("Bot starting...")
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Bot stopped by user")
        pass
    except Exception as e:
        logger.exception("Bot error", exc_info=True)
        raise
    finally:
        await bot.session.close()
        logger.info("Bot session closed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
        sys.exit(0)
    except Exception as e:
        logger.exception("Main error", exc_info=True)
        sys.exit(1)
