from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states import BillCreation
from storage.mock_storage import storage
from storage.neo4j_storage import storage, DebtStatus
from services.message_builder import MessageBuilder

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await storage.create_update_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    await message.answer(
        f"👋 Привет {message.from_user.first_name}! Я PayWithoutPain бот и помогу тебе контроллировать долги за общие счета!\n\n"
        "📝 Команды:\n"
        "/newbill — создать новый счёт\n"
        "/mybills — мои активные счета\n"
        "/mydebts — мои активные долги\n"
        "/pause {debt_id} - отложить долг\n"
        "/resume {debt_id} - возобновить долг\n"
        "/help — справка"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 **Справка**\n\n"
        "1. Создайте счёт через /newbill\n"
        "2. Добавьте участников (@username)\n"
        "3. Укажите сумму каждого вручную или разделите поровну\n"
        "4. Должники будут получать уведомления с кнопкой «Оплатить»\n"
        "5. После оплаты должник отправляет скриншот, вы его подтверждаете или отклоняете\n"
        "6. Если всё верно, долг закрывается\n"
        "7. Если у должника сейчас нет возможности оплатить, долг можно поставить на паузу. Уведомления по нему перестанут приходить, но это увидит плательщик\n"
        "8. В любой момент долг можно снять с паузы\n"
        "9. Долг можно закрыть частично\n"
    )


@router.message(Command("newbill"))
async def cmd_newbill(message: Message, state: FSMContext):
    await state.set_state(BillCreation.waiting_for_description)
    await message.answer(
        "📝 **Создание счёта**\n\n"
        "Введите описание счёта (например: «Ужин в кафе»):"
    )


@router.message(Command("mybills"))
async def cmd_mybills(message: Message):
    bills = await storage.get_user_bills(message.from_user.id)
    if not bills:
        await message.answer("✅️ У вас нет созданных счетов")
        return

    text = "⚡️ Ваши счета:\n\n"
    for bill in bills:
        debts = await storage.get_debts_for_bill(bill.id)
        debtors = [await storage.get_user_by_id(debt.debtor_id) for debt in debts]
        text += MessageBuilder.build_bill_message(bill, list(zip(debts, debtors)))
    await message.answer(text)


@router.message(Command("mydebts"))
async def cmd_mydebts(message: Message):
    debts = await storage.get_user_debts(message.from_user.id)
    if not debts:
        await message.answer("🎉 У вас нет активных долгов!")
        return

    text = "‼️ **Ваши долги:**\n\n"
    for debt in debts:
        bill = await storage.get_bill_by_id(debt.bill_id)
        payer = await storage.get_user_by_id(bill.creator_id)
        if not bill or not payer:
            await message.answer("Ошибка при загрузке данных по долгу. Пожалуйста, попробуйте снова.")
            continue
        text += MessageBuilder.build_debt_message(
            debt,
            bill,
            payer
        )

    await message.answer(text)
    
    
@router.callback_query(F.data.startswith("resume"))
async def callback_resume(callback: CallbackQuery):
    debt_id = callback.data.split()[1]
    user_id = callback.from_user.id
    
    debt_info = await storage.get_debt_by_id(debt_id)
    
    if not debt_info or debt_info.debtor_id != user_id:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    if debt_info.status != DebtStatus.PAUSED:
        await callback.answer("ℹ️ Не на паузе", show_alert=True)
        return
    
    await storage.update_debt_status(debt_id, DebtStatus.ACTIVE.value)
    
    await callback.answer("▶️ Долг активен")
    
@router.callback_query(F.data.startswith("pause"))
async def callback_pause(callback: CallbackQuery):
    debt_id = callback.data.split()[1]
    user_id = callback.from_user.id
    
    debt_info = await storage.get_debt_by_id(debt_id)
    
    if not debt_info or debt_info.debtor_id != user_id:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    if debt_info.status != DebtStatus.ACTIVE:
        await callback.answer("ℹ️ Не активен", show_alert=True)
        return
    
    await storage.update_debt_status(debt_id, DebtStatus.PAUSED.value)
    
    await callback.answer("⏸️ Долг на паузе")