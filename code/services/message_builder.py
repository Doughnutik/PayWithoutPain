from storage import Debt, User, Bill, DebtStatus, BillStatus

class MessageBuilder:
    @staticmethod
    def build_debt_message(debt: Debt, bill: Bill, payer: User) -> str:
        if debt.status == DebtStatus.CLOSED:
            return f"✅ Долг по счёту {bill.id} {bill.description} закрыт."
        
        payer_name = '@' + payer.username if payer.username else payer.first_name
        if debt.status == DebtStatus.ACTIVE:
            status_text = "⏳ Ожидает оплаты"
        elif debt.status == DebtStatus.PENDING:
            status_text = "📸 Скриншот отправлен"
        elif debt.status == DebtStatus.PAUSED:
            status_text = "⏸️ Долг на паузе"
        text = f"""📌 **Долг: {debt.id}**
📋 **Описание: {bill.description}**
💰 **Ваш долг: {debt.amount:.2f}{bill.currency}**
👤 **Плательщик: {payer_name}**
    Статус: {status_text}\n
"""

        return text

    @staticmethod
    def build_bill_message(bill: Bill, debts_info: list[tuple[Debt, User]]) -> str:
        if bill.status == BillStatus.CLOSED:
            return f"✅ Счёт {bill.id} {bill.description} закрыт."
        
        text = f"""📌 **Счёт: {bill.id}**
💰 **Сумма: {bill.amount:.2f}{bill.currency}**
📋 **Описание: {bill.description}**\n
"""

        for debt, debtor in debts_info:
            if debt.status == DebtStatus.CLOSED:
                continue
            
            debtor_name = '@' + debtor.username if debtor.username else debtor.first_name
            text += f"👤 **Должник: {debtor_name} - {debt.amount:.2f}{bill.currency}**\n"
            
            if debt.status == DebtStatus.ACTIVE:
                status_text = "⏳ Ожидает оплаты"
            elif debt.status == DebtStatus.PENDING:
                status_text = "📸 Скриншот отправлен"
            elif debt.status == DebtStatus.PAUSED:
                status_text = "⏸️ Долг на паузе"
            text += f"  Статус: {status_text}\n\n"

        return text
    