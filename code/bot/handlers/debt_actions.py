from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext

from bot.states import PaymentProof, DebtStatusUpdate
from bot.keyboards import get_confirmation_keyboard
from storage.neo4j_storage import storage, DebtStatus, Debt

router = Router()


@router.message(PaymentProof.waiting_for_id)
async def handle_id(message: Message, state: FSMContext):
    debt_id = message.text
    debt_info = await storage.get_debt_by_id(debt_id)

    if not debt_info or debt_info.debtor_id != message.from_user.id:
        await message.answer("❌ Неверный id долга. Пожалуйста, попробуйте снова:")
        return
    
    currency = (await storage.get_bill_by_id(debt_info.bill_id)).currency
    
    await state.update_data(debt_id=debt_id, total_amount=debt_info.amount, currency=currency)
    await state.set_state(PaymentProof.waiting_for_amount)
    await message.answer("Укажите сумму долга, которую хотите оплатить:")

@router.message(PaymentProof.waiting_for_amount)
async def handle_amount(message: Message, state: FSMContext):
    amount = float(message.text.replace(",", ".").strip())
    if amount <= 0:
        await message.answer("❌ Неверная сумма. Введите положительное число:")
        return
    
    data = await state.get_data()
    debt_id = data.get("debt_id")
    total_amount = data.get("total_amount")
    currency = data.get("currency")
    
    if amount > total_amount:
        await message.answer(f"❌ Сумма не может быть больше общего долга {total_amount:.2f}{currency}. Введите корректную сумму:")
        return
    
    await state.update_data(paid_amount=amount)
    await state.set_state(PaymentProof.waiting_for_screenshot)
    await message.answer("Пожалуйста, отправьте скриншот оплаты в этот чат:")

@router.message(F.photo, StateFilter(PaymentProof.waiting_for_screenshot))
async def handle_screenshot(message: Message, state: FSMContext):
    screenshot_id = message.photo[-1].file_id
    await storage.update_debt_status(debt_id, "paid", screenshot_id)

    debt = await storage.get_debt(debt_id)
    payer = await storage.get_or_create_user(debt.payer_id, "", "")

    await message.answer("✅ Скриншот отправлен! Ожидайте подтверждения от плательщика.")

    # Уведомление плательщику
    await message.bot.send_message(
        chat_id=debt.payer_id,
        text=f"🔔 @{message.from_user.username or message.from_user.first_name} отправил скриншот оплаты!\n"
             f"Сумма: {debt.amount:.2f} ₽\n\n"
             f"Проверьте поступление и подтвердите оплату.",
        reply_markup=get_confirmation_keyboard(debt_id)
    )

    await state.clear()


@router.callback_query(F.data.startswith("confirm"))
async def handle_confirm(callback: CallbackQuery):
    debt_id = callback.data.split()[1]
    bill = await storage.confirm_debt(debt_id)

    debt = await storage.get_debt_by_id(debt_id)
    debtor = await storage.get_or_create_user(debt.debtor_id, "", "")

    await callback.message.answer(f"✅ Оплата подтверждена! Долг закрыт.")

    # Уведомление должнику
    await callback.message.bot.send_message(
        chat_id=debt.debtor_id,
        text=f"✅ Ваша оплата по счёту `{bill.id}` подтверждена!\n"
             f"Сумма: {debt.amount:.2f} ₽\n"
             f"Остаток по счёту: {bill.amount:.2f} ₽"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reject_"))
async def handle_reject(callback: CallbackQuery):
    debt_id = callback.data.split("_")[1]
    await storage.update_debt_status(debt_id, "pending")

    debt = await storage.get_debt(debt_id)
    debtor = await storage.get_or_create_user(debt.debtor_id, "", "")

    await callback.message.answer("❌ Оплата отклонена. Должник будет уведомлён.")

    await callback.message.bot.send_message(
        chat_id=debt.debtor_id,
        text=f"❌ Плательщик отклонил вашу оплату по счёту.\n"
             f"Пожалуйста, проверьте транзакцию и отправьте скриншот повторно."
    )
    await callback.answer()

    
@router.message(DebtStatusUpdate.waiting_for_resume)
async def handle_resume_status(message: Message):
    debt_id = message.text.strip()
    debt_info = await storage.get_debt_by_id(debt_id)
    
    if not debt_info or debt_info.debtor_id != message.from_user.id:
        await message.answer("❌ Неверный id долга. Пожалуйста, попробуйте снова:")
        return
    
    if debt_info.status != DebtStatus.PAUSED:
        await message.answer("❌ Этот долг не на паузе. Пожалуйста, введите id другого долга:")
        return
    
    await storage.update_debt_status(debt_id, DebtStatus.ACTIVE.value)
    await message.answer("▶️ Долг активен")
    

@router.message(DebtStatusUpdate.waiting_for_pause)
async def handle_pause_status(message: Message):
    debt_id = message.text.strip()
    debt_info = await storage.get_debt_by_id(debt_id)
    
    if not debt_info or debt_info.debtor_id != message.from_user.id:
        await message.answer("❌ Неверный id долга. Пожалуйста, попробуйте снова:")
        return
    
    if debt_info.status != DebtStatus.ACTIVE:
        await message.answer("❌ Этот долг не активен. Пожалуйста, введите id другого долга:")
        return
    
    await storage.update_debt_status(debt_id, DebtStatus.PAUSED.value)
    await message.answer("⏸️ Долг на паузе")