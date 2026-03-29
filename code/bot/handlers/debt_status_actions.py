from aiogram import Router, F
from aiogram.types import CallbackQuery
from storage import storage, DebtStatus


router = Router()


@router.callback_query(F.data.startswith("resume_"))
async def handle_resume_debt(callback: CallbackQuery):
    debt_id = callback.data.split("_")[1]
    debt = await storage.get_debt_by_id(debt_id)
    
    if not debt:
        await callback.answer("❌ Долг не найден", show_alert=True)
        return
    
    if debt.status != DebtStatus.PAUSED:
        await callback.answer(f"ℹ️ Текущий статус {debt.status.value} не равен {DebtStatus.PAUSED.value}", show_alert=True)
        return

    result = await storage.update_debt_status(debt_id, DebtStatus.ACTIVE.value)
    if not result:
        await callback.answer("❌ Не удалось обновить статус долга", show_alert=True)
        return
    
    await callback.message.answer(f"Долг {debt.id} теперь имеет статус {DebtStatus.ACTIVE.value}")
    await callback.answer()
    

@router.callback_query(F.data.startswith("pause_"))
async def handle_pause_debt(callback: CallbackQuery):
    debt_id = callback.data.split("_")[1]
    debt = await storage.get_debt_by_id(debt_id)
    
    if not debt:
        await callback.answer("❌ Долг не найден", show_alert=True)
        return
    
    if debt.status != DebtStatus.ACTIVE:
        await callback.answer(f"ℹ️ Текущий статус {debt.status.value} не равен {DebtStatus.ACTIVE.value}", show_alert=True)
        return

    result = await storage.update_debt_status(debt_id, DebtStatus.PAUSED.value)
    if not result:
        await callback.answer("❌ Не удалось обновить статус долга", show_alert=True)
        return
    
    await callback.message.answer(f"Долг {debt.id} теперь имеет статус {DebtStatus.PAUSED.value}")
    await callback.answer()
