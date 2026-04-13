import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from .states import OrderState
from .keyboards import (
    main_menu,
    contact_kb,
    take_order_kb,
    arrived_kb,
    complete_kb
)
from .db import (
    get_user,
    save_user,
    create_order,
    update_order,
    get_order,
    get_driver,
    try_take_order,
    has_active_order
)
from .config import GROUP_ID

router = Router()

user_last_order_time = {}


# ---------------- UTILS ----------------
def normalize_phone(phone: str) -> str:
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone.startswith("+"):
        phone = f"+{phone}"
    return phone


def phone_to_html(phone: str) -> str:
    phone_clean = normalize_phone(phone)
    return f'<a href="tel:{phone_clean}">{phone}</a>'


# ---------------- START ----------------
@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Головне меню", reply_markup=main_menu())


# ---------------- CANCEL DURING ORDER CREATION ----------------
@router.message(
    StateFilter(
        OrderState.phone,
        OrderState.from_loc,
        OrderState.to_loc,
        OrderState.comment
    ),
    F.text == "Скасувати замовлення"
)
async def cancel_order_during_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Створення замовлення скасовано",
        reply_markup=main_menu()
    )


# ---------------- CREATE ORDER ----------------
@router.message(F.text == "Створити замовлення")
async def create_order_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)

    if user:
        await state.update_data(phone=user["phone"])
        await message.answer("Введіть адресу відправлення")
        await state.set_state(OrderState.from_loc)
    else:
        await message.answer(
            "Надішліть номер телефону",
            reply_markup=contact_kb()
        )
        await state.set_state(OrderState.phone)


