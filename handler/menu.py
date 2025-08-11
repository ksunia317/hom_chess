import logging
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.types import FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import repository
from keyboard.main_menu import menu_keyboard, main_reply_keyboard
from datetime import datetime
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_repo = repository.UserRepository()


class SupportStates(StatesGroup):
    waiting_for_message = State()
    admin_reply = State()


class EditProfile(StatesGroup):
    choosing_field = State()
    input_new_value = State()


class CancelRecording(StatesGroup):
    confirming = State()


class Registration(StatesGroup):
    input_name = State()
    input_surname = State()
    input_phone = State()
    input_email = State()
    input_category = State()


class RecordingStates(StatesGroup):
    choosing_time = State()


class AdminStates(StatesGroup):
    waiting_for_broadcast = State()


router = Router()


@router.message(F.text.lower() == "меню")
async def show_menu(message: types.Message):
    await message.answer(
        "🎖️ Твой идеальный помощник в мире шахмат",
        reply_markup=menu_keyboard
    )


@router.callback_query(F.data == "support")
async def support_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Пожалуйста, опишите вашу проблему или вопрос. "
        "Мы постараемся ответить как можно быстрее.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(SupportStates.waiting_for_message)
    await callback.answer()


@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: types.Message, state: FSMContext, bot: Bot):
    support_message = message.text

    user_info = (
        f"👤 Пользователь: @{message.from_user.username or 'нет username'}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"📅 Дата: {message.date.strftime('%d-%m-%Y %H:%M')}\n\n"
        f"✉️ Сообщение:\n{support_message}"
    )

    ADMIN_ID = 6166075182

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📨 Новое сообщение в поддержку:\n\n{user_info}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Ответить пользователю",
                    callback_data=f"reply_to_{message.from_user.id}"
                )]
            ]))

        await message.answer(
            "Спасибо за ваше сообщение! Мы уже получили его и скоро ответим.\n\n"
            "Ваше обращение очень важно для нас.",
            reply_markup=main_reply_keyboard
        )
    except Exception as e:
        await message.answer(
            "Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.",
            reply_markup=main_reply_keyboard
        )
        logger.error(f"Ошибка отправки сообщения админу: {e}")

    await state.clear()


@router.callback_query(F.data.startswith("reply_to_"))
async def reply_to_user(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[-1])
    await callback.message.answer(f"Введите ответ для пользователя (ID: {user_id}):")
    await state.set_state(SupportStates.admin_reply)
    await state.update_data(user_id=user_id)


@router.message(SupportStates.admin_reply)
async def send_admin_reply(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get("user_id")

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"📩 Ответ от поддержки:\n\n{message.text}"
        )
        await message.answer("✅ Ответ отправлен пользователю")
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить ответ: {e}")
        logger.error(f"Ошибка отправки ответа пользователю: {e}")

    await state.clear()


