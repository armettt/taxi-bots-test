import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .states import OrderState
from .keyboards import *
from .db import *
from .config import GROUP_ID

router = Router()

user_last_order_time = {}
user_active_order = {}
callback_cooldown = {}


# ===================== START =====================

@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Використовуй меню", reply_markup=main_menu())


# ===================== CREATE ORDER =====================

@router.message(F.text == "Створити замовлення")
async def create_order_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user:
        await state.update_data(phone=user["phone"])
        await message.answer("Звідки їхати?")
        await state.set_state(OrderState.from_loc)
    else:
        await message.answer("Надішли номер телефону", reply_markup=contact_kb())
        await state.set_state(OrderState.phone)


@router.message(OrderState.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await save_user(message.from_user.id, phone)
    await state.update_data(phone=phone)
    await message.answer("Звідки їхати?")
    await state.set_state(OrderState.from_loc)


@router.message(OrderState.from_loc)
async def get_from(message: Message, state: FSMContext):
    await state.update_data(from_loc=message.text)
    await message.answer("Куди їхати?")
    await state.set_state(OrderState.to_loc)


@router.message(OrderState.to_loc)
async def get_to(message: Message, state: FSMContext):
    await state.update_data(to_loc=message.text)
    await message.answer("Коментар:")
    await state.set_state(OrderState.comment)


@router.message(OrderState.comment)
async def finish_order(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    now = time.time()

    if user_last_order_time.get(user_id, 0) + 30 > now:
        await message.answer("Зачекай 30 секунд", reply_markup=main_menu())
        return

    if user_id in user_active_order:
        await message.answer("У тебе вже є активне замовлення")
        return

    data = await state.get_data()
    username = message.from_user.username or message.from_user.first_name

    order_id = await create_order(
        user_id,
        data["phone"],
        username,
        data["from_loc"],
        data["to_loc"],
        message.text
    )

    text = (
        f"<b>Замовлення #{order_id}</b>\n"
        f"Телефон: {data['phone']}\n"
        f"Маршрут: {data['from_loc']} → {data['to_loc']}\n"
        f"Коментар: {message.text}"
    )

    sent = await bot.send_message(
        GROUP_ID,
        text,
        reply_markup=take_order_kb(order_id),
        parse_mode="HTML"
    )

    await update_order(order_id, "waiting", message_id=sent.message_id)

    user_last_order_time[user_id] = now
    user_active_order[user_id] = order_id

    await message.answer(
        "Замовлення створено!",
        reply_markup=main_menu()
    )
    await state.clear()


# ===================== TAKE ORDER =====================

@router.callback_query(F.data.startswith("take_"))
async def take_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    driver = await get_driver(callback.from_user.id)

    if not driver:
        await callback.answer("Ви не зареєстровані", show_alert=True)
        return

    order = await get_order(order_id)
    if order["status"] != "waiting":
        await callback.answer("Замовлення вже взято")
        return

    await update_order(order_id, "taken", callback.from_user.id)

    # Данные водителя
    driver_name = driver["username"] or "Невідомо"
    driver_phone = driver["phone"]
    brand = driver["brand"] or ""
    model = driver["model"] or ""
    color = driver["color"] or ""
    plate = driver["plate"] or ""

    car_info = f"{brand} {model}".strip()

    # Обновление сообщения в группе
    group_text = (
        callback.message.text +
        "\n\nВодій прийняв замовлення\n"
        f"Водій: {driver_name}\n"
        f"Телефон: {driver_phone}\n"
        f"Авто: {car_info}\n"
        f"Колір: {color}\n"
        f"Номер: {plate}"
    )

    await callback.message.edit_text(
        group_text,
        reply_markup=arrived_kb(order_id),
        parse_mode="HTML"
    )

    # Сообщение пассажиру
    passenger_text = (
        "<b>Водій взяв ваше замовлення</b>\n\n"
        f"Водій: {driver_name}\n"
        f"Телефон: <a href='tel:{driver_phone}'>{driver_phone}</a>\n"
        f"Автомобіль: {car_info}\n"
        f"Колір: {color}\n"
        f"Номер: {plate}"
    )

    await bot.send_message(
        order["client_id"],
        passenger_text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    await callback.answer("Замовлення прийнято")


# ===================== DRIVER ARRIVED =====================

@router.callback_query(F.data.startswith("arrived_"))
async def arrived_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await get_order(order_id)

    if callback.from_user.id != order["driver_id"]:
        await callback.answer("Це не ваше замовлення", show_alert=True)
        return

    await update_order(order_id, "arrived")

    await callback.message.edit_reply_markup(
        reply_markup=complete_kb(order_id)
    )

    await bot.send_message(
        order["client_id"],
        "Водій прибув!"
    )

    await callback.answer("Ви прибули")


# ===================== COMPLETE ORDER =====================

@router.callback_query(F.data.startswith("complete_"))
async def complete_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await get_order(order_id)

    if callback.from_user.id != order["driver_id"]:
        await callback.answer("Це не ваше замовлення", show_alert=True)
        return

    await update_order(order_id, "completed")
    await callback.message.edit_reply_markup()

    user_active_order.pop(order["client_id"], None)

    await bot.send_message(
        order["client_id"],
        "Поїздку завершено!"
    )

    await callback.answer("Поїздку завершено")


# ===================== CANCEL ORDER =====================

@router.message(F.text == "Скасувати замовлення")
async def cancel_order(message: Message, bot: Bot):
    user_id = message.from_user.id

    if user_id not in user_active_order:
        await message.answer("У вас немає активного замовлення.")
        return

    order_id = user_active_order[user_id]
    order = await get_order(order_id)

    if order["status"] not in ["waiting", "taken"]:
        await message.answer("Це замовлення вже не можна скасувати.")
        return

    await update_order(order_id, "cancelled")
    user_active_order.pop(user_id, None)

    # Уведомление группы
    try:
        await bot.edit_message_text(
            chat_id=GROUP_ID,
            message_id=order["message_id"],
            text=f"Замовлення #{order_id} скасовано клієнтом."
        )
    except Exception:
        pass

    # Уведомление водителя
    if order.get("driver_id"):
        try:
            await bot.send_message(
                order["driver_id"],
                f"Клієнт скасував замовлення #{order_id}."
            )
        except Exception:
            pass

    await message.answer(
        "Замовлення скасовано.",
        reply_markup=main_menu()
    )
