from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# ---------------- MAIN MENU ----------------
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити замовлення")],
            [KeyboardButton(text="Скасувати замовлення")]
        ],
        resize_keyboard=True
    )


# ---------------- CONTACT ----------------
def contact_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Надіслати номер", request_contact=True)]
        ],
        resize_keyboard=True
    )


# ---------------- DRIVER TAKE ORDER ----------------
def take_order_kb(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для водителей — только принятие заказа."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚕 Взяти замовлення",
                    callback_data=f"take_{order_id}"
                )
            ]
        ]
    )


# ---------------- ARRIVED ----------------
def arrived_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Прибув",
                    callback_data=f"arrived_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати замовлення",
                    callback_data=f"cancel_{order_id}"
                )
            ]
        ]
    )


# ---------------- COMPLETE ----------------
def complete_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Завершити поїздку",
                    callback_data=f"complete_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати замовлення",
                    callback_data=f"cancel_{order_id}"
                )
            ]
        ]
    )
