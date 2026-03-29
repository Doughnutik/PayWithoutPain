from typing import Optional
from uuid import uuid4
import logging

from neo4j_database.neo4j_client import neo4j_client
from neo4j_database import queries

from .models import User, Debt, Bill


logger = logging.getLogger(__name__)


class Neo4jStorage:
    async def create_update_user(self, telegram_id: int, username: Optional[str], first_name: str) -> User:
        result = await neo4j_client.execute_write(
            queries.CREATE_UPDATE_USER,
            {
                "telegram_id": telegram_id,
                "username": username.lstrip("@") if username else None,
                "first_name": first_name
            }
        )
        return User.from_neo4j(result[0])

    async def get_user_by_username(self, username: str) -> Optional[User]:
        if not username:
            return None
        
        result = await neo4j_client.execute_query(
            queries.GET_USER_BY_USERNAME,
            {
                "username": username.lstrip("@")
            }
        )
        return User.from_neo4j(result[0]) if result else None
    
    async def get_user_by_id(self, telegram_id: int) -> Optional[User]:
        result = await neo4j_client.execute_query(
            queries.GET_USER_BY_ID,
            {
                "telegram_id": telegram_id
            }
        )
        return User.from_neo4j(result[0]) if result else None

    async def create_bill(self, creator_id: int, amount: float, description: str, currency: str) -> Bill:
        bill_id = str(uuid4())[:8]
        result = await neo4j_client.execute_write(
            queries.CREATE_BILL,
            {
                "bill_id": bill_id,
                "creator_id": creator_id,
                "amount": amount,
                "currency": currency,
                "description": description
            }
        )
        
        return Bill.from_neo4j(result[0])
    
    async def get_bill_by_id(self, bill_id: str) -> Optional[Bill]:
        result = await neo4j_client.execute_query(
            queries.GET_BILL_BY_ID,
            {"bill_id": bill_id}
        )
        return Bill.from_neo4j(result[0]) if result else None
    
    async def get_user_bills(self, telegram_id: int) -> list[Bill]:
        result = await neo4j_client.execute_query(
            queries.GET_USER_BILLS,
            {
                "telegram_id": telegram_id
            }
        )       
        return [Bill.from_neo4j(r) for r in result]
    
    async def decrease_bill_amount(self, bill_id: str, delta: float) -> Optional[Bill]:
        result = await neo4j_client.execute_write(
            queries.DECREASE_BILL_AMOUNT,
            {
                "bill_id": bill_id,
                "delta": delta
            }
        )
        return Bill.from_neo4j(result[0]) if result else None

    async def create_debt(self, bill_id: str, debtor_id: int, amount: float) -> Debt:
        debt_id = str(uuid4())[:8]
        result = await neo4j_client.execute_write(
            queries.CREATE_DEBT,
            {
                "debt_id": debt_id,
                "bill_id": bill_id,
                "debtor_id": debtor_id,
                "amount": amount
            }
        )
        return Debt.from_neo4j(result[0])

    async def update_debt_status(self, debt_id: str, status: str) -> Optional[Debt]:
        result = await neo4j_client.execute_write(
            queries.UPDATE_DEBT_STATUS,
            {
                "debt_id": debt_id,
                "status": status
            }
        )
        return Debt.from_neo4j(result[0]) if result else None

    async def get_user_debts(self, telegram_id: int) -> list[Debt]:
        result = await neo4j_client.execute_query(
            queries.GET_USER_DEBTS,
            {
                "telegram_id": telegram_id,
            }
        )
        return [Debt.from_neo4j(r) for r in result]

    async def get_debt_by_id(self, debt_id: str) -> Optional[Debt]:
        result = await neo4j_client.execute_query(
            queries.GET_DEBT_BY_ID,
            {"debt_id": debt_id}
        )
        return Debt.from_neo4j(result[0]) if result else None

    async def get_debts_for_bill(self, bill_id: str) -> list[Debt]:
        result = await neo4j_client.execute_query(
            queries.GET_DEBTS_FOR_BILL,
            {
                "bill_id": bill_id,
            }
        )
        return [Debt.from_neo4j(r) for r in result]

    async def decrease_debt_amount(self, debt_id: str, delta: float) -> Optional[Debt]:
        result = await neo4j_client.execute_write(
            queries.DECREASE_DEBT_AMOUNT,
            {
                "debt_id": debt_id,
                "delta": delta
            }
        )
        return Debt.from_neo4j(result[0]) if result else None
    
    async def update_debt_notifications(self, debt_id: str):
        await neo4j_client.execute_write(
            queries.UPDATE_DEBT_NOTIFICATIONS,
            {"debt_id": debt_id}
        )
        
    async def get_all_debts_for_reminder(self) -> list[Debt]:
        result = await neo4j_client.execute_query(
            queries.GET_ALL_DEBTS_FOR_REMINDER
        )
        return [Debt.from_neo4j(r) for r in result]