@router.callback_query(F.data == "write")
async def write_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = user_repo.get_user_by_id(user_id)

    if not user:
        await callback.message.answer(
            "❌ Для записи на занятие необходимо сначала зарегистрироваться!",
            reply_markup=main_reply_keyboard
        )
        return
    if 'username' not in user or 'username_phone' not in user:
        await callback.message.answer(
            "❌ В вашем профиле отсутствуют необходимые данные!",
            reply_markup=main_reply_keyboard
        )
        return
    builder = InlineKeyboardBuilder()
    times = [
        "Пн 17:00-19:00",
        "Вт 16:00-18:00",
        "Ср 18:00-20:00",
        "Чт 16:00-18:00",
        "Пт 17:00-19:00",
        "Сб 10:00-12:00"
    ]

    for time in times:
        builder.button(text=time, callback_data=f"time_{time}")

    builder.adjust(2)

    await callback.message.answer(
        "🕒 Выберите удобное время для занятия:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RecordingStates.choosing_time)


@router.callback_query(F.data.startswith("time_"), RecordingStates.choosing_time)
async def process_time_selection(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    selected_time = callback.data.split("_")[1]
    user_id = callback.from_user.id
    user = user_repo.get_user_by_id(user_id)

    recording_data = {
        "user_id": user_id,
        "username": user["username"],
        "phone": user["username_phone"],
        "time": selected_time,
        "date": callback.message.date.strftime("%d-%m-%Y %H:%M")
    }

    if user_repo.add_recording(recording_data):
        builder = InlineKeyboardBuilder()
        builder.button(text="Отменить запись", callback_data="cancel_recording")
        builder.adjust(1)

        await callback.message.answer(
            f"✅ Вы успешно записаны на занятие!\n\n"
            f"📅 Время: {selected_time}\n"
            f"👤 Имя: {user['username']}\n"
            f"📱 Телефон: {user['username_phone']}\n\n"
            "Тренер свяжется с вами для подтверждения.",
            reply_markup=builder.as_markup()
        )

        await bot.send_message(
            6166075182,
            f"📝 Новая запись на занятие:\n\n"
            f"👤 Пользователь: {user['username']}\n"
            f"📱 Телефон: {user['username_phone']}\n"
            f"🕒 Время: {selected_time}\n"
            f"📅 Дата записи: {recording_data['date']}"
        )
    else:
        await callback.message.answer(
            "❌ Вы уже записаны на это время!",
            reply_markup=main_reply_keyboard
        )

    await state.clear()


@router.callback_query(F.data == "schedule")
async def show_schedule(callback: types.CallbackQuery):
    await callback.message.answer("""🎖️ Расписание занятий по шахматам 🎖️

✅ Занятия проходят ежедневно, кроме воскресенья:

| День |    Время    |
| ---- | ----------- |
|  Пн  | 17:00–19:00 |
|  Вт  | 16:00–18:00 |
|  Ср  | 18:00–20:00 |
|  Чт  | 16:00–18:00 |
|  Пт  | 17:00–19:00 |
|  Сб  | 10:00–12:00 |
🆚 Группы формируются по уровню подготовки:

- Новички: вторник и четверг в 16:00
- Продвинутые игроки: среда и пятница в 18:00
- Дети: суббота в 10:00

🛠 Индивидуальное обучение доступно по предварительной договоренности.

📍 Место проведения: г. Оренбург ул.Пролетарская д. 314, эт. №1

Присоединяйся к миру шахмат и покоряй вершины мастерства вместе с нами!""")


@router.callback_query(F.data == "trener")
async def show_trainer_info(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.answer_photo(
            photo=FSInputFile("images/photo.png"),
            caption=(
                "🌟 Шахматы — твоя дорога к успеху! 🌟\n\n"
                "Со мной — тренером Марией🔥 — ты откроешь секреты великих игроков прошлого и настоящего. "
                "Ты научишься правильно анализировать позицию, разрабатывать стратегии и добиваться результатов в каждой партии.\n\n"
                "✅ Играй осознанно и выигрывай уверенно!\n"
                "✅ Повышай рейтинг и участвуй в турнирах!\n"
                "✅ Создай собственную школу успеха на шахматной доске!\n\n"
                "Приходи на тренировочные сессии, стань частью нашей команды победителей!"
            )
        )
        await callback.answer()
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")
        await callback.answer()


@router.callback_query(F.data == "registrastion")
async def start_registration(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    existing_user = user_repo.get_user_by_id(user_id)

    if existing_user:
        builder = InlineKeyboardBuilder()
        builder.button(text="Редактировать профиль", callback_data="edit_profile")
        builder.adjust(1)

        await callback.message.answer(
            "❌ Вы уже зарегистрированы!\n\n"
            f"Ваши данные:\n"
            f"👤 Имя: {existing_user['username']}\n"
            f"📝 Фамилия: {existing_user['username_surname']}\n"
            f"📱 Телефон: {existing_user['username_phone']}\n"
            f"📧 Email: {existing_user['username_email']}\n"
            f"🏆 Уровень игры: {existing_user['username_category']}",
            reply_markup=builder.as_markup()
        )
        return

    await callback.message.answer("Введите имя")
    await state.set_state(Registration.input_name)


@router.message(Registration.input_name)
async def input_name(message: Message, state: FSMContext):
    name = message.text
    await state.update_data(username=name)
    await message.answer("Введите фамилию")
    await state.set_state(Registration.input_surname)


@router.message(Registration.input_surname)
async def input_surname(message: Message, state: FSMContext):
    surname = message.text
    await state.update_data(username_surname=surname)
    await message.answer("Введите телефон")
    await state.set_state(Registration.input_phone)


@router.message(Registration.input_phone)
async def input_phone(message: Message, state: FSMContext):
    phone = message.text
    await state.update_data(username_phone=phone)
    await message.answer("Введите почту")
    await state.set_state(Registration.input_email)


@router.message(Registration.input_email)
async def input_email(message: Message, state: FSMContext):
    email = message.text
    await state.update_data(username_email=email)
    await message.answer("Введите уровень игры")
    await state.set_state(Registration.input_category)


@router.message(Registration.input_category)
async def input_category(message: Message, state: FSMContext, bot: Bot):
    category = message.text
    await state.update_data(username_category=category)

    data = await state.get_data()
    user_data = {
        "user_id": message.from_user.id,
        "username": data.get("username", ""),
        "username_surname": data.get("username_surname", ""),
        "username_phone": data.get("username_phone", ""),
        "username_email": data.get("username_email", ""),
        "username_category": data.get("username_category", "")
    }

    if user_repo.add_user(user_data):
        ADMIN_ID = 6166075182
        registration_info = (
            "🆕 *Новый пользователь зарегистрирован!*\n\n"
            f"👤 *Имя:* {user_data['username']}\n"
            f"📝 *Фамилия:* {user_data['username_surname']}\n"
            f"📱 *Телефон:* {user_data['username_phone']}\n"
            f"📧 *Email:* {user_data['username_email']}\n"
            f"🏆 *Уровень игры:* {user_data['username_category']}\n"
            f"🆔 *ID:* {message.from_user.id}\n"
            f"📅 *Дата регистрации:* {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        )

        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=registration_info,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="💬 Написать пользователю",
                                url=f"tg://user?id={message.from_user.id}"
                            ),
                            InlineKeyboardButton(
                                text="📋 Профиль",
                                callback_data=f"admin_view_profile_{message.from_user.id}"
                            )
                        ]
                    ]
                )
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу: {e}")

        await message.answer(
            "✅ Регистрация успешно завершена!\n"
            f"👤 Имя: {user_data['username']}\n"
            f"📝 Фамилия: {user_data['username_surname']}\n"
            f"📱 Телефон: {user_data['username_phone']}\n"
            f"📧 Email: {user_data['username_email']}\n"
            f"🏆 Ранг: {user_data['username_category']}",
            reply_markup=main_reply_keyboard
        )
    else:
        await message.answer(
            "❌ Ошибка: вы уже зарегистрированы или произошла ошибка при сохранении!",
            reply_markup=main_reply_keyboard
        )

    await state.clear()


@router.callback_query(F.data == "edit_profile")
async def start_edit_profile(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = user_repo.get_user_by_id(user_id)

    if not user:
        await callback.message.answer(
            "❌ Вы еще не зарегистрированы!",
            reply_markup=main_reply_keyboard
        )
        return

    builder = InlineKeyboardBuilder()
    fields = [
        ("Имя", "name"),
        ("Фамилия", "surname"),
        ("Телефон", "phone"),
        ("Email", "email"),
        ("Уровень игры", "category")
    ]

    for text, field in fields:
        builder.button(text=text, callback_data=f"edit_{field}")

    builder.button(text="Отмена", callback_data="cancel_edit")
    builder.adjust(2)

    await callback.message.answer(
        "✏️ Выберите поле для редактирования:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(EditProfile.choosing_field)


@router.callback_query(F.data.startswith("edit_"), EditProfile.choosing_field)
async def select_field_to_edit(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    await state.update_data(field=field)

    field_names = {
        "name": "имя",
        "surname": "фамилию",
        "phone": "телефон",
        "email": "email",
        "category": "уровень игры"
    }

    await callback.message.answer(
        f"Введите новое значение для {field_names[field]}:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="cancel_edit")]
        ])
    )
    await state.set_state(EditProfile.input_new_value)


@router.message(EditProfile.input_new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    new_value = message.text
    user_id = message.from_user.id

    users = user_repo.get_all_users()
    user_found = False

    field_mapping = {
        "name": "username",
        "surname": "username_surname",
        "phone": "username_phone",
        "email": "username_email",
        "category": "username_category"
    }

    db_field = field_mapping[field]

    updated_users = []
    for user in users:
        if "user_id" in user and user["user_id"] == user_id:
            user[db_field] = new_value
            user_found = True
        updated_users.append(user)

    if user_found:
        user_repo._save_data(user_repo.users_file, updated_users)

        updated_user = next((u for u in updated_users if "user_id" in u and u["user_id"] == user_id), None)

        if updated_user:
            await message.answer(
                f"✅ Данные успешно обновлены!\n\n"
                f"👤 Имя: {updated_user.get('username', 'не указано')}\n"
                f"📝 Фамилия: {updated_user.get('username_surname', 'не указана')}\n"
                f"📱 Телефон: {updated_user.get('username_phone', 'не указан')}\n"
                f"📧 Email: {updated_user.get('username_email', 'не указан')}\n"
                f"🏆 Уровень игры: {updated_user.get('username_category', 'не указан')}",
                reply_markup=main_reply_keyboard
            )
        else:
            await message.answer(
                "✅ Данные обновлены, но не удалось получить информацию о пользователе.",
                reply_markup=main_reply_keyboard
            )
    else:
        await message.answer(
            "❌ Ошибка: пользователь не найден!",
            reply_markup=main_reply_keyboard
        )

    await state.clear()


@router.callback_query(F.data == "cancel_edit", EditProfile.choosing_field)
@router.callback_query(F.data == "cancel_edit", EditProfile.input_new_value)
async def cancel_edit_profile(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Редактирование профиля отменено.",
        reply_markup=main_reply_keyboard
    )
    await state.clear()


@router.callback_query(F.data == "cancel_recording")
async def show_user_recordings(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    recordings = user_repo.get_all_recordings()
    user_recordings = [r for r in recordings if r["user_id"] == user_id]

    if not user_recordings:
        await callback.message.answer(
            "❌ У вас нет активных записей на занятия.",
            reply_markup=main_reply_keyboard
        )
        return

    builder = InlineKeyboardBuilder()
    for recording in user_recordings:
        builder.button(
            text=f"❌ Отменить {recording['time']}",
            callback_data=f"confirm_cancel_{recording['time']}"
        )

    builder.button(text="Назад", callback_data="menu")
    builder.adjust(1)

    await callback.message.answer(
        "📝 Ваши активные записи:\n\n" +
        "\n".join([f"🕒 {r['time']}" for r in user_recordings]),
        reply_markup=builder.as_markup()
    )
    await state.set_state(CancelRecording.confirming)


@router.callback_query(F.data.startswith("confirm_cancel_"), CancelRecording.confirming)
async def confirm_cancel_recording(callback: types.CallbackQuery, state: FSMContext):
    time_to_cancel = callback.data.split("_")[2]
    user_id = callback.from_user.id

    builder = InlineKeyboardBuilder()
    builder.button(text="Да, отменить", callback_data=f"final_cancel_{time_to_cancel}")
    builder.button(text="Нет, оставить", callback_data="menu")
    builder.adjust(2)

    await callback.message.answer(
        f"Вы уверены, что хотите отменить запись на {time_to_cancel}?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("final_cancel_"))
async def process_cancel_recording(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    time_to_cancel = callback.data.split("_")[2]
    user_id = callback.from_user.id

    recordings = user_repo.get_all_recordings()
    updated_recordings = [r for r in recordings if not (r["user_id"] == user_id and r["time"] == time_to_cancel)]

    if len(updated_recordings) < len(recordings):
        user_repo._save_data(user_repo.recordings_file, updated_recordings)

        user = user_repo.get_user_by_id(user_id)
        if user:
            await bot.send_message(
                5042095324,
                f"❌ Запись отменена:\n\n"
                f"👤 Пользователь: {user['username']}\n"
                f"📱 Телефон: {user['username_phone']}\n"
                f"🕒 Время: {time_to_cancel}\n"
                f"📅 Дата отмены: {callback.message.date.strftime('%d-%m-%Y %H:%M')}"
            )

        await callback.message.answer(
            f"✅ Запись на {time_to_cancel} успешно отменена.",
            reply_markup=main_reply_keyboard
        )
    else:
        await callback.message.answer(
            "❌ Не удалось найти запись для отмены.",
            reply_markup=main_reply_keyboard
        )

    await state.clear()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != 6166075182:
        await callback.answer("Доступ запрещён")
        return

    await callback.message.answer(
        "📢 Введите сообщение для рассылки:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
            ]
        )
    )
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()


@router.message(Command("broadcast"))
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != 6166075182:
        await message.answer("Эта команда доступна только администратору.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Да, продолжить", callback_data="confirm_broadcast")
    builder.button(text="Отмена", callback_data="cancel_broadcast")
    builder.adjust(2)

    await message.answer(
        "⚠️ Вы собираетесь сделать рассылку всем пользователям. Продолжить?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите сообщение для рассылки всем пользователям:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Рассылка отменена.")
    await state.clear()
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast)
async def process_admin_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    users = user_repo.get_all_users()
    if not users:
        await message.answer("❌ Нет пользователей для рассылки")
        await state.clear()
        return

    success = 0
    failed = 0

    progress_msg = await message.answer("🔄 Начинаю рассылку...")

    for user in users:
        try:
            await bot.send_message(
                chat_id=user['user_id'],
                text=message.html_text if message.html_text else message.text,
                parse_mode="HTML" if message.html_text else None
            )
            success += 1
            if success % 10 == 0:
                await progress_msg.edit_text(f"⏳ Отправлено: {success}/{len(users)}")
            await asyncio.sleep(0.1)
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка отправки пользователю {user.get('user_id')}: {e}")
    user_repo.add_broadcast({
        "text": message.text,
        "date": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "success": success,
        "failed": failed
    })

    await progress_msg.delete()
    await message.answer(
        f"✅ Рассылка завершена:\n\n"
        f"▪️ Успешно: {success}\n"
        f"▪️ Не удалось: {failed}\n"
        f"▪️ Всего пользователей: {len(users)}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В меню админа", callback_data="admin_back")]
            ]
        )
    )
    await state.clear()


