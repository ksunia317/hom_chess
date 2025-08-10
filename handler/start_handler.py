from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, \
    KeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.media_group import MediaGroupBuilder
import asyncio
import logging
from keyboard.main_menu import menu_keyboard, main_reply_keyboard

router = Router()


@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        """🤩Занятия по шахматам ждут тебя!  🏆

✅Улучшение стратегического мышления
✅Развитие памяти и концентрации внимания
✅Общение с единомышленниками

♟️Запишись прямо сейчас!""",
        reply_markup=main_reply_keyboard
    )


@router.message(Command("menu"))
async def menu(message: types.Message):
    await message.answer(
        "🎖️ Твой идеальный помощник в мире шахмат",
        reply_markup=menu_keyboard
    )
