import asyncio
import logging

import config
import database
import scheduler
import shadow_user
import worker_manager
from master_bot.bot import build_master


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config.validate()

    await database.init()

    scheduler.start()
    scheduler.register_healthcheck()
    await scheduler.register_all_mailings()

    await worker_manager.start_all_alive()

    master_bot, master_dp = build_master()
    logging.info("Master bot starting…")
    if shadow_user.session_ready():
        logging.info("Telethon shadow-check: session готов, буду использовать юзер-аккаунт.")
    else:
        logging.info("Telethon shadow-check: сессия не готова, fallback на t.me HTML.")
    try:
        await master_dp.start_polling(master_bot)
    finally:
        await worker_manager.shutdown()
        scheduler.shutdown()
        await shadow_user.shutdown()
        await master_bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
