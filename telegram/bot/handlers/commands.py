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
        "👋 Привет! Я бот для разделения счетов.\n\n"
        "📝 Команды:\n"
        "/newbill — создать новый счёт\n"
        "/mybills — мои созданные счета\n"
        "/debts — мои активные долги\n"
        "/closed — закрытые счета\n"
        "/help — справка"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 **Справка**\n\n"
        "1. Создайте счёт через /newbill\n"
        "2. Добавьте участников (@username)\n"
        "3. Укажите сумму и разделите поровну или вручную\n"
        "4. Должники получат уведомление с кнопкой «Оплатить»\n"
        "5. После оплаты должник отправляет скриншот\n"
        "6. Вы подтверждаете оплату — долг закрывается"
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
        await message.answer("📭 У вас нет созданных счетов")
        return

    text = "📋 **Ваши счета:**\n\n"
    for bill in bills:
        status_emoji = {"active": "🟢", "closed": "✅", "archived": "🗄️"}.get(bill.status, "⚪")
        text += f"{status_emoji} `{bill.id}` — {bill.description}\n"
        text += f"   Осталось: {bill.amount_left:.2f} ₽ | Статус: {bill.status}\n\n"

    await message.answer(text)


@router.message(Command("debts"))
async def cmd_debts(message: Message):
    debts = await storage.get_user_debts(message.from_user.id, status="pending")
    if not debts:
        await message.answer("🎉 У вас нет активных долгов!")
        return

    text = "💸 **Ваши долги:**\n\n"
    for debt in debts:
        bill = await storage.get_bill(debt.bill_id)
        text += f"📌 Счёт `{debt.bill_id}` ({bill.description})\n"
        text += f"   Сумма: {debt.amount:.2f} ₽\n"
        text += f"   Плательщик: @{(await storage.get_or_create_user(debt.payer_id, '', '')).username}\n\n"

    await message.answer(text)


@router.message(Command("closed"))
async def cmd_closed(message: Message):
    bills = await storage.get_user_bills(message.from_user.id, status="closed")
    if not bills:
        await message.answer("📭 Нет закрытых счетов")
        return

    text = "✅ **Закрытые счета:**\n\n"
    for bill in bills:
        unpaid = [d for d in bill.debts if d.status != "confirmed"]
        text += f"📌 `{bill.id}` — {bill.description}\n"
        if unpaid:
            text += f"   ⚠️ Не оплачено долгов: {len(unpaid)}\n"
        text += "\n"

    await message.answer(text)
    
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Действие отменено.")
    else:
        await message.answer("ℹ️ Нет активных действий для отмены.")

@router.message(Command("notifications"))
async def cmd_notifications(message: Message):
    """Показывает настройки уведомлений"""
    is_muted = await storage.get_user_notification_settings(message.from_user.id)
    
    if is_muted:
        text = "🔕 **Уведомления отключены**\n\n"
        text += "Вы не получаете напоминания о долгах.\n\n"
        text += "Включить уведомления? /enable_notifications"
    else:
        text = "🔔 **Уведомления включены**\n\n"
        text += "Вы получаете напоминания о долгах.\n\n"
        text += "Отключить уведомления? /disable_notifications"
    
    await message.answer(text)


@router.message(Command("disable_notifications"))
async def cmd_disable_notifications(message: Message):
    """Отключает уведомления"""
    await storage.set_user_notification_settings(message.from_user.id, True)
    await message.answer("🔕 Уведомления отключены. Вы больше не будете получать напоминания о долгах.")


@router.message(Command("enable_notifications"))
async def cmd_enable_notifications(message: Message):
    """Включает уведомления"""
    await storage.set_user_notification_settings(message.from_user.id, False)
    await message.answer("🔔 Уведомления включены. Вы будете получать напоминания о долгах.")


@router.callback_query(F.data.startswith("mute_"))
async def callback_mute_debt(callback: CallbackQuery):
    """Отключает уведомления по конкретному долгу"""
    # В данной реализации просто отключаем все уведомления
    await storage.set_user_notification_settings(callback.from_user.id, True)
    await callback.answer("🔕 Уведомления отключены", show_alert=True)
    await callback.message.edit_text(
        callback.message.text + "\n\n🔕 Уведомления отключены"
    )