@router.callback_query(F.data == "my_profile")
async def show_my_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = user_repo.get_user_by_id(user_id)

    if not user:
        await callback.message.answer(
            "❌ Вы еще не зарегистрированы!",
            reply_markup=main_reply_keyboard
        )
        return

    profile_text = (
        "👤 Ваш профиль:\n\n"
        f"🏷️ Имя: {user.get('username', 'не указано')}\n"
        f"📝 Фамилия: {user.get('username_surname', 'не указана')}\n"
        f"📱 Телефон: {user.get('username_phone', 'не указан')}\n"
        f"📧 Email: {user.get('username_email', 'не указан')}\n"
        f"🏆 Уровень игры: {user.get('username_category', 'не указан')}\n"
        f"📅 Дата регистрации: {user.get('registration_date', 'неизвестно')}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать профиль", callback_data="edit_profile")
    builder.button(text="⬅️ Назад", callback_data="menu")
    builder.adjust(1)

    await callback.message.answer(
        profile_text,
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "my_recordings")
async def show_my_recordings(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    recordings = user_repo.get_user_recordings(user_id)

    if not recordings:
        await callback.message.answer(
            "❌ У вас нет активных записей на занятия.",
            reply_markup=main_reply_keyboard
        )
        return

    recordings_text = "📅 Ваши записи на занятия:\n\n"
    for i, rec in enumerate(recordings, 1):
        recordings_text += (
            f"{i}. 🕒 {rec.get('time', 'неизвестно')}\n"
            f"   📅 Дата записи: {rec.get('date', 'неизвестно')}\n\n"
        )

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить запись", callback_data="cancel_recording")
    builder.button(text="⬅️ Назад", callback_data="menu")
    builder.adjust(1)

    await callback.message.answer(
        recordings_text,
        reply_markup=builder.as_markup()
    )


@router.message(Registration.input_category)
async def input_category(message: Message, state: FSMContext, bot: Bot):
    category = message.text
    await state.update_data(username_category=category)

    data = await state.get_data()
    user_data = {
        "user_id": message.from_user.id,
        "username": data.get("username", ""),
        "username_surname": data.get("username_surname", ""),
        "username_phone": data.get("username_phone", ""),
        "username_email": data.get("username_email", ""),
        "username_category": data.get("username_category", "")
    }

    if user_repo.add_user(user_data):
        ADMIN_ID = 6166075182
        registration_info = (
            "🆕 *Новый пользователь зарегистрирован!*\n\n"
            f"👤 *Имя:* {user_data['username']}\n"
            f"📝 *Фамилия:* {user_data['username_surname']}\n"
            f"📱 *Телефон:* {user_data['username_phone']}\n"
            f"📧 *Email:* {user_data['username_email']}\n"
            f"🏆 *Уровень игры:* {user_data['username_category']}\n"
            f"🆔 *ID:* {message.from_user.id}\n"
            f"📅 *Дата регистрации:* {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        )

        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=registration_info,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу: {e}")

        await message.answer(
            "✅ Регистрация успешно завершена!\n"
            f"👤 Имя: {user_data['username']}\n"
            f"📝 Фамилия: {user_data['username_surname']}\n"
            f"📱 Телефон: {user_data['username_phone']}\n"
            f"📧 Email: {user_data['username_email']}\n"
            f"🏆 Уровень игры: {user_data['username_category']}",
            reply_markup=main_reply_keyboard
        )
    else:
        await message.answer(
            "❌ Ошибка: вы уже зарегистрированы или произошла ошибка при сохранении!",
            reply_markup=main_reply_keyboard
        )

    await state.clear()


@router.callback_query(F.data.startswith("admin_view_profile_"))
async def admin_view_profile(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    user = user_repo.get_user_by_id(user_id)

    if not user:
        await callback.answer("Пользователь не найден")
        return

    profile_text = (
        "👤 *Профиль пользователя*\n\n"
        f"🆔 ID: {user_id}\n"
        f"🏷️ Имя: {user.get('username', 'не указано')}\n"
        f"📝 Фамилия: {user.get('username_surname', 'не указана')}\n"
        f"📱 Телефон: {user.get('username_phone', 'не указан')}\n"
        f"📧 Email: {user.get('username_email', 'не указан')}\n"
        f"🏆 Уровень игры: {user.get('username_category', 'не указан')}\n"
        f"📅 Дата регистрации: {user.get('registration_date', 'неизвестно')}"
    )

    await callback.message.edit_text(
        text=profile_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Написать",
                        url=f"tg://user?id={user_id}"
                    ),
                    InlineKeyboardButton(
                        text="📅 Записи",
                        callback_data=f"admin_view_recordings_{user_id}"
                    )
                ]
            ]
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_recordings_"))
async def admin_view_recordings(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    recordings = user_repo.get_user_recordings(user_id)

    if not recordings:
        await callback.answer("У пользователя нет записей")
        return

    recordings_text = "📅 *Записи пользователя*\n\n"
    for i, rec in enumerate(recordings, 1):
        recordings_text += (
            f"{i}. 🕒 {rec.get('time', 'неизвестно')}\n"
            f"   📅 Дата записи: {rec.get('date', 'неизвестно')}\n\n"
        )

    await callback.message.edit_text(
        text=recordings_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data=f"admin_view_profile_{user_id}"
                    )
                ]
            ]
        )
    )
    await callback.answer()


