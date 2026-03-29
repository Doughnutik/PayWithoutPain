import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class BotScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.notification_service = NotificationService(bot)

    def start(self):
        # # Напоминания каждую минуту в 00 секунд для тестирования
        # self.scheduler.add_job(
        #     self.send_reminders,
        #     CronTrigger(second=0),
        #     id="day",
        #     name="Дневное напоминания о долгах",
        #     replace_existing=True
        # )
        
        # Напоминания каждый день в 12:00
        self.scheduler.add_job(
            self.send_reminders,
            CronTrigger(hour=12, minute=0),
            id="day",
            name="Дневное напоминания о долгах",
            replace_existing=True
        )

        # Напоминания каждый вечер в 20:00
        self.scheduler.add_job(
            self.send_reminders,
            CronTrigger(hour=20, minute=0),
            id="evening",
            name="Вечерние напоминания о долгах",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("✅ Scheduler started")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("✅ Scheduler stopped")

    async def send_reminders(self):
        logger.info("🔔 Starting reminder job...")
        try:
            stats = await self.notification_service.send_all_reminders()
            logger.info(f"✅ Reminder job completed: {stats}")
        except Exception as e:
            logger.error(f"❌ Reminder job failed: {e}")
