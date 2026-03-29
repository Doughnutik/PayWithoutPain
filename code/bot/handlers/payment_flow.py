import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.states import PaymentProof, PaymentConfirmation
from bot.keyboards import get_confirmation_keyboard
from storage import storage, DebtStatus
from services.message_builder import MessageBuilder

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("pay_"))
async def handle_pay_request(callback: CallbackQuery, state: FSMContext):
    debt_id = callback.data.split("_")[1]
    debtor_id = callback.from_user.id
    
    debt = await storage.get_debt_by_id(debt_id)
    
    if not debt or debt.debtor_id != debtor_id:
        await callback.answer("❌ Долг не найден", show_alert=True)
        return
    
    if debt.status != DebtStatus.ACTIVE:
        await callback.answer(f"ℹ️ Текущий статус {debt.status.value} не равен {DebtStatus.ACTIVE.value}", show_alert=True)
        return
    
    bill = await storage.get_bill_by_id(debt.bill_id)
    
    await state.update_data(debt=debt, bill=bill)
    await state.set_state(PaymentProof.waiting_for_amount)
    
    text = MessageBuilder.build_debt_message(debt, bill, await storage.get_user_by_id(bill.creator_id))
    text += "Введите сумму оплаты:"
    await callback.message.answer(
        text
    )
    await callback.answer()


@router.message(PaymentProof.waiting_for_amount)
async def handle_payment_amount(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    if not text.replace(".", "", 1).isdigit():
        await message.answer("❌ Введите число:")
        return
    
    amount = float(text)
    if amount <= 0:
        await message.answer("❌ Введите положительное число:")
        return
    
    data = await state.get_data()
    debt = data['debt']
    bill = data['bill']
    
    if amount > debt.amount:
        await message.answer(
            f"⚠️ Сумма {amount:.2f}{bill.currency} превышает остаток долга {debt.amount:.2f}{bill.currency}\n\n"
            f"Введите сумму не более {debt.amount:.2f}{bill.currency}:"
        )
        return
    
    await state.update_data(paid_amount=amount)
    await state.set_state(PaymentProof.waiting_for_screenshot)
    
    await message.answer(
        f"📸 Отправьте скриншот оплаты на {amount:.2f}{bill.currency}:"
    )


@router.message(F.photo, StateFilter(PaymentProof.waiting_for_screenshot))
async def handle_screenshot_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    debt = data['debt']
    bill = data['bill']
    paid_amount = data['paid_amount']
    
    screenshot_id = message.photo[-1].file_id
    
    await storage.update_debt_status(debt.id, DebtStatus.PENDING.value)
    
    await message.answer(
        f"✅ Скриншот отправлен!\n\n"
        f"💰 Сумма оплаты: {paid_amount:.2f}{bill.currency}\n"
        f"📝 Счёт: {bill.description}\n\n"
        f"Ожидайте подтверждения от плательщика."
    )
    
    debtor_name = '@' + message.from_user.username if message.from_user.username else message.from_user.first_name
    try:
        caption = (
            f"🔔 Новая оплата по счёту\n\n"
            f"👤 Должник: {debtor_name}\n"
            f"💰 Сумма оплаты: {paid_amount:.2f}{bill.currency}\n"
            f"📊 Общий долг: {debt.amount:.2f}{bill.currency}\n"
            f"📝 Счёт: {bill.id}\n"
            f"📋 Описание: {bill.description}\n\n"
            f"Проверьте поступление средств и подтвердите оплату:"
        )
        
        await message.bot.send_photo(
            chat_id=bill.creator_id,
            photo=screenshot_id,
            caption=caption,
            reply_markup=get_confirmation_keyboard(debt.id, paid_amount, bill.currency)
        )
        
        logger.info(f"Partial payment screenshot forwarded to payer {bill.creator_id} for debt {debt.id}")
        
    except Exception as e:
        logger.error(f"Failed to forward screenshot to payer: {e}")
        await message.answer("⚠️ Не удалось уведомить плательщика")
    
    await state.clear()


@router.callback_query(F.data.startswith("confirm_pay"))
async def handle_confirm_payment(callback: CallbackQuery):
    parts = callback.data.split("_")
    debt_id = parts[2]
    paid_amount = float(parts[3])
    payer_id = callback.from_user.id
    
    debt = await storage.get_debt_by_id(debt_id)
    
    if not debt:
        await callback.answer("❌ Долг не найден", show_alert=True)
        return
    
    bill = await storage.get_bill_by_id(debt.bill_id)
    
    if bill.creator_id != payer_id:
        await callback.answer("❌ Вы не являетесь плательщиком", show_alert=True)
        return
    
    if debt.status != DebtStatus.PENDING:
        await callback.answer(f"ℹ️ Текущий статус {debt.status.value} не равен {DebtStatus.PENDING.value}", show_alert=True)
        return
    
    debt = await storage.decrease_debt_amount(debt_id, paid_amount)
    if not debt:
        await callback.answer(f"❌ Ошибка при обновлении долга {debt_id}", show_alert=True)
        return
    
    bill = await storage.decrease_bill_amount(bill.id, paid_amount)
    if not bill:
        await callback.answer(f"❌ Ошибка при обновлении счёта {bill.id}", show_alert=True)
        return
    
    status_text = f"✅ Осталось: {(bill.amount):.2f}{bill.currency}"
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n{status_text}"
    )
    
    try:
        await callback.message.bot.send_message(
            chat_id=debt.debtor_id,
            text=(
                f"✅ Оплата подтверждена!\n\n"
                f"📌 Долг: {debt.id}\n"
                f"💰 Внесено: {paid_amount:.2f}{bill.currency}\n"
                f"📊 Осталось: {debt.amount:.2f}{bill.currency}\n"
                f"📝 Счёт: {bill.description}"
            )
        )
    except Exception as e:
        logger.error(f"Failed to notify debtor about confirmation: {e}")
    
    await callback.answer("✅ Оплата подтверждена")


