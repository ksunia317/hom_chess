from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Регистрация", callback_data="registrastion"),
         InlineKeyboardButton(text="📝 Записаться", callback_data="write")],
        [InlineKeyboardButton(text="📅 Мои записи", callback_data="my_recordings"),
         InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton(text="🕒 Расписание", callback_data="schedule"),
         InlineKeyboardButton(text="👨‍🏫 Тренер", callback_data="trener")],
        [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")],
    ]
)

main_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Меню")]
    ],
    resize_keyboard=True
)
