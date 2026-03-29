from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from storage import storage
from bot.states import BillClosure
from bot.keyboards import get_yes_no_keyboard


router = Router()


@router.callback_query(F.data.startswith("close_"))
async def handle_close_bill(callback: CallbackQuery, state: FSMContext):
    bill_id = callback.data.split("_")[1]
    bill = await storage.get_bill_by_id(bill_id)

    if not bill:
        await callback.answer("❌ Счёт не найден", show_alert=True)
        return

    await state.set_state(BillClosure.waiting_for_confirmation)
    await state.update_data(bill=bill)

    text = f"❓️ **Закрытие счёта {bill.id}**\n\n"
    text += f"📝 Описание: {bill.description}\n"
    text += f"💰 Сумма: {bill.amount:.2f}{bill.currency}\n\n"
    text += "Вы уверены, что хотите закрыть счёт? Это действие нельзя будет отменить!"
        
    await callback.message.answer(
            text,
            reply_markup=get_yes_no_keyboard("confirm_close", "cancel_close")
        )
    
    await callback.answer()
    
@router.callback_query(BillClosure.waiting_for_confirmation, F.data == "confirm_close")
async def confirm_close_bill(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bill = data['bill']
    
    debts = await storage.get_debts_for_bill(bill.id)
    if not debts:
        await callback.answer("❌ Не найдено долгов по этому счёту", show_alert=True)
        return
    
    for debt in debts:
        if debt.amount > 0:
            result = await storage.decrease_debt_amount(debt.id, debt.amount)
            if not result:
                await callback.answer("❌ Не удалось закрыть долг по счёту", show_alert=True)
                return
    
    result = await storage.decrease_bill_amount(bill.id, bill.amount)
    if not result:
        await callback.answer("❌ Не удалось закрыть счёт", show_alert=True)
        return
    
    await callback.message.answer(f"✅ Счёт {bill.id} успешно закрыт вместе со всеми долгами!")
    await state.clear()
    await callback.answer()
    
@router.callback_query(BillClosure.waiting_for_confirmation, F.data == "cancel_close")
async def cancel_close_bill(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("❌ Закрытие счёта отменено")
    await state.clear()
    await callback.answer()