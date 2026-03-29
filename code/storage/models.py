from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from enum import Enum

@dataclass
class User:
    telegram_id: int
    first_name: str
    username: Optional[str] = None
    created_at: datetime = datetime.now()

    @classmethod
    def from_neo4j(cls, record: dict) -> "User":
        user = record['user']
        return cls(
            telegram_id=user['telegram_id'],
            username=user.get("username"),
            first_name=user["first_name"],
            created_at=user['created_at']
        )


class DebtStatus(Enum):
    ACTIVE = "active"
    PENDING = "pending"
    PAUSED = "paused"
    CLOSED = "closed"
    

@dataclass
class Debt:
    id: str
    bill_id: str
    debtor_id: int
    amount: float
    status: DebtStatus = DebtStatus.ACTIVE
    created_at: datetime = datetime.now()
    changed_at: datetime = datetime.now()
    notifications_count: int = 0
    last_notification_at: Optional[datetime] = None

    @classmethod
    def from_neo4j(cls, record: dict) -> "Debt":
        debt = record['debt']
        return cls(
            id=debt['id'],
            bill_id=debt['bill_id'],
            debtor_id=debt['debtor_id'],
            amount=debt['amount'],
            status=DebtStatus(debt['status']),
            created_at=debt["created_at"],
            changed_at=debt["changed_at"],
            notifications_count=debt["notifications_count"],
            last_notification_at=debt.get("last_notification_at")
        )


class BillStatus(Enum):
    ACTIVE = "active"
    CLOSED = "closed"

@dataclass
class Bill:
    id: str
    creator_id: int
    amount: float
    currency: str = "RUB"
    description: str = ""
    status: BillStatus = BillStatus.ACTIVE
    created_at: datetime = datetime.now()
    changed_at: datetime = datetime.now()

    @classmethod
    def from_neo4j(cls, record: dict) -> "Bill":
        bill = record['bill']
        return cls(
            id=bill["id"],
            creator_id=bill["creator_id"],
            amount=bill["amount"],
            currency=bill["currency"],
            description=bill["description"],
            status=BillStatus(bill["status"]),
            created_at=bill["created_at"],
            changed_at=bill["changed_at"]
        )
