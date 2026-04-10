from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити замовлення")],
            [KeyboardButton(text="Скасувати замовлення")]
        ],
        resize_keyboard=True
    )


def contact_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Надіслати номер", request_contact=True)]
        ],
        resize_keyboard=True
    )


def take_order_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Взяти замовлення", callback_data=f"take_{order_id}")]
        ]
    )


def arrived_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Прибув", callback_data=f"arrived_{order_id}")]
        ]
    )


def complete_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Завершити поїздку", callback_data=f"complete_{order_id}")]
        ]
    )
