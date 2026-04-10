from aiogram.fsm.state import State, StatesGroup


class Register(StatesGroup):
    phone = State()
    brand = State()
    model = State()
    color = State()
    plate = State()
