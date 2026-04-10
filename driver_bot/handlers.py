from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from .states import Register
from .keyboards import phone_kb, main_kb
from .db import get_driver, save_driver
from .config import GROUP_ID

router = Router()


@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    driver = await get_driver(message.from_user.id)
    if driver:
        await message.answer("Ви вже зареєстровані!", reply_markup=main_kb())
    else:
        await message.answer(
            "Надішліть номер телефону",
            reply_markup=phone_kb()
        )
        await state.set_state(Register.phone)


@router.message(F.text == "✏️ Изменить данные")
async def edit_driver(message: Message, state: FSMContext):
    await message.answer("Надішліть номер телефону", reply_markup=phone_kb())
    await state.set_state(Register.phone)


@router.message(Register.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("Марка авто:")
    await state.set_state(Register.brand)


@router.message(Register.brand)
async def get_brand(message: Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await message.answer("Модель авто:")
    await state.set_state(Register.model)


@router.message(Register.model)
async def get_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text)
    await message.answer("Колір авто:")
    await state.set_state(Register.color)


@router.message(Register.color)
async def get_color(message: Message, state: FSMContext):
    await state.update_data(color=message.text)
    await message.answer("Номер авто:")
    await state.set_state(Register.plate)


@router.message(Register.plate)
async def finish_registration(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    user = message.from_user

    await save_driver(
        user.id,
        user.username,
        data["phone"],
        data["brand"],
        data["model"],
        data["color"],
        message.text
    )

    text = (
        "🚕 <b>Новий водій</b>\n"
        f"👤 @{user.username}\n"
        f"📱 {data['phone']}\n"
        f"🚗 {data['brand']} {data['model']}\n"
        f"🎨 {data['color']}\n"
        f"🔢 {message.text}"
    )

    await bot.send_message(GROUP_ID, text, parse_mode="HTML")
    await message.answer("✅ Реєстрація завершена!", reply_markup=main_kb())
    await state.clear()
