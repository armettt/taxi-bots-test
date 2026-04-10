import time
from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from .states import OrderState
from .keyboards import main_menu, contact_kb, take_order_kb, arrived_kb, complete_kb
from .db import get_user, save_user, create_order, get_order, update_order_status, delete_order
from .config import GROUP_ID
from shared.database import fetchrow
from aiogram import Bot

user_last_order_time = {}
user_active_order = {}
CALLBACK_COOLDOWN = {}

async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Використовуй кнопки нижче", reply_markup=main_menu())

async def start_order(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user:
        await state.update_data(phone=user["phone"])
        await message.answer("Звідки їхати?")
        await state.set_state(OrderState.from_loc)
    else:
        await message.answer("Надішли номер телефону", reply_markup=contact_kb())
        await state.set_state(OrderState.phone)

async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await save_user(message.from_user.id, phone)
    await state.update_data(phone=phone)
    await message.answer("Звідки їхати?")
    await state.set_state(OrderState.from_loc)

async def get_from(message: Message, state: FSMContext):
    await state.update_data(from_loc=message.text)
    await message.answer("Куди їхати?")
    await state.set_state(OrderState.to_loc)

async def get_to(message: Message, state: FSMContext):
    await state.update_data(to_loc=message.text)
    await message.answer("Коментар (або '-'):")
    await state.set_state(OrderState.comment)

async def create_order_handler(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    now = time.time()
    if user_id in user_last_order_time and now - user_last_order_time[user_id] < 30:
        await message.answer("Зачекай трохи", reply_markup=main_menu())
        return
    if user_active_order.get(user_id):
        await message.answer("У тебе вже є замовлення", reply_markup=main_menu())
        return
    data = await state.get_data()
    username = message.from_user.username
    name = f"@{username}" if username else message.from_user.first_name
    order_id = await create_order({
        "client_id": user_id,
        "phone": data["phone"],
        "username": name,
        "from_loc": data["from_loc"],
        "to_loc": data["to_loc"],
        "comment": message.text
    })
    phone_link = f"<a href='tel:{data['phone']}'>{data['phone']}</a>"
    text = (
        f"🚕 <b>Замовлення #{order_id}</b>\n\n"
        f"📞 Телефон клієнта: {phone_link}\n"
        f"👤 Клієнт: {name}\n"
        f"📍 Маршрут: {data['from_loc']} → {data['to_loc']}\n"
        f"💬 Коментар: {message.text}"
    )
    sent = await bot.send_message(GROUP_ID, text, reply_markup=take_order_kb(order_id), parse_mode="HTML")
    await update_order_status(order_id, "waiting", message_id=sent.message_id)
    user_last_order_time[user_id] = now
    user_active_order[user_id] = order_id
    await message.answer("Замовлення створено", reply_markup=main_menu())
    await state.clear()
