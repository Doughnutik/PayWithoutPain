from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
from uuid import uuid4

from database.neo4j_client import neo4j_client
from database import queries


@dataclass
class User:
    telegram_id: int
    username: str
    first_name: str
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_neo4j(cls, record: dict) -> "User":
        u = record.get("u", {})
        return cls(
            telegram_id=u.get("telegram_id"),
            username=u.get("username", ""),
            first_name=u.get("first_name", ""),
            created_at=u.get("created_at").to_native() if u.get("created_at") else datetime.now()
        )


@dataclass
class Debt:
    id: str
    bill_id: str
    debtor_id: int
    payer_id: int
    amount: float
    status: str = "pending"
    proof_screenshot: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    changed_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_neo4j(cls, record: dict, bill_id: str = None, payer_id: int = None) -> "Debt":
        d = record.get("d", {})
        return cls(
            id=d.get("id"),
            bill_id=bill_id or record.get("bill", {}).get("id"),
            debtor_id=record.get("debtor", {}).get("telegram_id"),
            payer_id=payer_id or record.get("payer", {}).get("telegram_id"),
            amount=d.get("amount"),
            status=d.get("status", "pending"),
            proof_screenshot=d.get("proof_screenshot"),
            created_at=d.get("created_at").to_native() if d.get("created_at") else datetime.now(),
            changed_at=d.get("changed_at").to_native() if d.get("changed_at") else datetime.now()
        )


@dataclass
class Bill:
    id: str
    creator_id: int
    amount_left: float
    currency: str = "RUB"
    description: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    changed_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_neo4j(cls, record: dict) -> "Bill":
        b = record.get("b", {})
        return cls(
            id=b.get("id"),
            creator_id=record.get("creator", {}).get("telegram_id"),
            amount_left=b.get("amount_left"),
            currency=b.get("currency", "RUB"),
            description=b.get("description", ""),
            status=b.get("status", "active"),
            created_at=b.get("created_at").to_native() if b.get("created_at") else datetime.now(),
            changed_at=b.get("changed_at").to_native() if b.get("changed_at") else datetime.now()
        )


