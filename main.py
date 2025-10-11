import asyncio
import sys
import logging
from loader import dp, bot
from handlers import router as handlers_router
from utils.directory_utils import setup_media_structure, setup_static_structure
from utils.universal_error_logger import get_universal_logger
from utils.terminal_error_handler import setup_terminal_error_handler

logger = get_universal_logger("AlfaConnectBot")

# Terminal error handler'ni sozlash
terminal_error_handler = setup_terminal_error_handler()

# Setup media and static directory structures
try:
    setup_media_structure()
    setup_static_structure()
except Exception as e:
    logger.error(f"Directory setup failed: {e}")
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
        logger.error(f"Bot error: {e}")
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
        logger.error(f"Main error: {e}")
        sys.exit(1)
