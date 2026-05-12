import asyncio
import httpx
from datetime import datetime
import os

# ========== НАСТРОЙКА ==========
# ВСТАВЬ СВОИ ТОКЕНЫ СЮДА:
BOT_TOKEN = "8628470329:AAGNu__7pUBGbxo5UoRehztxrxHqsNrayFM"
WEATHER_API_KEY = "3a678ada131c76b2d68e764b1a4301c4"
# ===============================

# URL для API Telegram
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Хранилище состояний пользователей (чтобы бот не забывал, что спросил)
user_states = {}


async def send_message(chat_id, text, reply_markup=None):
    """Отправляет сообщение в Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)


async def send_typing(chat_id):
    """Показывает, что бот печатает"""
    url = f"{TELEGRAM_API}/sendChatAction"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "action": "typing"})


def get_weather_keyboard():
    """Клавиатура с одной кнопкой"""
    return {
        "keyboard": [[{"text": "🌤 Узнать погоду"}]],
        "resize_keyboard": True
    }


def get_back_keyboard():
    """Клавиатура с кнопкой назад"""
    return {
        "keyboard": [[{"text": "🔙 Назад"}]],
        "resize_keyboard": True
    }


def get_weather_emoji(description: str) -> str:
    """Выбирает эмодзи по описанию погоды"""
    desc = description.lower()
    if 'ясно' in desc or 'солнеч' in desc or 'sun' in desc:
        return '☀️'
    elif 'облач' in desc or 'пасмур' in desc or 'cloud' in desc:
        return '☁️'
    elif 'дождь' in desc or 'дожд' in desc or 'rain' in desc:
        return '🌧'
    elif 'снег' in desc or 'snow' in desc:
        return '❄️'
    elif 'гроза' in desc or 'thunder' in desc:
        return '⛈'
    elif 'туман' in desc or 'fog' in desc:
        return '🌫'
    else:
        return '🌡'


async def get_weather(city: str):
    """Получает погоду с OpenWeatherMap"""
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city,
        'appid': WEATHER_API_KEY,
        'units': 'metric',
        'lang': 'ru'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'city': data['name'],
                    'country': data['sys']['country'],
                    'temp': data['main']['temp'],
                    'feels_like': data['main']['feels_like'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'wind_speed': data['wind']['speed'],
                    'description': data['weather'][0]['description']
                }
            else:
                return {'success': False, 'error': 'Город не найден'}
    except Exception as e:
        return {'success': False, 'error': 'Ошибка соединения'}


async def handle_start(chat_id):
    """Обработка команды /start"""
    text = (
        "👋 <b>Привет! Я погодный бот.</b>\n\n"
        "Я показываю погоду в любом городе мира!\n\n"
        "<b>Как пользоваться:</b>\n"
        "• Отправь название города (например: Москва)\n"
        "• Нажми кнопку \"🌤 Узнать погоду\"\n"
        "• Используй команду /weather Москва\n\n"
        "🌍 Поддерживаются города на русском и английском"
    )
    await send_message(chat_id, text, get_weather_keyboard())


async def handle_help(chat_id):
    """Обработка команды /help"""
    text = (
        "🔍 <b>Помощь</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать работу\n"
        "/help - Показать помощь\n"
        "/weather [город] - Погода в городе\n\n"
        "<b>Примеры:</b>\n"
        "Москва\n"
        "London\n"
        "/weather Париж"
    )
    await send_message(chat_id, text)


async def handle_weather_command(chat_id, text):
    """Обработка команды /weather"""
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        city = parts[1].strip()
        await send_typing(chat_id)
        await show_weather(chat_id, city)
    else:
        await send_message(chat_id, "ℹ️ Напиши: /weather Москва")


async def show_weather(chat_id, city):
    """Показывает погоду для города"""
    # Отправляем сообщение "Ищу..."
    url = f"{TELEGRAM_API}/sendMessage"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "chat_id": chat_id,
            "text": f"🔍 Ищу погоду в <b>{city}</b>...",
            "parse_mode": "HTML"
        })
        wait_msg = resp.json()
        wait_msg_id = wait_msg['result']['message_id']

    # Получаем погоду
    weather = await get_weather(city)

    if weather['success']:
        emoji = get_weather_emoji(weather['description'])
        text = (
            f"{emoji} <b>Погода в {weather['city']}, {weather['country']}</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🌡 <b>Температура:</b> {weather['temp']:.1f}°C\n"
            f"🤔 <b>Ощущается как:</b> {weather['feels_like']:.1f}°C\n"
            f"☁️ <b>Описание:</b> {weather['description'].capitalize()}\n"
            f"💧 <b>Влажность:</b> {weather['humidity']}%\n"
            f"💨 <b>Ветер:</b> {weather['wind_speed']:.1f} м/с\n"
            f"📊 <b>Давление:</b> {weather['pressure']} гПа"
        )

        # Удаляем сообщение "Ищу..."
        async with httpx.AsyncClient() as client:
            await client.post(f"{TELEGRAM_API}/deleteMessage", json={
                "chat_id": chat_id,
                "message_id": wait_msg_id
            })

        # Отправляем результат
        await send_message(chat_id, text, get_weather_keyboard())
    else:
        # Редактируем сообщение "Ищу..." в "Не найдено"
        async with httpx.AsyncClient() as client:
            await client.post(f"{TELEGRAM_API}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": wait_msg_id,
                "text": f"❌ Город '<b>{city}</b>' не найден. Проверь название.",
                "parse_mode": "HTML"
            })


async def handle_message(chat_id, text):
    """Обработка обычных текстовых сообщений"""
    # Если пользователь нажал "Узнать погоду"
    if text == "🌤 Узнать погоду":
        await send_message(chat_id, "🏙 Введи название города:", get_back_keyboard())
        user_states[chat_id] = "waiting_for_city"

    # Если пользователь нажал "Назад"
    elif text == "🔙 Назад":
        user_states.pop(chat_id, None)
        await handle_start(chat_id)

    # Если бот ожидает название города
    elif user_states.get(chat_id) == "waiting_for_city":
        user_states.pop(chat_id, None)
        await send_typing(chat_id)
        await show_weather(chat_id, text)

    # Иначе считаем, что это название города
    elif not text.startswith('/'):
        await send_typing(chat_id)
        await show_weather(chat_id, text)


async def get_updates(offset=None):
    """Получает обновления от Telegram"""
    url = f"{TELEGRAM_API}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=35.0)
            if response.status_code == 200:
                data = response.json()
                if data['ok']:
                    return data['result']
        except Exception as e:
            print(f"Ошибка получения обновлений: {e}")
        return []


async def main():
    """Главный цикл бота"""
    print("=" * 40)
    print("✅ Погодный бот запущен!")
    print("👨‍💻 Бот: @onarjrbot")
    print("=" * 40)

    last_update_id = 0

    while True:
        try:
            updates = await get_updates(last_update_id + 1)

            for update in updates:
                last_update_id = update['update_id']

                if 'message' in update:
                    message = update['message']
                    chat_id = message['chat']['id']
                    text = message.get('text', '')

                    # Обрабатываем команды
                    if text == '/start':
                        await handle_start(chat_id)
                    elif text == '/help':
                        await handle_help(chat_id)
                    elif text.startswith('/weather'):
                        await handle_weather_command(chat_id, text)
                    else:
                        await handle_message(chat_id, text)

        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")

        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())