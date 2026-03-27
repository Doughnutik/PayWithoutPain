from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import BillCreation
from bot.keyboards import get_split_mode_keyboard, get_yes_no_keyboard
from storage.neo4j_storage import storage
from services.notification_service import NotificationService


router = Router()


@router.message(BillCreation.waiting_for_description)
async def handle_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(BillCreation.waiting_for_amount)
    await message.answer("💰 Введите общую сумму счёта за вычетом своей части (число, например 4000):")


@router.message(BillCreation.waiting_for_amount)
async def handle_amount(message: Message, state: FSMContext):
    amount = float(message.text.replace(",", ".").strip())
    if amount <= 0:
        await message.answer("❌ Неверная сумма. Введите положительное число:")
        return
    
    await state.update_data(amount=amount)
    await state.set_state(BillCreation.waiting_for_currency)
    await message.answer("💱 Введите валюту 3 буквами (например RUB, USD, EUR):")


@router.message(BillCreation.waiting_for_currency)
async def handle_currency(message: Message, state: FSMContext):
    currency = message.text.upper().strip()
    if len(currency) != 3 or not currency.isalpha():
        await message.answer("❌ Неверный формат валюты. Введите 3 буквы (например RUB, USD, EUR):")
        return
    
    await state.update_data(currency=currency)
    await state.set_state(BillCreation.waiting_for_participants)
    await message.answer(
        "👥 Введите участников через пробел (@username):\n"
        "Например: @misha @grisha @tisha"
    )


@router.message(BillCreation.waiting_for_participants)
async def handle_participants(message: Message, state: FSMContext):
    usernames = [u.lstrip('@') for u in message.text.split() if u.startswith("@")]
    if not usernames:
        await message.answer("❌ Не найдено участников. Введите @username через пробел:")
        return

    await state.update_data(participants=usernames)
    await state.set_state(BillCreation.waiting_for_split_mode)
    await message.answer(
        "🔢 Как разделить сумму?",
        reply_markup=get_split_mode_keyboard()
    )


@router.callback_query(BillCreation.waiting_for_split_mode, F.data == "split_equal")
async def handle_split_equal(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data["amount"]
    participants = data["participants"]
    
    if not participants:
        await callback.answer("❌ Ошибка: нет участников", show_alert=True)
        return
        
    per_person = amount / len(participants)

    await state.update_data(split_mode="equal", per_person=per_person)
    await state.set_state(BillCreation.confirmation)

    text = "✅ **Подтверждение счёта**\n\n"
    text += f"📝 Описание: {data['description']}\n"
    text += f"💰 Сумма: {amount:.2f}{data['currency']}\n"
    text += f"👥 Участников: {len(participants)}\n"
    text += f"🔢 Разделение: поровну\n"
    text += f"💵 С каждого: {per_person:.2f}{data['currency']}\n\n"
    text += "Создать счёт?"

    await callback.message.answer(
        text,
        reply_markup=get_yes_no_keyboard("confirm_create", "cancel_create")
    )
    await callback.answer()


@router.callback_query(BillCreation.waiting_for_split_mode, F.data == "split_manual")
async def handle_split_manual(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    participants = data["participants"]

    await state.update_data(split_mode="manual", manual_index=0, remain_sum=data['amount'], manual_amounts=[])
    await state.set_state(BillCreation.waiting_for_manual_amounts)

    await callback.message.answer(
        f"✍️ Введите сумму для {participants[0]}:\n"
        f"(осталось ввести для {len(participants)} участников)"
    )
    await callback.answer()


@router.message(BillCreation.waiting_for_manual_amounts)
async def handle_manual_amount(message: Message, state: FSMContext):
    amount = float(message.text.replace(",", ".").strip())
    if amount < 0:
        await message.answer("❌ Введите положительное число:")
        return

    data = await state.get_data()
    remain_sum = data['remain_sum']
    
    if amount > remain_sum:
        await message.answer(f"❌ Значение не может быть больше {remain_sum:.2f}. Введите корректное значение:")
        return
    
    participants = data["participants"]
    manual_index = data.get("manual_index", 0)
    manual_amounts = data.get("manual_amounts", [])

    if manual_index >= len(participants):
        await message.answer("⚠️ Произошла ошибка синхронизации. Пожалуйста, начните создание счёта заново (/newbill).")
        await state.clear()
        return
    
    if manual_index == len(participants) - 1 and amount != remain_sum:
        await message.answer(f"❌ Для последнего участника нужно ввести оставшуюся сумму {remain_sum:.2f}. Пожалуйста, введите корректное значение:")
        return

    manual_amounts.append(amount)
    next_index = manual_index + 1
    await state.update_data(manual_amounts=manual_amounts, manual_index=next_index, remain_sum=remain_sum - amount)

    if next_index >= len(participants):
        await state.set_state(BillCreation.confirmation)
        text = "✅ **Подтверждение счёта**\n\n"
        text += f"📝 Описание: {data['description']}\n"
        text += f"💰 Сумма: {data['amount']:.2f}{data['currency']}\n"
        text += f"👥 Участников: {len(participants)}\n"
        text += f"🔢 Разделение: вручную\n\n"
        for i in range(len(participants)):
            text += f"@{participants[i]}: {manual_amounts[i]:.2f}{data['currency']}\n"
        text += "\nСоздать счёт?"

        await message.answer(
            text,
            reply_markup=get_yes_no_keyboard("confirm_create", "cancel_create")
        )
    else:
        await message.answer(
            f"✍️ Введите сумму для {participants[next_index]}:\n"
            f"(осталось ввести для {len(participants) - next_index} участников)"
        )

@router.callback_query(BillCreation.confirmation, F.data == "confirm_create")
async def confirm_create_bill(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    creator_id = callback.from_user.id

    bill = await storage.create_bill(
        creator_id=creator_id,
        amount=data["amount"],
        description=data["description"],
        currency=data['currency']
    )

    participants = data["participants"]
    if data["split_mode"] == "equal":
        per_person = data["per_person"]
        for p in participants:
            debtor = await storage.get_user_by_username(p)
            if not debtor:
                await callback.message.answer("❌ Ошибка при создании долга. Пожалуйста, попробуйте снова.")
                await state.clear()
                return
            
            await storage.create_debt(
                bill_id=bill.id,
                debtor_id=debtor.telegram_id,
                amount=per_person
            )
    else:
        amounts = data["manual_amounts"]
        for i in range(len(participants)):
            debtor = await storage.get_user_by_username(participants[i])
            if not debtor:
                await callback.message.answer("❌ Ошибка при создании долга. Пожалуйста, попробуйте снова.")
                await state.clear()
                return  
            
            await storage.create_debt(
                bill_id=bill.id,
                debtor_id=debtor.telegram_id,
                amount=amounts[i]
            )

    await callback.message.answer(
        f"✅ Счёт `{bill.id}` создан!\n"
        f"Осталось собрать: {bill.amount:.2f}{bill.currency}\n\n"
        f"Должники получили уведомления."
    )
    await state.clear()
    await callback.answer()


@router.callback_query(BillCreation.confirmation, F.data == "cancel_create")
async def cancel_create_bill(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("❌ Создание счёта отменено")
    await state.clear()
    await callback.answer()