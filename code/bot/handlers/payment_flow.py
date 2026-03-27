import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PhotoSize
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext

from bot.states import PaymentProof, PaymentConfirmation
from bot.keyboards import get_payment_keyboard, get_confirmation_keyboard
from storage.neo4j_storage import storage, DebtStatus

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("pay_"))
async def handle_pay_request(callback: CallbackQuery, state: FSMContext):
    debt_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    debt_info = await storage.get_debt_by_id(debt_id)
    
    if not debt_info or debt_info.debtor_id != user_id:
        await callback.answer("❌ Долг не найден", show_alert=True)
        return
    
    if debt_info.status != DebtStatus.ACTIVE:
        await callback.answer(f"ℹ️ Неподходящий статус: {debt_info.status.value}", show_alert=True)
        return
    
    currency = (await storage.get_bill_by_id(debt_info.bill_id)).currency
    
    await state.update_data(debt_id=debt_id, total_amount=debt_info.amount, currency=currency)
    await state.set_state(PaymentProof.waiting_for_amount)
    
    await callback.message.answer("Укажите сумму, которую хотите оплатить:")
    await callback.answer()
    

@router.message(PaymentProof.waiting_for_amount)
async def handle_amount(message: Message, state: FSMContext):
    amount = float(message.text.replace(",", ".").strip())
    if amount <= 0:
        await message.answer("❌ Неверная сумма. Введите положительное число:")
        return
    
    data = await state.get_data()
    total_amount = data.get("total_amount")
    currency = data.get("currency")
    
    if amount > total_amount:
        await message.answer(f"❌ Сумма не может быть больше общего долга {total_amount:.2f}{currency}. Введите корректную сумму:")
        return
    
    await state.update_data(paid_amount=amount)
    await state.set_state(PaymentProof.waiting_for_screenshot)
    await message.answer("Пожалуйста, отправьте скриншот оплаты в этот чат:")


@router.message(F.photo, StateFilter(PaymentProof.waiting_for_screenshot))
async def handle_screenshot_photo(message: Message, state: FSMContext):
    await process_screenshot(message, state)


async def process_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    debt_id = data.get("debt_id")
    
    screenshot_id = message.photo[-1].file_id
    
    debt_info = await storage.get_debt_by_id(debt_id)
    
    bill_id = debt_info.bill_id
    bill = await storage.get_bill_by_id(bill_id)
    payer_id = bill.creator_id
    
    await message.answer(
        "✅ **Скриншот отправлен!**\n\n"
        f"💰 Сумма: {data['paid_amount']:.2f}{data['currency']}\n"
        f"📝 Счёт: {bill.description}\n\n"
        "Ожидайте подтверждения от плательщика."
    )
    
    try:
        debtor = '@' + message.from_user.username if message.from_user.username else message.from_user.first_name
        caption = (
            f"🔔 **Новая оплата по счёту**\n\n"
            f"👤 Должник: {debtor}\n"
            f"💰 Сумма: {data['paid_amount']:.2f}{data['currency']}\n"
            f"📝 Счёт: {bill.description}\n\n"
            "Проверьте поступление средств и подтвердите оплату:"
        )
        
        await message.bot.send_photo(
            chat_id=payer_id,
            photo=screenshot_id,
            caption=caption,
            reply_markup=get_confirmation_keyboard(debt_id),
            parse_mode="Markdown"
        )
        
        logger.info(f"Screenshot forwarded to payer {payer_id} for debt {debt_id}")
        
    except Exception as e:
        logger.error(f"Failed to forward screenshot to payer: {e}")
        await message.answer("❌ Не удалось уведомить плательщика")
    
    await state.clear()


@router.message(Command("cancel"), StateFilter(PaymentProof.waiting_for_screenshot))
async def cancel_screenshot(message: Message, state: FSMContext):
    await message.answer("❌ Отправка скриншота отменена")
    await state.clear()


# ============================================================================
# 2️⃣ ПЛАТЕЛЬЩИК: Получает скриншот и кнопки "Принять/Отклонить"
# ============================================================================

