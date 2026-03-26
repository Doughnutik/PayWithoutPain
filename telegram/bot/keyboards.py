from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_split_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔢 Поровну", callback_data="split_equal")
    builder.button(text="✍️ Вручную", callback_data="split_manual")
    return builder.as_markup()


def get_payment_keyboard(debt_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Оплатить", callback_data=f"pay_{debt_id}")
    builder.button(text="🔕 Не напоминать", callback_data=f"mute_{debt_id}")
    return builder.as_markup()


def get_confirmation_keyboard(debt_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm_{debt_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{debt_id}")
    return builder.as_markup()


def get_bill_actions_keyboard(bill_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статус", callback_data=f"bill_status_{bill_id}")
    builder.button(text="🗄️ Архивировать", callback_data=f"archive_{bill_id}")
    return builder.as_markup()


def get_yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=yes_data)
    builder.button(text="❌ Нет", callback_data=no_data)
    return builder.as_markup()