from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states import BillCreation, PaymentProof
from bot.keyboards import get_split_mode_keyboard
from storage.mock_storage import storage
from storage.neo4j_storage import storage

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await storage.get_or_create_user(
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
        "/pause - отложить долг\n"
        "/resume - возобновить долг\n"
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
        debtors: list[tuple[str, float, str]] = bill.get_debtors() # get username, amount_left, debt_status
        text += f"Cчёт: {bill.id}\n"
        text += f"Описание: {bill.description}\n"
        text += f"Осталось: {bill.amount_left:.2f} + {bill.currency}\n"
        text += "Должники:\n"
        for debtor in debtors:
            text += f"Username: @{debtor[0]}, amount: {debtor[1]:.2f}{bill.currency}, status: {debtor[2]}\n"
        text += "\n"
    await message.answer(text)


@router.message(Command("mydebts"))
async def cmd_mydebts(message: Message):
    debts = await storage.get_user_debts(message.from_user.id)
    if not debts:
        await message.answer("🎉 У вас нет активных долгов!")
        return

    text = "‼️ **Ваши долги:**\n\n"
    for debt in debts:
        bill = await storage.get_bill(debt.bill_id)
        text += f"Cчёт: {bill.id}\n"
        text += f"Описание: {bill.description}\n"
        text += f"Остаток: {debt.amount:.2f}{bill.currency}\n"
        text += f"Плательщик: @{await storage.get_or_create_user(debt.payer_id).username}\n"
        text += f"Статус: {debt.status}\n\n"

    await message.answer(text)
    
    
@router.callback_query(F.data.startswith("resume"))
async def callback_resume(callback: CallbackQuery):
    debt_id = callback.data.split()[1]
    user_id = callback.from_user.id
    
    debt_info = await storage.get_debt_info(debt_id)
    
    if not debt_info or debt_info["debt"].debtor_id != user_id:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    if debt_info["debt"].status != "paused":
        await callback.answer("ℹ️ Не на паузе", show_alert=True)
        return
    
    await storage.resume_debt(debt_id)
    
    await callback.message.edit_text(
        callback.message.text + "\n\n▶️ **Возобновлено**"
    )
    await callback.answer("▶️ Долг активен")