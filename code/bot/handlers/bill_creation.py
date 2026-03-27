from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import BillCreation
from bot.keyboards import get_split_mode_keyboard, get_yes_no_keyboard
from storage.neo4j_storage import storage
from services.notification_service import notification_service

router = Router()


@router.message(BillCreation.waiting_for_description)
async def handle_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(BillCreation.waiting_for_amount)
    await message.answer("💰 Введите общую сумму счёта (число, например 4000):")


@router.message(BillCreation.waiting_for_amount)
async def handle_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Неверная сумма. Введите положительное число:")
        return

    await state.update_data(amount=amount)
    await state.set_state(BillCreation.waiting_for_participants)
    await message.answer(
        "👥 Введите участников через пробел (@username):\n"
        "Например: @misha @grisha @tisha\n\n"
        "Или отправьте /skip чтобы добавить только себя:"
    )


@router.message(BillCreation.waiting_for_participants, F.text == "/skip")
async def skip_participants(message: Message, state: FSMContext):
    username = message.from_user.username or f"user_{message.from_user.id}"
    await state.update_data(participants=[username])
    await state.set_state(BillCreation.waiting_for_split_mode)
    await message.answer(
        "🔢 Как разделить сумму?",
        reply_markup=get_split_mode_keyboard()
    )


@router.message(BillCreation.waiting_for_participants)
async def handle_participants(message: Message, state: FSMContext):
    usernames = [u.strip() for u in message.text.split() if u.startswith("@")]
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
    
    # Защита от деления на ноль
    if not participants:
        await callback.answer("❌ Ошибка: нет участников", show_alert=True)
        return
        
    per_person = amount / len(participants)

    await state.update_data(split_mode="equal", per_person=per_person)
    await state.set_state(BillCreation.confirmation)

    text = "✅ **Подтверждение счёта**\n\n"
    text += f"📝 Описание: {data['description']}\n"
    text += f"💰 Сумма: {amount:.2f} ₽\n"
    text += f"👥 Участников: {len(participants)}\n"
    text += f"🔢 Разделение: поровну\n"
    text += f"💵 С каждого: {per_person:.2f} ₽\n\n"
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

    # Инициализируем индекс 0 и пустой словарь сумм
    await state.update_data(split_mode="manual", manual_index=0, manual_amounts={})
    await state.set_state(BillCreation.waiting_for_manual_amounts)

    await callback.message.answer(
        f"✍️ Введите сумму для {participants[0]}:\n"
        f"(осталось ввести для {len(participants)} участников)"
    )
    await callback.answer()


@router.message(BillCreation.waiting_for_manual_amounts)
async def handle_manual_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число:")
        return

    data = await state.get_data()
    participants = data["participants"]
    manual_index = data.get("manual_index", 0)
    manual_amounts = data.get("manual_amounts", {})

    # 🔒 ЗАЩИТА: Проверяем, не вышли ли мы за границы списка
    if manual_index >= len(participants):
        await message.answer("⚠️ Произошла ошибка синхронизации. Пожалуйста, начните создание счёта заново (/newbill).")
        await state.clear()
        return

    # Сохраняем сумму для текущего участника
    current_user = participants[manual_index]
    manual_amounts[current_user] = amount
    
    # Увеличиваем индекс для следующего шага
    next_index = manual_index + 1
    await state.update_data(manual_amounts=manual_amounts, manual_index=next_index)

    # Проверяем, ввели ли все суммы
    if next_index >= len(participants):
        total_manual = sum(manual_amounts.values())
        total_bill = data["amount"]

        if abs(total_manual - total_bill) > 0.01:
            diff = total_bill - total_manual
            sign = "+" if diff > 0 else ""
            await message.answer(
                f"⚠️ Сумма долей ({total_manual:.2f}) не совпадает с общей ({total_bill:.2f})\n"
                f"Разница: {sign}{diff:.2f} ₽\n\n"
                f"Введите сумму для {current_user} повторно:"
            )
            # Откатываем индекс, чтобы пользователь ввёл сумму заново
            await state.update_data(manual_index=manual_index)
            return

        await state.set_state(BillCreation.confirmation)
        text = "✅ **Подтверждение счёта**\n\n"
        text += f"📝 Описание: {data['description']}\n"
        text += f"💰 Сумма: {total_bill:.2f} ₽\n"
        text += f"👥 Участников: {len(participants)}\n"
        text += f"🔢 Разделение: вручную\n\n"
        for p, a in manual_amounts.items():
            text += f"   {p}: {a:.2f} ₽\n"
        text += "\nСоздать счёт?"

        await message.answer(
            text,
            reply_markup=get_yes_no_keyboard("confirm_create", "cancel_create")
        )
    else:
        # Запрос следующей суммы
        await message.answer(
            f"✍️ Введите сумму для {participants[next_index]}:\n"
            f"(осталось ввести для {len(participants) - next_index} участников)"
        )

@router.callback_query(BillCreation.confirmation, F.data == "confirm_create")
async def confirm_create_bill(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    creator_id = callback.from_user.id
    creator_username = callback.from_user.username or f"user_{creator_id}"

    # Создаём счёт
    bill = await storage.create_bill(
        creator_id=creator_id,
        amount=data["amount"],
        description=data["description"]
    )

    # Создаём долги и отправляем уведомления
    participants = data["participants"]
    if data["split_mode"] == "equal":
        per_person = data["per_person"]
        for p in participants:
            # Ищем пользователя по username в Neo4j
            debtor = await storage.get_user_by_username(p)
            if debtor:
                debtor_id = debtor.telegram_id
            else:
                # Если пользователь не найден, создаём заглушку
                debtor_id = creator_id  # Или пропускаем
            debt = await storage.add_debt(
                bill_id=bill.id,
                debtor_id=debtor_id,
                payer_id=creator_id,
                amount=per_person
            )
            # 🆕 Отправляем начальное уведомление
            if notification_service:
                await notification_service.send_initial_notification(
                    debt_id=debt.id,
                    debtor_id=debtor_id,
                    bill_description=bill.description,
                    amount=per_person,
                    payer_username=creator_username
                )
    else:
        for p, amount in data["manual_amounts"].items():
            debtor_id = creator_id  # Заглушка
            debt = await storage.add_debt(
                bill_id=bill.id,
                debtor_id=debtor_id,
                payer_id=creator_id,
                amount=amount
            )
            # 🆕 Отправляем начальное уведомление
            if notification_service:
                await notification_service.send_initial_notification(
                    debt_id=debt.id,
                    debtor_id=debtor_id,
                    bill_description=bill.description,
                    amount=amount,
                    payer_username=creator_username
                )

    await callback.message.answer(
        f"✅ Счёт `{bill.id}` создан!\n"
        f"Осталось собрать: {bill.amount_left:.2f} ₽\n\n"
        f"Должники получили уведомления."
    )
    await state.clear()
    await callback.answer()


@router.callback_query(BillCreation.confirmation, F.data == "cancel_create")
async def cancel_create_bill(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("❌ Создание счёта отменено")
    await state.clear()
    await callback.answer()