class Neo4jStorage:
    """Реальное хранилище на Neo4j"""

    async def get_or_create_user(self, telegram_id: int, username: str, first_name: str) -> User:
        result = await neo4j_client.execute_write(
            queries.CREATE_USER,
            {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name
            }
        )
        return User.from_neo4j(result[0]) if result else None

    async def create_bill(self, creator_id: int, amount: float, description: str) -> Bill:
        bill_id = str(uuid4())[:8]
        result = await neo4j_client.execute_write(
            queries.CREATE_BILL,
            {
                "bill_id": bill_id,
                "creator_id": creator_id,
                "amount": amount,
                "currency": "RUB",
                "description": description
            }
        )
        return Bill.from_neo4j(result[0]) if result else None

    async def add_debt(self, bill_id: str, debtor_id: int, payer_id: int, amount: float) -> Debt:
        debt_id = str(uuid4())[:8]
        result = await neo4j_client.execute_write(
            queries.CREATE_DEBT,
            {
                "debt_id": debt_id,
                "bill_id": bill_id,
                "debtor_id": debtor_id,
                "payer_id": payer_id,
                "amount": amount
            }
        )
        return Debt.from_neo4j(result[0], bill_id=bill_id, payer_id=payer_id) if result else None

    async def update_debt_status(self, debt_id: str, status: str, screenshot: Optional[str] = None) -> Debt:
        result = await neo4j_client.execute_write(
            queries.UPDATE_DEBT_STATUS,
            {
                "debt_id": debt_id,
                "status": status,
                "screenshot": screenshot
            }
        )
        return Debt.from_neo4j(result[0]) if result else None

    async def confirm_debt(self, debt_id: str) -> Bill:
        # Сначала обновляем статус долга
        await self.update_debt_status(debt_id, "confirmed")

        # Получаем информацию о долге
        debt_result = await neo4j_client.execute_query(
            queries.GET_DEBT_BY_ID,
            {"debt_id": debt_id}
        )
        if not debt_result:
            return None

        debt_data = debt_result[0].get("d", {})
        bill_id = debt_data.get("bill_id")
        amount = debt_data.get("amount")

        # Обновляем сумму счёта
        result = await neo4j_client.execute_write(
            queries.UPDATE_BILL_AMOUNT,
            {
                "bill_id": bill_id,
                "amount": amount
            }
        )
        return Bill.from_neo4j(result[0]) if result else None

    async def get_user_debts(self, telegram_id: int, status: Optional[str] = None) -> list[Debt]:
        result = await neo4j_client.execute_query(
            queries.GET_USER_DEBTS,
            {
                "telegram_id": telegram_id,
                "status": status
            }
        )
        return [Debt.from_neo4j(r) for r in result]

    async def get_user_bills(self, telegram_id: int, status: Optional[str] = None) -> list[Bill]:
        result = await neo4j_client.execute_query(
            queries.GET_USER_BILLS,
            {
                "telegram_id": telegram_id,
                "status": status
            }
        )
        return [Bill.from_neo4j(r) for r in result]

    async def get_bill(self, bill_id: str) -> Optional[Bill]:
        result = await neo4j_client.execute_query(
            queries.GET_BILL_BY_ID,
            {"bill_id": bill_id}
        )
        return Bill.from_neo4j(result[0]) if result else None

    async def get_debt(self, debt_id: str) -> Optional[Debt]:
        result = await neo4j_client.execute_query(
            queries.GET_DEBT_BY_ID,
            {"debt_id": debt_id}
        )
        return Debt.from_neo4j(result[0]) if result else None

    async def archive_bill(self, bill_id: str) -> Bill:
        result = await neo4j_client.execute_write(
            queries.ARCHIVE_BILL,
            {"bill_id": bill_id}
        )
        return Bill.from_neo4j(result[0]) if result else None

    async def get_debts_for_bill(self, bill_id: str, status: Optional[str] = None) -> list[Debt]:
        result = await neo4j_client.execute_query(
            queries.GET_DEBTS_FOR_BILL,
            {
                "bill_id": bill_id,
                "status": status
            }
        )
        return [Debt.from_neo4j(r, bill_id=bill_id) for r in result]

    async def get_bill_with_debts(self, bill_id: str) -> Optional[tuple[Bill, list[Debt]]]:
        result = await neo4j_client.execute_query(
            queries.GET_BILL_WITH_DEBTS,
            {"bill_id": bill_id}
        )
        if not result:
            return None

        bill = Bill.from_neo4j(result[0])
        debts = []
        for item in result[0].get("debts", []):
            debt_record = {"d": item.get("debt", {}), "debtor": item.get("debtor", {}), "payer": item.get("payer", {})}
            debts.append(Debt.from_neo4j(debt_record))
        return bill, debts

    async def get_active_debts_for_notification(self, hours: int = 24) -> list[dict]:
        result = await neo4j_client.execute_query(
            queries.GET_ACTIVE_DEBTS_FOR_NOTIFICATION,
            {"hours": hours}
        )
        return result

    async def get_debts_for_reminder(self, hours: int = 24, max_count: int = 5) -> list[dict]:
        """Получает долги, требующие напоминания"""
        result = await neo4j_client.execute_query(
            queries.GET_DEBTS_FOR_REMINDER,
            {
                "hours": hours,
                "max_count": max_count
            }
        )
        return result

    async def increment_notification_count(self, debt_id: str) -> None:
        """Увеличивает счётчик отправленных уведомлений"""
        await neo4j_client.execute_write(
            queries.UPDATE_DEBT_NOTIFICATION_COUNT,
            {"debt_id": debt_id}
        )

    async def reset_notification_count(self, debt_id: str) -> None:
        """Сбрасывает счётчик при оплате"""
        await neo4j_client.execute_write(
            queries.RESET_DEBT_NOTIFICATION_COUNT,
            {"debt_id": debt_id}
        )

    async def get_user_notification_settings(self, telegram_id: int) -> bool:
        """Проверяет, заглушены ли уведомления пользователя"""
        result = await neo4j_client.execute_query(
            queries.GET_USER_NOTIFICATION_SETTINGS,
            {"telegram_id": telegram_id}
        )
        if not result:
            return False
        return result[0].get("u", {}).get("muted", False) or False

    async def set_user_notification_settings(self, telegram_id: int, muted: bool) -> None:
        """Устанавливает настройки уведомлений"""
        await neo4j_client.execute_write(
            queries.UPDATE_USER_NOTIFICATION_SETTINGS,
            {
                "telegram_id": telegram_id,
                "muted": muted
            }
        )

    # Обновляем confirm_debt для сброса счётчика
    async def confirm_debt(self, debt_id: str) -> Bill:
        await self.update_debt_status(debt_id, "confirmed")
        await self.reset_notification_count(debt_id)  # 🆕 Сброс счётчика

        debt_result = await neo4j_client.execute_query(
            queries.GET_DEBT_BY_ID,
            {"debt_id": debt_id}
        )
        if not debt_result:
            return None

        debt_data = debt_result[0].get("d", {})
        bill_id = debt_data.get("bill_id")
        amount = debt_data.get("amount")

        result = await neo4j_client.execute_write(
            queries.UPDATE_BILL_AMOUNT,
            {
                "bill_id": bill_id,
                "amount": amount
            }
        )
        return Bill.from_neo4j(result[0]) if result else None

storage = Neo4jStorage()