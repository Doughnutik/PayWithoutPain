from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class User:
    telegram_id: int
    username: str
    first_name: str
    created_at: datetime = field(default_factory=datetime.now)


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


@dataclass
class Bill:
    id: str
    creator_id: int
    amount: float
    currency: str = "RUB"
    description: str = ""
    status: str = "active"  # active, closed, archived
    created_at: datetime = field(default_factory=datetime.now)
    changed_at: datetime = field(default_factory=datetime.now)
    debts: list[Debt] = field(default_factory=list)


class MockStorage:
    """Заглушка вместо Neo4j для тестирования логики бота"""

    def __init__(self):
        self.users: dict[int, User] = {}
        self.bills: dict[str, Bill] = {}
        self.debts: dict[str, Debt] = {}
        self.user_bills: dict[int, list[str]] = {}  # telegram_id -> bill_ids
        self.user_debts: dict[int, list[str]] = {}  # telegram_id -> debt_ids

    async def get_or_create_user(self, telegram_id: int, username: str, first_name: str) -> User:
        if telegram_id not in self.users:
            self.users[telegram_id] = User(
                telegram_id=telegram_id,
                username=username or f"user_{telegram_id}",
                first_name=first_name or "User"
            )
        return self.users[telegram_id]

    async def create_bill(self, creator_id: int, amount: float, description: str) -> Bill:
        bill_id = str(uuid4())[:8]
        bill = Bill(
            id=bill_id,
            creator_id=creator_id,
            amount=amount,
            description=description
        )
        self.bills[bill_id] = bill
        if creator_id not in self.user_bills:
            self.user_bills[creator_id] = []
        self.user_bills[creator_id].append(bill_id)
        return bill

    async def add_debt(self, bill_id: str, debtor_id: int, payer_id: int, amount: float) -> Debt:
        debt_id = str(uuid4())[:8]
        debt = Debt(
            id=debt_id,
            bill_id=bill_id,
            debtor_id=debtor_id,
            payer_id=payer_id,
            amount=amount
        )
        self.debts[debt_id] = debt
        self.bills[bill_id].debts.append(debt)
        if debtor_id not in self.user_debts:
            self.user_debts[debtor_id] = []
        self.user_debts[debtor_id].append(debt_id)
        return debt

    async def update_debt_status(self, debt_id: str, status: str, screenshot: Optional[str] = None) -> Debt:
        debt = self.debts[debt_id]
        debt.status = status
        debt.changed_at = datetime.now()
        if screenshot:
            debt.proof_screenshot = screenshot
        return debt

    async def confirm_debt(self, debt_id: str) -> Bill:
        debt = self.debts[debt_id]
        debt.status = "confirmed"
        debt.changed_at = datetime.now()
        bill = self.bills[debt.bill_id]
        bill.amount -= debt.amount
        bill.changed_at = datetime.now()
        if bill.amount <= 0:
            bill.status = "closed"
        return bill

    async def get_user_debts(self, telegram_id: int, status: Optional[str] = None) -> list[Debt]:
        debt_ids = self.user_debts.get(telegram_id, [])
        debts = [self.debts[did] for did in debt_ids]
        if status:
            debts = [d for d in debts if d.status == status]
        return debts

    async def get_user_bills(self, telegram_id: int, status: Optional[str] = None) -> list[Bill]:
        bill_ids = self.user_bills.get(telegram_id, [])
        bills = [self.bills[bid] for bid in bill_ids]
        if status:
            bills = [b for b in bills if b.status == status]
        return bills

    async def get_bill(self, bill_id: str) -> Optional[Bill]:
        return self.bills.get(bill_id)

    async def get_debt(self, debt_id: str) -> Optional[Debt]:
        return self.debts.get(debt_id)

    async def archive_bill(self, bill_id: str) -> Bill:
        bill = self.bills[bill_id]
        bill.status = "archived"
        bill.changed_at = datetime.now()
        return bill

    async def get_debts_for_bill(self, bill_id: str, status: Optional[str] = None) -> list[Debt]:
        bill = self.bills.get(bill_id)
        if not bill:
            return []
        debts = bill.debts
        if status:
            debts = [d for d in debts if d.status == status]
        return debts

storage = MockStorage()