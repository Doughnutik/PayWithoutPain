from aiogram import Router
from aiogram.types import Message
from bot.states import DebtStatusUpdate
from storage.neo4j_storage import storage, DebtStatus


router = Router()
    
    
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