# ---------------- PHONE ----------------
@router.message(OrderState.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone = normalize_phone(message.contact.phone_number)

    await save_user(message.from_user.id, phone)
    await state.update_data(phone=phone)

    await message.answer("Введіть адресу відправлення")
    await state.set_state(OrderState.from_loc)


# ---------------- FROM ----------------
@router.message(OrderState.from_loc)
async def get_from(message: Message, state: FSMContext):
    await state.update_data(from_loc=message.text)
    await message.answer("Введіть адресу призначення")
    await state.set_state(OrderState.to_loc)


# ---------------- TO ----------------
@router.message(OrderState.to_loc)
async def get_to(message: Message, state: FSMContext):
    await state.update_data(to_loc=message.text)
    await message.answer("Коментар до замовлення")
    await state.set_state(OrderState.comment)


# ---------------- FINISH ORDER ----------------
@router.message(OrderState.comment)
async def finish_order(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    now = time.time()

    if user_last_order_time.get(user_id, 0) + 30 > now:
        await message.answer("⏳ Потрібно зачекати 30 секунд")
        return

    if await has_active_order(user_id):
        await message.answer("❌ У вас вже є активне замовлення")
        return

    data = await state.get_data()

    phone = normalize_phone(data["phone"])
    phone_html = phone_to_html(phone)

    username = message.from_user.username
    first_name = message.from_user.first_name
    user_identity = f"@{username}" if username else first_name

    order_id = await create_order(
        user_id,
        phone,
        user_identity,
        data["from_loc"],
        data["to_loc"],
        message.text
    )

    text = (
        f"<b>Замовлення #{order_id}</b>\n"
        f"👤 Клієнт: {user_identity}\n"
        f"📞 Телефон: {phone_html}\n"
        f"📍 Від: {data['from_loc']}\n"
        f"🏁 До: {data['to_loc']}\n"
        f"💬 Коментар: {message.text}"
    )

    sent = await bot.send_message(
        GROUP_ID,
        text,
        reply_markup=take_order_kb(order_id),
        parse_mode="HTML"
    )

    await update_order(order_id, "waiting", message_id=sent.message_id)

    user_last_order_time[user_id] = now

    await message.answer("✅ Замовлення створено", reply_markup=main_menu())
    await state.clear()


# ---------------- CANCEL FROM MENU (FIXED) ----------------
@router.message(F.text == "Скасувати замовлення")
async def cancel_order_from_menu(message: Message, bot: Bot):
    user_id = message.from_user.id

    order = await has_active_order(user_id)
    if not order:
        await message.answer(
            "❌ У вас немає активних замовлень",
            reply_markup=main_menu()
        )
        return

    order = await get_order(order["id"])

    # Обновляем статус заказа
    await update_order(order["id"], "cancelled")

    # Обновляем сообщение в группе
    if order.get("message_id"):
        try:
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=order["message_id"],
                text=f"❌ Замовлення #{order['id']} скасовано пасажиром",
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Уведомление пассажира
    await bot.send_message(
        order["client_id"],
        f"❌ Ваше замовлення №{order['id']} скасовано"
    )

    # Уведомление водителя
    if order.get("driver_id"):
        await bot.send_message(
            order["driver_id"],
            f"❌ Замовлення №{order['id']} скасовано пасажиром"
        )

    # Ответ пользователю
    await message.answer(
        f"❌ Замовлення №{order['id']} скасовано",
        reply_markup=main_menu()
    )


# ---------------- TAKE ORDER ----------------
@router.callback_query(F.data.startswith("take_"))
async def take_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    driver_id = callback.from_user.id

    driver = await get_driver(driver_id)
    if not driver:
        await callback.answer("Ви не зареєстровані як водій", show_alert=True)
        return

    result = await try_take_order(order_id, driver_id)
    if not result:
        await callback.answer("Замовлення вже взято іншим водієм", show_alert=True)
        return

    order = await get_order(order_id)

    client_phone_html = phone_to_html(order["phone"])

    driver_username = driver.get("username") or callback.from_user.full_name
    driver_phone = driver.get("phone")
    driver_brand = driver.get("brand", "")
    driver_model = driver.get("model", "")
    driver_color = driver.get("color", "")
    driver_plate = driver.get("plate", "")

    if driver_phone:
        driver_phone = normalize_phone(driver_phone)
        driver_phone_html = phone_to_html(driver_phone)
    else:
        driver_phone_html = "Не вказано"

    car_info = " ".join(filter(None, [driver_brand, driver_model])).strip()
    car_full_info = f"{car_info} ({driver_color})" if driver_color else car_info

    # ---------------- GROUP MESSAGE ----------------
    group_text = (
        f"<b>Замовлення #{order_id}</b>\n"
        f"👤 Клієнт: {order['username']}\n"
        f"📞 Телефон: {client_phone_html}\n"
        f"📍 Від: {order['from_loc']}\n"
        f"🏁 До: {order['to_loc']}\n"
        f"💬 Коментар: {order['comment']}\n\n"
        f"<b>🚖 Прийнято водієм</b>\n"
        f"👨‍✈️ Водій: {driver_username}\n"
        f"📞 Телефон: {driver_phone_html}\n"
        f"🚗 Авто: {car_full_info}\n"
        f"🔢 Номер: {driver_plate}"
    )

    await callback.message.edit_text(
        group_text,
        reply_markup=arrived_kb(order_id),
        parse_mode="HTML"
    )

    # ---------------- CLIENT MESSAGE (FIXED) ----------------
    client_text = (
        f"🚖 <b>Ваше замовлення прийнято!</b>\n\n"
        f"📍 Від: {order['from_loc']}\n"
        f"🏁 До: {order['to_loc']}\n\n"
        f"👨‍✈️ Водій: {driver_username}\n"
        f"📞 Телефон: {driver_phone_html}\n"
        f"🚗 Авто: {car_full_info}\n"
        f"🎨 Колір: {driver_color}\n"
        f"🔢 Номер: {driver_plate}"
    )

    await bot.send_message(
        order["client_id"],
        client_text,
        parse_mode="HTML"
    )

    await bot.send_message(
        driver_id,
        f"✅ Ви прийняли замовлення №{order_id}"
    )

    await callback.answer("Ви взяли замовлення")
# ---------------- CANCEL CALLBACK (SECURE) ----------------
@router.callback_query(F.data.startswith("cancel_"))
async def cancel_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await get_order(order_id)

    if not order:
        await callback.answer("Замовлення не знайдено", show_alert=True)
        return

    user_id = callback.from_user.id
    client_id = order["client_id"]
    driver_id = order.get("driver_id")

    # уже завершено
    if order["status"] in ("completed", "cancelled"):
        await callback.answer("Замовлення вже завершено", show_alert=True)
        return

    # ---------------- WAITING ----------------
    # водитель МОЖЕТ отменить
    if order["status"] == "waiting":
        allowed = True  # любой водитель или клиент

    # ---------------- TAKEN / ARRIVED ----------------
    elif order["status"] in ("taken", "arrived"):
        allowed = (user_id == client_id) or (user_id == driver_id)

    else:
        allowed = False

    if not allowed:
        await callback.answer("Ви не можете скасувати це замовлення", show_alert=True)
        return

    # определить кто отменил
    if user_id == client_id:
        cancelled_by = "пасажиром"
    elif user_id == driver_id:
        cancelled_by = "водієм"
    else:
        cancelled_by = "водієм"

    await update_order(order_id, "cancelled")

    try:
        if order.get("message_id"):
            await bot.edit_message_text(
                chat_id=GROUP_ID,
                message_id=order["message_id"],
                text=f"❌ Замовлення #{order_id} скасовано {cancelled_by}",
                parse_mode="HTML"
            )
    except:
        pass

    # пассажиру всегда
    await bot.send_message(
        client_id,
        f"❌ Ваше замовлення №{order_id} скасовано"
    )

    # водителю если есть
    if driver_id:
        await bot.send_message(
            driver_id,
            f"❌ Замовлення №{order_id} скасовано"
        )

    await callback.answer("Замовлення скасовано")

# ---------------- ARRIVED ----------------
@router.callback_query(F.data.startswith("arrived_"))
async def arrived_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await get_order(order_id)

    if callback.from_user.id != order["driver_id"]:
        await callback.answer("Не ваше", show_alert=True)
        return

    await update_order(order_id, "arrived")

    await callback.message.edit_reply_markup(
        reply_markup=complete_kb(order_id)
    )

    await bot.send_message(order["client_id"], "🚖 Водій прибув")

    await callback.answer()


# ---------------- COMPLETE ----------------
@router.callback_query(F.data.startswith("complete_"))
async def complete_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await get_order(order_id)

    if callback.from_user.id != order["driver_id"]:
        await callback.answer("Не ваше", show_alert=True)
        return

    await update_order(order_id, "completed")

    await callback.message.edit_reply_markup()

    await bot.send_message(order["client_id"], "✅ Поїздку завершено")

    await callback.answer("Завершено")