@router.callback_query(F.data.startswith("confirm_"))
async def handle_confirm_payment(callback: CallbackQuery):
    debt_id = callback.data.split("_")[1]
    payer_id = callback.from_user.id
    
    debt_info = await storage.get_debt_by_id(debt_id)
    bill = await storage.get_bill_by_id(debt_info.bill_id)
    
    if bill.creator_id != payer_id:
        await callback.answer("❌ Вы не являетесь плательщиком", show_alert=True)
        return
    
    updated_bill = await storage.decrease_debt_amount(debt_id, )
    
    # Уведомляем плательщика
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ **Оплата подтверждена**",
        reply_markup=None
    )
    
    # 🆕 ОТПРАВЛЯЕМ РЕЗУЛЬТАТ ДОЛЖНИКУ
    try:
        await callback.message.bot.send_message(
            chat_id=debt.debtor_id,
            text=(
                f"✅ **Оплата подтверждена!**\n\n"
                f"📌 ID: `{debt_id}`\n"
                f"💰 Сумма: {debt.amount:.2f} ₽\n"
                f"📝 Счёт: {bill.description if bill else 'N/A'}\n\n"
                f"🎉 Ваш долг закрыт!"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify debtor about confirmation: {e}")
    
    await callback.answer("✅ Оплата подтверждена")


@router.callback_query(F.data.startswith("reject_"))
async def handle_reject_payment(callback: CallbackQuery, state: FSMContext):
    """Плательщик отклоняет оплату"""
    debt_id = callback.data.split("_")[1]
    payer_id = callback.from_user.id
    
    # Проверяем долг
    debt_info = await storage.get_debt_with_details(debt_id)
    
    if not debt_info:
        await callback.answer("❌ Долг не найден", show_alert=True)
        return
    
    debt = debt_info["debt"]
    bill = debt_info.get("bill")
    
    # Проверяем, что пользователь — плательщик
    if debt.payer_id != payer_id:
        await callback.answer("❌ Вы не являетесь плательщиком", show_alert=True)
        return
    
    # Проверяем статус
    if debt.status != "paid":
        await callback.answer(f"ℹ️ Статус: {debt.status}", show_alert=True)
        return
    
    # Сохраняем данные для запроса комментария
    await state.update_data(debt_id=debt_id, debtor_id=debt.debtor_id)
    await state.set_state(PaymentConfirmation.waiting_for_decision)
    
    await callback.message.answer(
        "✍️ **Введите причину отклонения**\n\n"
        "Например: «Не получил средства, проверьте реквизиты»\n\n"
        "❌ /cancel — отменить отклонение"
    )
    await callback.answer()


@router.message(PaymentConfirmation.waiting_for_decision)
async def handle_reject_reason(message: Message, state: FSMContext):
    """Плательщик вводит причину отклонения"""
    data = await state.get_data()
    debt_id = data.get("debt_id")
    debtor_id = data.get("debtor_id")
    
    if not debt_id or not debtor_id:
        await message.answer("❌ Ошибка: нет данных о долге")
        await state.clear()
        return
    
    reason = message.text.strip()
    
    # Возвращаем долг в статус pending
    await storage.update_debt_status(debt_id, "pending")
    
    # Уведомляем плательщика
    await message.answer("❌ Оплата отклонена. Должник уведомлён.")
    
    # 🆕 ОТПРАВЛЯЕМ РЕЗУЛЬТАТ ДОЛЖНИКУ
    try:
        await message.bot.send_message(
            chat_id=debtor_id,
            text=(
                f"❌ **Оплата отклонена**\n\n"
                f"📌 ID: `{debt_id}`\n"
                f"💰 Сумма: {debt.amount:.2f} ₽\n\n"
                f"📝 **Причина:**\n{reason}\n\n"
                "Пожалуйста, проверьте транзакцию и отправьте скриншот повторно."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify debtor about rejection: {e}")
    
    await state.clear()


@router.message(Command("cancel"), StateFilter(PaymentConfirmation.waiting_for_decision))
async def cancel_rejection(message: Message, state: FSMContext):
    """Плательщик отменяет отклонение"""
    await message.answer("❌ Отклонение отменено")
    await state.clear()


# ============================================================================
# 3️⃣ ДОЛЖНИК: Получает результат (подтверждено/отклонено)
# ============================================================================
# (Реализовано в handle_confirm_payment и handle_reject_reason выше)