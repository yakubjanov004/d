import asyncio
import sys
import logging
from loader import create_bot_and_dp
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
    bot, dp = await create_bot_and_dp()
    dp.include_router(handlers_router)
    
    # Pollingni barqaror qilish uchun backoff bilan qayta urinib ko'rish
    base_delay = 1
    max_delay = 60
    attempt = 0
    
    while True:
        try:
            logger.info("Bot starting...")
            await dp.start_polling(bot)
            break  # muvaffaqiyatli tugasa siklni to'xtatamiz
        except asyncio.CancelledError:
            logger.info("Bot stopped by user")
            break
        except Exception:
            attempt += 1
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            logger.exception("Polling error. Reconnecting after %s seconds...", delay, exc_info=True)
            await asyncio.sleep(delay)
            continue
        finally:
            try:
                await bot.session.close()
            except Exception:
                pass
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
