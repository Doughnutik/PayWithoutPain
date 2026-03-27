from aiogram.fsm.state import State, StatesGroup


class BillCreation(StatesGroup):
    waiting_for_description = State()
    waiting_for_amount = State()
    waiting_for_currency = State()
    waiting_for_participants = State()
    waiting_for_split_mode = State()
    waiting_for_manual_amounts = State()
    confirmation = State()


class PaymentProof(StatesGroup):
    waiting_for_screenshot = State()