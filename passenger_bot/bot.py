import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from passenger_bot.config import BOT_TOKEN
from passenger_bot.handlers import router
from shared.database import init_db
from shared.middleware import LoggingMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)


async def main():
    # Инициализация базы данных
    await init_db()

    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    # Инициализация диспетчера
    dp = Dispatcher(storage=MemoryStorage())

    # Подключение middleware
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # Подключение роутеров
    dp.include_router(router)

    logging.info("Passenger bot started successfully ✅")

    # Запуск polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
