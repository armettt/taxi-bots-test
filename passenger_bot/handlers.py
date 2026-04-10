import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .states import OrderState
from .keyboards import main_menu, contact_kb, take_order_kb, arrived_kb, complete_kb, cancel_kb
from .db import get_user, save_user, create_order, update_order, get_order, get_driver
from .config import GROUP_ID

router = Router()

user_last_order_time = {}
user_active_order = {}


# ---------------- START ----------------
@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Головне меню", reply_markup=main_menu())


# ---------------- CREATE ORDER ----------------
@router.message(F.text == "Створити замовлення")
async def create_order_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)

    if user:
        await state.update_data(phone=user["phone"])
        await message.answer("Введіть адресу відправлення")
        await state.set_state(OrderState.from_loc)
    else:
        await message.answer("Надішліть номер телефону", reply_markup=contact_kb())
        await state.set_state(OrderState.phone)


# ---------------- PHONE ----------------
@router.message(OrderState.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number

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
        await message.answer("Потрібно зачекати 30 секунд")
        return

    if user_id in user_active_order:
        await message.answer("У вас вже є активне замовлення")
        return

    data = await state.get_data()
    phone = data["phone"]

    order_id = await create_order(
        user_id,
        phone,
        message.from_user.username or message.from_user.first_name,
        data["from_loc"],
        data["to_loc"],
        message.text
    )

    phone_html = f'<a href="tel:{phone}">{phone}</a>'

    text = (
        f"Замовлення #{order_id}\n"
        f"Телефон: {phone_html}\n"
        f"Від: {data['from_loc']}\n"
        f"До: {data['to_loc']}\n"
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

    await message.answer("Замовлення створено")
    await state.clear()


# ---------------- TAKE ORDER ----------------
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

    text = callback.message.text + "\n\nСтатус: прийнято водієм"

    await callback.message.edit_text(
        text,
        reply_markup=arrived_kb(order_id),
        parse_mode="HTML"
    )

    await bot.send_message(
        order["client_id"],
        "Ваше замовлення прийнято водієм"
    )

    await callback.answer("Прийнято")


# ---------------- CANCEL ORDER ----------------
@router.callback_query(F.data.startswith("cancel_"))
async def cancel_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await get_order(order_id)

    user_id = callback.from_user.id

    # клиент может отменить свой заказ
    if order["client_id"] != user_id and order["driver_id"] != user_id:
        await callback.answer("Немає доступу", show_alert=True)
        return

    await update_order(order_id, "cancelled")

    await callback.message.edit_text(
        callback.message.text + "\n\nСтатус: скасовано",
        parse_mode="HTML"
    )

    await bot.send_message(order["client_id"], "Замовлення скасовано")
    await callback.answer("Скасовано")


# ---------------- ARRIVED ----------------
@router.callback_query(F.data.startswith("arrived_"))
async def arrived_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await get_order(order_id)

    if callback.from_user.id != order["driver_id"]:
        await callback.answer("Не ваше замовлення", show_alert=True)
        return

    await update_order(order_id, "arrived")

    await callback.message.edit_reply_markup(reply_markup=complete_kb(order_id))

    await bot.send_message(order["client_id"], "Водій прибув")

    await callback.answer("Готово")


# ---------------- COMPLETE ----------------
@router.callback_query(F.data.startswith("complete_"))
async def complete_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    order = await get_order(order_id)

    if callback.from_user.id != order["driver_id"]:
        await callback.answer("Не ваше замовлення", show_alert=True)
        return

    await update_order(order_id, "completed")

    await callback.message.edit_reply_markup()

    await bot.send_message(order["client_id"], "Поїздку завершено")

    await callback.answer("Завершено")
