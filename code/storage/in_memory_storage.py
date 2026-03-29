from datetime import datetime
from typing import Optional
from uuid import uuid4

from .models import User, Debt, Bill, DebtStatus, BillStatus
    

class InMemoryStorage:

    def __init__(self):
        self.users: dict[int, User] = {}
        self.bills: dict[str, Bill] = {}
        self.debts: dict[str, Debt] = {}
        self.user_bills: dict[int, list[str]] = {}  # telegram_id -> bill_ids
        self.user_debts: dict[int, list[str]] = {}  # telegram_id -> debt_ids

    async def create_update_user(self, telegram_id: int, username: Optional[str], first_name: str) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username.lstrip("@") if username else None,
            first_name=first_name
        )
        self.users[telegram_id] = user
        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        if not username:
            return None
        
        for user in self.users.values():
            if user.username and user.username == username.lstrip("@"):
                return user
        return None
    
    async def get_user_by_id(self, telegram_id: int) -> Optional[User]:
        return self.users.get(telegram_id)

    async def create_bill(self, creator_id: int, amount: float, description: str, currency: str) -> Bill:
        bill_id = str(uuid4())[:8]
        bill = Bill(
            id=bill_id,
            creator_id=creator_id,
            amount=amount,
            currency=currency,
            description=description
        )
        self.bills[bill_id] = bill
        
        if creator_id not in self.user_bills:
            self.user_bills[creator_id] = []
        self.user_bills[creator_id].append(bill_id)
        return bill
    
    async def get_bill_by_id(self, bill_id: str) -> Optional[Bill]:
        return self.bills.get(bill_id)
    
    async def get_user_bills(self, telegram_id: int) -> list[Bill]:
        bill_ids = self.user_bills.get(telegram_id, [])
        return [self.bills[bill_id] for bill_id in bill_ids if self.bills[bill_id].status != BillStatus.CLOSED]
    
    async def decrease_bill_amount(self, bill_id: str, delta: float) -> Optional[Bill]:
        if bill_id not in self.bills:
            return None
        self.bills[bill_id].amount -= delta
        self.bills[bill_id].changed_at = datetime.now()
        if self.bills[bill_id].amount <= 0:
            self.bills[bill_id].status = BillStatus.CLOSED
        return self.bills[bill_id]

    async def create_debt(self, bill_id: str, debtor_id: int, amount: float) -> Debt:
        debt_id = str(uuid4())[:8]
        debt = Debt(
            id=debt_id,
            bill_id=bill_id,
            debtor_id=debtor_id,
            amount=amount
        )
        self.debts[debt_id] = debt
        
        if debtor_id not in self.user_debts:
            self.user_debts[debtor_id] = []
        self.user_debts[debtor_id].append(debt_id)
        return debt

    async def update_debt_status(self, debt_id: str, status: str) -> Optional[Debt]:
        if debt_id not in self.debts:
            return None
        self.debts[debt_id].status = DebtStatus(status)
        self.debts[debt_id].changed_at = datetime.now()
        return self.debts[debt_id]

    async def get_user_debts(self, telegram_id: int) -> list[Debt]:
        debt_ids = self.user_debts.get(telegram_id, [])
        return [self.debts[debt_id] for debt_id in debt_ids if self.debts[debt_id].status != DebtStatus.CLOSED]

    async def get_debt_by_id(self, debt_id: str) -> Optional[Debt]:
        return self.debts.get(debt_id)

    async def get_debts_for_bill(self, bill_id: str) -> list[Debt]:
        return [debt for debt in self.debts.values() if debt.bill_id == bill_id]

    async def decrease_debt_amount(self, debt_id: str, delta: float) -> Optional[Debt]:
        if debt_id not in self.debts:
            return None
        self.debts[debt_id].amount -= delta
        self.debts[debt_id].changed_at = datetime.now()
        if self.debts[debt_id].amount <= 0:
            self.debts[debt_id].status = DebtStatus.CLOSED
        return self.debts[debt_id]
    
    async def update_debt_notifications(self, debt_id: str):
        if debt_id not in self.debts:
            return None
        self.debts[debt_id].notifications_count += 1
        self.debts[debt_id].last_notification_at = datetime.now()
        return self.debts[debt_id]
        
    async def get_all_debts_for_reminder(self) -> list[Debt]:
        return [debt for debt in self.debts.values() if debt.status == DebtStatus.ACTIVE]
