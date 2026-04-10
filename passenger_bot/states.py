from aiogram.fsm.state import State, StatesGroup


class OrderState(StatesGroup):
    phone = State()
    from_loc = State()
    to_loc = State()
    comment = State()
