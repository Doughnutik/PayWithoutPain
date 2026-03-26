# ==================== USER ====================

CREATE_USER = """
MERGE (u:User {telegram_id: $telegram_id})
ON CREATE SET
    u.username = $username,
    u.first_name = $first_name,
    u.created_at = datetime()
ON MATCH SET
    u.username = COALESCE($username, u.username),
    u.first_name = COALESCE($first_name, u.first_name)
RETURN u
"""

GET_USER_BY_ID = """
MATCH (u:User {telegram_id: $telegram_id})
RETURN u
"""

# ==================== BILL ====================

CREATE_BILL = """
MATCH (creator:User {telegram_id: $creator_id})
CREATE (b:Bill {
    id: $bill_id,
    amount_left: $amount,
    currency: $currency,
    description: $description,
    status: 'active',
    created_at: datetime(),
    changed_at: datetime()
})
CREATE (creator)-[:CREATED]->(b)
RETURN b
"""

GET_BILL_BY_ID = """
MATCH (b:Bill {id: $bill_id})
RETURN b
"""

GET_USER_BILLS = """
MATCH (creator:User {telegram_id: $telegram_id})-[:CREATED]->(b:Bill)
WHERE $status IS NULL OR b.status = $status
RETURN b ORDER BY b.changed_at DESC
"""

UPDATE_BILL_AMOUNT = """
MATCH (b:Bill {id: $bill_id})
SET b.amount_left = b.amount_left - $amount,
    b.changed_at = datetime()
WITH b
WHERE b.amount_left <= 0
SET b.status = 'closed'
RETURN b
"""

ARCHIVE_BILL = """
MATCH (b:Bill {id: $bill_id})
SET b.status = 'archived',
    b.changed_at = datetime()
RETURN b
"""

# ==================== DEBT ====================

CREATE_DEBT = """
MATCH (bill:Bill {id: $bill_id})
MATCH (debtor:User {telegram_id: $debtor_id})
MATCH (payer:User {telegram_id: $payer_id})
CREATE (d:Debt {
    id: $debt_id,
    amount: $amount,
    status: 'pending',
    created_at: datetime(),
    changed_at: datetime()
})
CREATE (debtor)-[:OWES]->(d)
CREATE (payer)-[:PAID_TO]->(d)
CREATE (bill)-[:HAS_DEBT]->(d)
RETURN d
"""

GET_DEBT_BY_ID = """
MATCH (d:Debt {id: $debt_id})
RETURN d
"""

GET_USER_DEBTS = """
MATCH (debtor:User {telegram_id: $telegram_id})-[:OWES]->(d:Debt)
WHERE $status IS NULL OR d.status = $status
WITH d
MATCH (bill:Bill)-[:HAS_DEBT]->(d)
MATCH (payer:User)-[:PAID_TO]->(d)
RETURN d, bill, payer ORDER BY d.changed_at ASC
"""

UPDATE_DEBT_STATUS = """
MATCH (d:Debt {id: $debt_id})
SET d.status = $status,
    d.changed_at = datetime()
WITH d
WHERE $screenshot IS NOT NULL
SET d.proof_screenshot = $screenshot
RETURN d
"""

GET_DEBTS_FOR_BILL = """
MATCH (b:Bill {id: $bill_id})-[:HAS_DEBT]->(d:Debt)
WHERE $status IS NULL OR d.status = $status
RETURN d ORDER BY d.changed_at ASC
"""

GET_BILL_WITH_DEBTS = """
MATCH (b:Bill {id: $bill_id})-[:HAS_DEBT]->(d:Debt)
OPTIONAL MATCH (debtor:User)-[:OWES]->(d)
OPTIONAL MATCH (payer:User)-[:PAID_TO]->(d)
RETURN b, collect({debt: d, debtor: debtor, payer: payer}) as debts
"""

# ==================== NOTIFICATIONS ====================

GET_ACTIVE_DEBTS_FOR_NOTIFICATION = """
MATCH (b:Bill)-[:HAS_DEBT]->(d:Debt)
WHERE d.status IN ['pending', 'paid']
  AND b.status <> 'archived'
  AND b.changed_at < datetime() - duration({hours: $hours})
WITH d, b
MATCH (debtor:User)-[:OWES]->(d)
RETURN d, b, debtor
"""

# Обновление счётчика уведомлений
UPDATE_DEBT_NOTIFICATION_COUNT = """
MATCH (d:Debt {id: $debt_id})
SET d.notification_count = COALESCE(d.notification_count, 0) + 1,
    d.last_notification_at = datetime()
RETURN d
"""

# Сброс счётчика при оплате
RESET_DEBT_NOTIFICATION_COUNT = """
MATCH (d:Debt {id: $debt_id})
SET d.notification_count = 0,
    d.last_notification_at = null
RETURN d
"""

# Получение долгов для напоминания
GET_DEBTS_FOR_REMINDER = """
MATCH (b:Bill)-[:HAS_DEBT]->(d:Debt)
WHERE d.status IN ['pending', 'paid']
  AND b.status <> 'archived'
  AND (d.last_notification_at IS NULL 
       OR d.last_notification_at < datetime() - duration({hours: $hours}))
  AND (d.notification_count IS NULL OR d.notification_count < $max_count)
WITH d, b
MATCH (debtor:User)-[:OWES]->(d)
MATCH (payer:User)-[:PAID_TO]->(d)
RETURN d, b, debtor, payer
ORDER BY d.changed_at ASC
"""

# Проверка, заблокировал ли пользователь бота (опционально)
GET_USER_NOTIFICATION_SETTINGS = """
MATCH (u:User {telegram_id: $telegram_id})
RETURN u.notifications_muted as muted
"""

UPDATE_USER_NOTIFICATION_SETTINGS = """
MATCH (u:User {telegram_id: $telegram_id})
SET u.notifications_muted = $muted
RETURN u
"""