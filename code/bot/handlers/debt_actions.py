from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext

from bot.states import PaymentProof
from bot.keyboards import get_payment_keyboard, get_confirmation_keyboard
from storage.neo4j_storage import storage

router = Router()


@router.callback_query(F.data.startswith("pay"))
async def handle_pay(callback: CallbackQuery, state: FSMContext):
    debt_id = callback.data.split()[1]
    debt = await storage.get_debt_by_id(debt_id)

    if not debt:
        await callback.answer("❌ Долг не найден", show_alert=True)
        return

    await state.update_data(debt_id=debt_id)
    await state.set_state(PaymentProof.waiting_for_screenshot)
    await callback.message.answer(
        "📸 Отправьте скриншот оплаты:\n\n"
        "(или отправьте /cancel для отмены)"
    )
    await callback.answer()


@router.message(F.photo, StateFilter(PaymentProof.waiting_for_screenshot))
async def handle_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    debt_id = data.get("debt_id")

    if not debt_id:
        await message.answer("❌ Ошибка: нет активного долга")
        await state.clear()
        return

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


@router.message(Command("cancel"), StateFilter(PaymentProof.waiting_for_screenshot))
async def cancel_screenshot(message: Message, state: FSMContext):
    await message.answer("❌ Отправка скриншота отменена.")
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


@router.callback_query(F.data.startswith("archive_"))
async def handle_archive(callback: CallbackQuery):
    bill_id = callback.data.split("_")[1]
    bill = await storage.get_bill(bill_id)

    if bill.creator_id != callback.from_user.id:
        await callback.answer("❌ Только создатель может архивировать счёт", show_alert=True)
        return

    await storage.archive_bill(bill_id)
    await callback.message.answer(f"🗄️ Счёт `{bill_id}` заархивирован. Уведомления отключены.")
    await callback.answer()