@router.callback_query(F.data.startswith("reject_pay_"))
async def handle_reject_payment(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    debt_id = parts[2]
    paid_amount = float(parts[3])
    payer_id = callback.from_user.id
    
    debt = await storage.get_debt_by_id(debt_id)
    
    if not debt:
        await callback.answer("❌ Долг не найден", show_alert=True)
        return
    
    bill = await storage.get_bill_by_id(debt.bill_id)
    
    if bill.creator_id != payer_id:
        await callback.answer("❌ Вы не являетесь плательщиком", show_alert=True)
        return
    
    if debt.status != DebtStatus.PENDING:
        await callback.answer(f"ℹ️ Текущий статус {debt.status.value} не равен {DebtStatus.PENDING.value}", show_alert=True)
        return
    
    await state.update_data(debt=debt, bill=bill, paid_amount=paid_amount)
    await state.set_state(PaymentConfirmation.waiting_for_decision)
    
    await callback.message.answer(
        f"✍️ Введите причину отклонения\n\n"
        f"Сумма оплаты: {paid_amount:.2f}{bill.currency}\n\n"
        f"Например: «Не получил средства, проверьте реквизиты»"
    )
    await callback.answer()


@router.message(PaymentConfirmation.waiting_for_decision)
async def handle_reject_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    debt = data['debt']
    paid_amount = data['paid_amount']
    bill = data['bill']
    
    reason = message.text.strip()
    
    await storage.update_debt_status(debt.id, DebtStatus.ACTIVE.value)
    
    await message.answer("❌ Оплата отклонена. Должник уведомлён.")
    
    try:
        await message.bot.send_message(
            chat_id=debt.debtor_id,
            text=(
                f"❌ Оплата отклонена\n\n"
                f"📌 Долг: {debt.id}\n"
                f"💰 Сумма: {paid_amount:.2f}{bill.currency}\n\n"
                f"📝 Причина:\n{reason}\n\n"
                f"Пожалуйста, проверьте транзакцию и отправьте скриншот повторно."
            )
        )
    except Exception as e:
        logger.error(f"Failed to notify debtor about rejection: {e}")
    
    await state.clear()
