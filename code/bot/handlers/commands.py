from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states import BillCreation, DebtStatusUpdate
from storage import storage
from services.message_builder import MessageBuilder
from bot.keyboards import get_debt_keyboard, get_close_bill_keyboard


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
        "/help — справка"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 Справка\n\n"
        "1. Создайте счёт через /newbill\n"
        "2. Добавьте участников (@username)\n"
        "3. Укажите сумму каждого вручную или разделите поровну\n"
        "4. Должники будут получать уведомления с кнопкой «Оплатить»\n"
        "5. После оплаты должник отправляет скриншот, вы его подтверждаете или отклоняете\n"
        "6. Если всё верно, долг закрывается\n"
        "7. Если у должника сейчас нет возможности оплатить, долг можно поставить на паузу. Уведомления по нему перестанут приходить, но это увидит плательщик\n"
        "8. В любой момент долг можно снять с паузы\n"
        "9. Долг можно закрыть частично\n"
        "10. Счёт можно закрыть самостоятельно, тогда все долги по нему закроются"
    )


@router.message(Command("newbill"))
async def cmd_newbill(message: Message, state: FSMContext):
    await state.set_state(BillCreation.waiting_for_description)
    await message.answer(
        "📝 Создание счёта\n\n"
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
    
    for bill in bills:
        await message.answer(
            f"💰 Счёт: {bill.id}",
            reply_markup=get_close_bill_keyboard(bill.id)
        )


@router.message(Command("mydebts"))
async def cmd_mydebts(message: Message):
    debts = await storage.get_user_debts(message.from_user.id)
    if not debts:
        await message.answer("🎉 У вас нет активных долгов!")
        return

    text = "‼️ Ваши долги:\n\n"
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
    
    for debt in debts:
        await message.answer(
            f"💰 Долг: {debt.id}",
            reply_markup=get_debt_keyboard(debt.id, debt.status)
        )
    
    
@router.message(Command("resume"))
async def cmd_resume(message: Message, state: FSMContext):
    await state.set_state(DebtStatusUpdate.waiting_for_resume)
    await message.answer(
        "Введите id долга, который хотите возобновить:"
    )
    
@router.message(Command("pause"))
async def cmd_pause(message: Message, state: FSMContext):
    await state.set_state(DebtStatusUpdate.waiting_for_pause)
    await message.answer(
        "Введите id долга, который хотите поставить на паузу:"
    )
