import os
import asyncio
import random
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Загружаем токен из .env файла
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для регистрации
class RegistrationState(StatesGroup):
    first_name = State()
    last_name = State()
    group = State()

# Состояния для заявок
class BookingState(StatesGroup):
    purpose = State()
    date = State()
    time = State()

# Словарь для хранения данных пользователей
users_data = {}
user_ratings = {}
user_challenges = {}  # Для отслеживания выполнения челленджей

# Текущая загруженность коворкинга (демо данные)
coworking_status = {
    "total_seats": 50,
    "occupied_seats": 23,
    "last_updated": datetime.now().strftime("%H:%M")
}

# Фейковые пользователи для демонстрации рейтинга
fake_users = [
    {"name": "Алексей Иванов", "group": "БИВТ-25-15", "rating": 150, "level": 3},
    {"name": "Мария Петрова", "group": "БИВТ-25-16", "rating": 120, "level": 3},
    {"name": "Дмитрий Сидоров", "group": "БИВТ-25-14", "rating": 95, "level": 2},
    {"name": "Екатерина Волкова", "group": "БИВТ-25-17", "rating": 80, "level": 2},
    {"name": "Иван Козлов", "group": "БИВТ-25-15", "rating": 65, "level": 2},
    {"name": "Ольга Новикова", "group": "БИВТ-25-16", "rating": 45, "level": 1},
    {"name": "Павел Морозов", "group": "БИВТ-25-14", "rating": 30, "level": 1},
    {"name": "Анна Соколова", "group": "БИВТ-25-17", "rating": 25, "level": 1},
    {"name": "Сергей Орлов", "group": "БИВТ-25-15", "rating": 15, "level": 1},
    {"name": "Наталья Лебедева", "group": "БИВТ-25-16", "rating": 5, "level": 1}
]

# Еженедельные челленджи
weekly_challenges = [
    {
        "id": 1,
        "title": "Ранняя пташка 🐦",
        "description": "Приди в коворкинг до 10 утра 3 раза за неделю",
        "reward": 20,
        "progress": 0,
        "target": 3
    },
    {
        "id": 2,
        "title": "Активный участник ⚡",
        "description": "Посети коворкинг 5 раз за неделю",
        "reward": 30,
        "progress": 0,
        "target": 5
    },
    {
        "id": 3,
        "title": "Помощник сообщества 🤝",
        "description": "Сделай 2 доната за неделю",
        "reward": 25,
        "progress": 0,
        "target": 2
    },
    {
        "id": 4,
        "title": "Социальный активист 🌟",
        "description": "Предложи 3 идеи для улучшения коворкинга",
        "reward": 15,
        "progress": 0,
        "target": 3
    }
]