@router.message(Command("admin"))
async def admin_menu(message: types.Message):
    if message.from_user.id != 6166075182:
        return

    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Все записи", callback_data="admin_all_recordings")],
            [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_all_users")],
            [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")]
        ]
    )

    await message.answer("Панель администратора:", reply_markup=admin_kb)


@router.callback_query(F.data == "admin_all_recordings")
async def show_all_recordings(callback: types.CallbackQuery):
    if callback.from_user.id != 6166075182:
        await callback.answer("Доступ запрещен")
        return

    recordings = user_repo.get_all_recordings()

    if not recordings:
        await callback.message.answer("Нет активных записей")
        return
    recordings_by_time = {}
    for rec in recordings:
        time_slot = rec.get('time', 'Не указано')
        if time_slot not in recordings_by_time:
            recordings_by_time[time_slot] = []
        recordings_by_time[time_slot].append(rec)
    message_text = "📋 Все записи на занятия:\n\n"
    for time_slot, records in recordings_by_time.items():
        message_text += f"🕒 {time_slot}:\n"
        for i, rec in enumerate(records, 1):
            user = user_repo.get_user_by_id(rec['user_id'])
            username = user.get('username', 'Неизвестно') if user else 'Неизвестно'
            message_text += f"{i}. {username} (ID: {rec['user_id']})\n"
        message_text += "\n"

    await callback.message.answer(
        message_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_all_recordings")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
            ]
        )
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    if callback.from_user.id != 6166075182:
        await callback.answer("Доступ запрещен")
        return

    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Все записи", callback_data="admin_all_recordings")],
            [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_all_users")],
            [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")]
        ]
    )

    await callback.message.edit_text(
        "Панель администратора:",
        reply_markup=admin_kb
    )
    await callback.answer()


@router.callback_query(F.data == "admin_all_users")
async def show_all_users(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id != 6166075182:
        await callback.answer("Доступ запрещен")
        return

    users = user_repo.get_all_users()

    if not users:
        await callback.message.answer("Нет зарегистрированных пользователей")
        return

    message_text = "👥 Все пользователи:\n\n"
    for i, user in enumerate(users, 1):
        try:
            tg_user = await bot.get_chat(user['user_id'])
            username = f"@{tg_user.username}" if tg_user.username else "нет username"
        except Exception as e:
            username = "недоступен"
            logger.error(f"Ошибка получения username для {user['user_id']}: {e}")

        reg_date = user.get('registration_date', 'неизвестно')
        message_text += (
            f"{i}. {user.get('username', 'Неизвестно')} "
            f"{user.get('username_surname', '')}\n"
            f"   👤 {username} "
            f"📱 {user.get('username_phone', 'Не указан')} "
            f"🆔 {user.get('user_id', 'N/A')}\n"
            f"   📅 {reg_date}\n\n"
        )

    await callback.message.answer(
        message_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_all_users")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
            ]
        )
    )
    await callback.answer()
