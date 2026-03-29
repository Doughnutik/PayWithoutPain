# ==================== USER ====================

CREATE_UPDATE_USER = """
MERGE (user:User {telegram_id: $telegram_id})
ON CREATE SET
    user.username = $username,
    user.first_name = $first_name,
    user.created_at = datetime()
ON MATCH SET
    user.username = $username,
    user.first_name = $first_name
RETURN user
"""

GET_USER_BY_ID = """
MATCH (user:User {telegram_id: $telegram_id})
RETURN user
"""

GET_USER_BY_USERNAME = """
MATCH (user:User {username: $username})
RETURN user
"""

# ==================== BILL ====================

CREATE_BILL = """
MATCH (creator:User {telegram_id: $creator_id})
CREATE (bill:Bill {
    id: $bill_id,
    creator_id: $creator_id,
    amount: $amount,
    currency: $currency,
    description: $description,
    status: 'active',
    created_at: datetime(),
    changed_at: datetime()
})
CREATE (creator)-[:CREATED]->(bill)
RETURN bill
"""

GET_BILL_BY_ID = """
MATCH (bill:Bill {id: $bill_id})
RETURN bill
"""

GET_USER_BILLS = """
MATCH (creator:User {telegram_id: $telegram_id})-[:CREATED]->(bill:Bill)
WHERE bill.status = 'active'
RETURN bill ORDER BY bill.changed_at DESC
"""

DECREASE_BILL_AMOUNT = """
MATCH (bill:Bill {id: $bill_id})
SET bill.amount = bill.amount - $delta,
    bill.changed_at = datetime(),
    bill.status = CASE 
        WHEN bill.amount - $delta <= 0 THEN 'closed'
        ELSE 'active'
    END
RETURN bill
"""

# ==================== DEBT ====================

CREATE_DEBT = """
MATCH (bill:Bill {id: $bill_id})
MATCH (debtor:User {telegram_id: $debtor_id})
CREATE (debt:Debt {
    id: $debt_id,
    bill_id: $bill_id,
    debtor_id: $debtor_id,
    amount: $amount,
    status: 'active',
    created_at: datetime(),
    changed_at: datetime(),
    notifications_count: 0
})
CREATE (debtor)-[:OWES]->(debt)
CREATE (bill)-[:HAS_DEBT]->(debt)
RETURN debt
"""

GET_DEBT_BY_ID = """
MATCH (debt:Debt {id: $debt_id})
RETURN debt
"""

GET_USER_DEBTS = """
MATCH (debtor:User {telegram_id: $telegram_id})-[:OWES]->(debt:Debt)
WHERE debt.status <> 'closed'
RETURN debt ORDER BY debt.changed_at ASC
"""

UPDATE_DEBT_STATUS = """
MATCH (debt:Debt {id: $debt_id})
SET debt.status = $status,
    debt.changed_at = datetime()
RETURN debt
"""

DECREASE_DEBT_AMOUNT = """
MATCH (debt:Debt {id: $debt_id})
SET debt.amount = debt.amount - $delta,
    debt.changed_at = datetime(),
    debt.status = CASE 
        WHEN debt.amount - $delta <= 0 THEN 'closed'
        ELSE 'active'
    END
RETURN debt
"""

GET_DEBTS_FOR_BILL = """
MATCH (bill:Bill {id: $bill_id})-[:HAS_DEBT]->(debt:Debt)
WHERE debt.status <> 'closed'
RETURN debt ORDER BY debt.changed_at ASC
"""

UPDATE_DEBT_NOTIFICATIONS = """
MATCH (debt:Debt {id: $debt_id})
SET debt.notifications_count = debt.notifications_count + 1,
    debt.last_notification_at = datetime()
RETURN debt
"""

GET_ALL_DEBTS_FOR_REMINDER = """
MATCH (debt:Debt)
WHERE debt.status = 'active'
RETURN debt"""