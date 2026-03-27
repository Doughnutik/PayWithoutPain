import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from neo4j_database.neo4j_client import neo4j_client
from bot.handlers import commands_router, bill_creation_router, debt_actions_router
from services.scheduler import BotScheduler
from services.notification_service import NotificationService


logging.basicConfig(level=logging.INFO)


async def on_startup(bot: Bot):
    global notification_service, scheduler
    
    logging.info("Bot started, connecting to Neo4j...")
    try:
        await neo4j_client.execute_query("RETURN 1")
        logging.info("✅ Neo4j connected")
    except Exception as e:
        logging.error(f"❌ Neo4j connection failed: {e}")

    notification_service = NotificationService(bot)
    
    scheduler = BotScheduler(bot)
    scheduler.start()
    logging.info("✅ Notification scheduler started")


async def on_shutdown(bot: Bot):
    logging.info("Bot shutting down, closing Neo4j connection...")
    await neo4j_client.close()
    logging.info("✅ Neo4j connection closed")

    if scheduler:
        scheduler.stop()
        logging.info("✅ Scheduler stopped")


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(commands_router)
    dp.include_router(bill_creation_router)
    dp.include_router(debt_actions_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())