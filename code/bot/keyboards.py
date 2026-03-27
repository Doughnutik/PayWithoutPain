from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_split_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔢 Поровну", callback_data="split_equal")
    builder.button(text="✍️ Вручную", callback_data="split_manual")
    return builder.as_markup()


def get_confirmation_keyboard(debt_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"confirm_{debt_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{debt_id}")
    builder.adjust(2)
    return builder.as_markup()


def get_payment_keyboard(debt_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Оплатить", callback_data=f"pay_{debt_id}")
    builder.button(text="⏸️ На паузу", callback_data=f"pause_{debt_id}")
    return builder.as_markup()


def get_bill_actions_keyboard(bill_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статус", callback_data=f"bill_status_{bill_id}")
    builder.button(text="🗄️ Архивировать", callback_data=f"archive_{bill_id}")
    return builder.as_markup()


def get_debt_status_keyboard(debt_id: str) -> InlineKeyboardMarkup:
    """Информация о долге"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Детали", callback_data=f"debt_info_{debt_id}")
    return builder.as_markup()