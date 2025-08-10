import os
import asyncio
from aiogram.fsm.state import StatesGroup, State
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handler import start_handler, menu


class SupportStates(StatesGroup):
    waiting_for_message = State()
    admin_reply = State()


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token="8221393937:AAHB_leEIX4-WdJQzp_9Bpq0nhdocGLR7ps")
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_routers(
        start_handler.router,
        menu.router
    )

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