# Создаем главное меню
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⭐ Мой рейтинг"), KeyboardButton(text="🏆 Топ рейтинг")],
            [KeyboardButton(text="❤️ Донат"), KeyboardButton(text="🎯 Челленджи")],
            [KeyboardButton(text="📊 Загруженность"), KeyboardButton(text="📅 Бронирование")],
            [KeyboardButton(text="📱 Мой QR-код"), KeyboardButton(text="🚨 Сообщить о проблеме")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id in users_data:
        await message.answer(
            f"С возвращением, {users_data[user_id]['first_name']}! 🎉",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "Привет! Добро пожаловать в наше коворкинг-сообщество! 🚀\n"
            "Давай зарегистрируем тебя. Напиши своё имя"
        )
        await state.set_state(RegistrationState.first_name)

# Обработка имени
@dp.message(RegistrationState.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Отлично! Теперь введи свою фамилию:")
    await state.set_state(RegistrationState.last_name)

# Обработка фамилии
@dp.message(RegistrationState.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Отлично! Теперь введи свою группу по примеру: БИВТ-25-15")
    await state.set_state(RegistrationState.group)

# Обработка группы и завершение регистрации
@dp.message(RegistrationState.group)
async def process_group(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    # Сохраняем данные пользователя
    users_data[user_id] = {
        'first_name': user_data['first_name'],
        'last_name': user_data['last_name'],
        'group': message.text,
        'username': message.from_user.username
    }
    
    # Инициализируем рейтинг и челленджи
    user_ratings[user_id] = 0
    user_challenges[user_id] = weekly_challenges.copy()
    
    await message.answer(
        f"Спасибо за регистрацию, {user_data['first_name']}! 🎉\n"
        "Рады видеть тебя в нашем сообществе!",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

# Кнопка "Мой рейтинг"
@dp.message(lambda message: message.text == "⭐ Мой рейтинг")
async def show_my_rating(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    
    rating = user_ratings.get(user_id, 0)
    
    # Определяем уровень и звание
    if rating < 50:
        level = 1
        rank = "Новичок 🐣"
    elif rating < 100:
        level = 2
        rank = "Активный участник ⚡"
    elif rating < 200:
        level = 3
        rank = "Лидер сообщества 🏆"
    else:
        level = 4
        rank = "Легенда коворкинга 🌟"
    
    await message.answer(
        f"📊 <b>Твой рейтинг:</b>\n"
        f"• Баллы: {rating} ⭐\n"
        f"• Уровень: {level}\n"
        f"• Звание: {rank}\n\n"
        f"<i>Продолжай в том же духе! 💪</i>",
        parse_mode='HTML'
    )

# Кнопка "Топ рейтинг"
@dp.message(lambda message: message.text == "🏆 Топ рейтинг")
async def show_top_rating(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    
    # Сортируем фейковых пользователей по рейтингу
    sorted_users = sorted(fake_users, key=lambda x: x['rating'], reverse=True)
    
    # Формируем сообщение с топом
    top_message = "🏆 <b>Топ 10 участников коворкинга:</b>\n\n"
    
    for i, user in enumerate(sorted_users[:10], 1):
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        
        top_message += f"{medal}{i}. {user['name']} ({user['group']})\n"
        top_message += f"   ⭐ {user['rating']} баллов | Уровень {user['level']}\n\n"
    
    top_message += "<i>Зарабатывай баллы за посещения, донаты и активность!</i>"
    
    await message.answer(top_message, parse_mode='HTML')

# Кнопка "Челленджи"
@dp.message(lambda message: message.text == "🎯 Челленджи")
async def show_challenges(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    
    challenges = user_challenges.get(user_id, weekly_challenges.copy())
    
    challenges_message = "🎯 <b>Еженедельные челленджи:</b>\n\n"
    
    for challenge in challenges:
        progress_bar = "🟢" * challenge['progress'] + "⚪" * (challenge['target'] - challenge['progress'])
        challenges_message += f"<b>{challenge['title']}</b>\n"
        challenges_message += f"{challenge['description']}\n"
        challenges_message += f"Прогресс: {progress_bar} ({challenge['progress']}/{challenge['target']})\n"
        challenges_message += f"Награда: {challenge['reward']} ⭐\n\n"
    
    challenges_message += "<i>Выполняй челленджи и получай бонусные баллы!</i>"
    
    await message.answer(challenges_message, parse_mode='HTML')

# Кнопка "Загруженность"
@dp.message(lambda message: message.text == "📊 Загруженность")
async def show_occupancy(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    
    free_seats = coworking_status["total_seats"] - coworking_status["occupied_seats"]
    occupancy_percentage = (coworing_status["occupied_seats"] / coworking_status["total_seats"]) * 100
    
    if occupancy_percentage < 30:
        status_emoji = "🟢"
        status_text = "Свободно"
    elif occupancy_percentage < 70:
        status_emoji = "🟡"
        status_text = "Средняя загрузка"
    else:
        status_emoji = "🔴"
        status_text = "Многолюдно"
    
    occupancy_message = (
        f"📊 <b>Загруженность коворкинга:</b>\n\n"
        f"{status_emoji} <b>Статус:</b> {status_text}\n"
        f"👥 <b>Людей:</b> {coworking_status['occupied_seats']}/{coworking_status['total_seats']}\n"
        f"🪑 <b>Свободных мест:</b> {free_seats}\n"
        f"⏰ <b>Обновлено:</b> {coworking_status['last_updated']}\n\n"
        f"<i>Приходи в удобное время! 🕐</i>"
    )
    
    await message.answer(occupancy_message, parse_mode='HTML')

# Кнопка "Бронирование"
@dp.message(lambda message: message.text == "📅 Бронирование")
async def start_booking(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    
    await message.answer(
        "📅 <b>Бронирование аудитории:</b>\n\n"
        "Для какой цели ты хочешь забронировать аудиторию?\n"
        "Например: собрание команды, мероприятие, учеба и т.д.",
        parse_mode='HTML'
    )
    await state.set_state(BookingState.purpose)

# Обработка цели бронирования
@dp.message(BookingState.purpose)
async def process_booking_purpose(message: types.Message, state: FSMContext):
    await state.update_data(purpose=message.text)
    await message.answer(
        "📆 На какую дату нужна аудитория?\n"
        "Укажи в формате ДД.ММ.ГГГГ (например: 15.12.2024)"
    )
    await state.set_state(BookingState.date)

# Обработка даты бронирования
@dp.message(BookingState.date)
async def process_booking_date(message: types.Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.answer(
        "⏰ На какое время?\n"
        "Укажи в формате ЧЧ:ММ (например: 14:30)"
    )
    await state.set_state(BookingState.time)

# Обработка времени и завершение бронирования
@dp.message(BookingState.time)
async def process_booking_time(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    booking_info = (
        f"✅ <b>Заявка на бронирование создана!</b>\n\n"
        f"<b>Цель:</b> {user_data['purpose']}\n"
        f"<b>Дата:</b> {user_data['date']}\n"
        f"<b>Время:</b> {message.text}\n"
        f"<b>Имя:</b> {users_data[user_id]['first_name']} {users_data[user_id]['last_name']}\n\n"
        f"<i>Мы свяжемся с тобой для подтверждения бронирования! 📞</i>"
    )
    
    await message.answer(booking_info, parse_mode='HTML')
    await state.clear()

# Кнопка "Донат"
@dp.message(lambda message: message.text == "❤️ Донат")
async def donate_handler(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    
    await message.answer(
        "🙏 <b>Поддержка коворкинга:</b>\n\n"
        "Ты можешь помочь нашему сообществу!\n"
        "Отправь фото:\n"
        "• Чека за донат\n"
        "• Еды или напитков\n"
        "• Полезных вещей\n\n"
        "<i>За каждый донат ты получаешь баллы рейтинга!</i>",
        parse_mode='HTML'
    )

# Обработка фото доната
@dp.message(lambda message: message.photo)
async def process_donation_photo(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    
    # Добавляем 10 баллов за донат
    user_ratings[user_id] = user_ratings.get(user_id, 0) + 10
    
    await message.answer(
        "✅ <b>Спасибо за донат!</b>\n\n"
        "Мы проверим твое фото и начислим баллы.\n"
        f"Твой текущий рейтинг: <b>{user_ratings[user_id]} ⭐</b>\n\n"
        "<i>Ты делаешь наш коворкинг лучше! 💫</i>",
        parse_mode='HTML'
    )

# Кнопка "Сообщить о проблеме"
@dp.message(lambda message: message.text == "🚨 Сообщить о проблеме")
async def report_problem(message: types.Message):
    await message.answer(
        "🛠️ <b>Сообщи о проблеме:</b>\n\n"
        "Опиши, что случилось:\n"
        "• Что не работает?\n"
        "• Где находится?\n"
        "• Насколько это срочно?\n\n"
        "<i>Мы постараемся решить проблему как можно скорее!</i>",
        parse_mode='HTML'
    )

# Обработка текстовых сообщений (проблемы/запросы)
@dp.message(lambda message: message.text and message.text not in ["⭐ Мой рейтинг", "🏆 Топ рейтинг", "❤️ Донат", "🚨 Сообщить о проблеме"])
async def process_problem_report(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in users_data:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    
    await message.answer(
        "✅ <b>Сообщение получено!</b>\n\n"
        "Спасибо за обращение! Мы уже работаем над твоим запросом.\n"
        "<i>Скоро с тобой свяжутся для уточнения деталей.</i>",
        parse_mode='HTML'
    )

# Запуск бота
async def main():
    print("Бот запущен! 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
