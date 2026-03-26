import logging
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from storage.neo4j_storage import storage
from bot.keyboards import get_payment_keyboard

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.max_reminders = 5
        self.reminder_intervals = [
            (24, "🔔 Первое напоминание"),
            (72, "⚠️ Второе напоминание"),
            (168, "🚨 Третье напоминание (неделя)"),
            (336, "❗ Четвёртое напоминание (2 недели)"),
            (504, "⛔ Финальное напоминание (3 недели)"),
        ]

    async def send_debt_reminder(self, debt: dict) -> bool:
        """Отправляет напоминание должнику"""
        debtor_data = debt.get("debtor", {})
        debt_data = debt.get("d", {})
        bill_data = debt.get("bill", {})
        payer_data = debt.get("payer", {})

        telegram_id = debtor_data.get("telegram_id")
        debt_id = debt_data.get("id")
        amount = debt_data.get("amount")
        bill_description = bill_data.get("description", "Счёт")
        payer_username = payer_data.get("username", "Плательщик")

        # Проверяем, не заглушены ли уведомления
        is_muted = await storage.get_user_notification_settings(telegram_id)
        if is_muted:
            logger.info(f"User {telegram_id} muted notifications, skipping")
            return False

        # Формируем сообщение
        notification_count = debt_data.get("notification_count", 0) or 0
        interval_info = self._get_interval_info(notification_count)

        text = f"""{interval_info}

📌 **Счёт:** {bill_description}
💰 **Ваша доля:** {amount:.2f} ₽
👤 **Плательщик:** @{payer_username}

⏳ Статус: {'⏳ Ожидает оплаты' if debt_data.get('status') == 'pending' else '📸 Скриншот отправлен'}

Пожалуйста, оплатите долг и отправьте скриншот."""

        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                reply_markup=get_payment_keyboard(debt_id),
                parse_mode="Markdown"
            )

            # Увеличиваем счётчик
            await storage.increment_notification_count(debt_id)
            logger.info(f"Reminder sent to {telegram_id} for debt {debt_id}")
            return True

        except TelegramForbiddenError:
            logger.warning(f"User {telegram_id} blocked the bot")
            return False
        except TelegramBadRequest as e:
            logger.error(f"Failed to send reminder to {telegram_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending reminder: {e}")
            return False

    def _get_interval_info(self, count: int) -> str:
        """Возвращает текст напоминания в зависимости от количества"""
        if count < len(self.reminder_intervals):
            return self.reminder_intervals[count][1]
        return "🔔 Напоминание о долге"

    async def send_all_reminders(self) -> dict:
        """Отправляет все запланированные напоминания"""
        stats = {
            "sent": 0,
            "skipped": 0,
            "blocked": 0,
            "errors": 0
        }

        # Получаем долги для напоминания (каждые 24 часа)
        debts = await storage.get_debts_for_reminder(hours=24, max_count=self.max_reminders)

        logger.info(f"Found {len(debts)} debts for reminder")

        for debt in debts:
            result = await self.send_debt_reminder(debt)
            if result:
                stats["sent"] += 1
            elif result is False:
                # Проверяем, была ли ошибка блокировки
                debtor_id = debt.get("debtor", {}).get("telegram_id")
                is_muted = await storage.get_user_notification_settings(debtor_id)
                if is_muted:
                    stats["skipped"] += 1
                else:
                    stats["blocked"] += 1
            else:
                stats["errors"] += 1

        logger.info(f"Reminder stats: {stats}")
        return stats

    async def send_initial_notification(self, debt_id: str, debtor_id: int, bill_description: str, amount: float, payer_username: str) -> bool:
        """Отправляет первое уведомление при создании долга"""
        text = f"""💸 **Новый долг**

📌 **Счёт:** {bill_description}
💰 **Ваша доля:** {amount:.2f} ₽
👤 **Плательщик:** @{payer_username}

Пожалуйста, оплатите свою долю и отправьте скриншот."""

        try:
            await self.bot.send_message(
                chat_id=debtor_id,
                text=text,
                reply_markup=get_payment_keyboard(debt_id),
                parse_mode="Markdown"
            )
            await storage.increment_notification_count(debt_id)
            return True
        except Exception as e:
            logger.error(f"Failed to send initial notification: {e}")
            return False

notification_service = None