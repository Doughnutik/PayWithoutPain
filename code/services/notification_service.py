import logging
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from storage import storage, Debt, DebtStatus
from bot.keyboards import get_debt_keyboard
from enum import Enum

from services.message_builder import MessageBuilder

logger = logging.getLogger(__name__)

class NotificationResult(Enum):
    SENT = "sent"
    BLOCKED = "blocked"
    ERROR = "error"
    SKIPPED = "skipped"

class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.reminder_messages = [
            (12, "🔔 У вас есть неоплаченный долг\n"),
            (24, "⚠️ Напоминаем о существующем долге\n"),
            (48, "❗ Пора бы оплатить долг\n"),
            (96, "🚨 Если вы вдруг забыли, у вас есть неоплаченный долг\n"),
            (168, "⛔ Прошло уже много времени, а долг всё ещё не оплачен\n"),
        ]

    async def send_debt_reminder(self, debt: Debt) -> NotificationResult:
        if debt.status == DebtStatus.PAUSED:
            return NotificationResult.SKIPPED

        bill_id = debt.bill_id
        bill = await storage.get_bill_by_id(bill_id)

        debtor_id = debt.debtor_id
        
        payer_id = bill.creator_id
        payer = await storage.get_user_by_id(payer_id)

        text = self.get_reminder_message(debt.notifications_count)[1] + MessageBuilder.build_debt_message(debt, bill, payer)

        try:
            await self.bot.send_message(
                chat_id=debtor_id,
                text=text,
                reply_markup=get_debt_keyboard(debt.id, debt.status)
            )

            await storage.update_debt_notifications(debt.id)
            logger.info(f"Reminder sent to {debtor_id} for debt {debt.id}")
            return NotificationResult.SENT

        except TelegramForbiddenError:
            logger.warning(f"User {debtor_id} blocked the bot")
            return NotificationResult.BLOCKED
        except TelegramBadRequest as e:
            logger.error(f"Failed to send reminder to {debtor_id}: {e}")
            return NotificationResult.ERROR
        except Exception as e:
            logger.error(f"Unexpected error sending reminder: {e}")
            return NotificationResult.ERROR

    def get_reminder_message(self, count: int) -> tuple[int, str]:
        if count < len(self.reminder_messages):
            return self.reminder_messages[count]
        return self.reminder_messages[-1]

    async def send_all_reminders(self):
        stats = {
            "sent": 0,
            "skipped": 0,
            "blocked": 0,
            "errors": 0
        }

        debts = await storage.get_all_debts_for_reminder()
        cur_time = datetime.now()
        
        for debt in debts:
            last_notification = debt.last_notification_at if debt.last_notification_at else debt.created_at
            hours_since_last = (cur_time - last_notification).total_seconds()
            message = self.get_reminder_message(debt.notifications_count)
            
            if hours_since_last < message[0]:
                continue
            
            result = await self.send_debt_reminder(debt)
            stats[result.value] += 1
