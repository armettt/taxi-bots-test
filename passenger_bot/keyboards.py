from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Створити замовлення")],
            [KeyboardButton("Скасувати замовлення")]
        ],
        resize_keyboard=True
    )

def contact_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("Надіслати номер", request_contact=True)]],
        resize_keyboard=True
    )

def take_order_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("Взяти замовлення", callback_data=f"take_{order_id}")]]
    )

def arrived_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("Прибув", callback_data=f"arrived_{order_id}")]]
    )

def complete_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("Завершити поїздку", callback_data=f"complete_{order_id}")]]
    )
