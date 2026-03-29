from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from storage.neo4j_storage import DebtStatus


def get_split_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔢 Поровну", callback_data="split_equal")
    builder.button(text="✍️ Вручную", callback_data="split_manual")
    return builder.as_markup()


def get_confirmation_keyboard(debt_id: str, payment_amount: float, currency: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅ Принять {payment_amount:.2f}{currency}", callback_data=f"confirm_{debt_id}_{payment_amount}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{debt_id}_{payment_amount}")
    builder.adjust(2)
    return builder.as_markup()


def get_debt_keyboard(debt_id: str, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.button(text=f"💰 Оплатить", callback_data=f"pay_{debt_id}")
    
    if status == DebtStatus.ACTIVE:
        builder.button(text="⏸️ На паузу", callback_data=f"pause_{debt_id}")
    else:
        builder.button(text="▶️ Возобновить", callback_data=f"resume_{debt_id}")
        
    builder.adjust(1)
    return builder.as_markup()


def get_bill_keyboard(bill_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅️ Закрыть долг", callback_data=f"close_{bill_id}")
    return builder.as_markup()


def get_yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=yes_data)
    builder.button(text="❌ Нет", callback_data=no_data)
    return builder.as_markup()