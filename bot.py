import asyncio
import httpx
from datetime import datetime

# ========== ТОКЕНЫ (УЖЕ ВСТАВЛЕНЫ) ==========
BOT_TOKEN = "8628470329:AAGNu__7pUBGbxo5UoRehztxrxHqsNrayFM"
WEATHER_API_KEY = "3a678ada131c76b2d68e764b1a4301c4"
# ============================================

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
user_states = {}

async def send_message(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def send_typing(chat_id):
    url = f"{TELEGRAM_API}/sendChatAction"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "action": "typing"})

def get_weather_keyboard():
    return {"keyboard": [[{"text": "🌤 Узнать погоду"}]], "resize_keyboard": True}

def get_back_keyboard():
    return {"keyboard": [[{"text": "🔙 Назад"}]], "resize_keyboard": True}

def get_weather_emoji(description: str) -> str:
    desc = description.lower()
    if 'ясно' in desc or 'солнеч' in desc:
        return '☀️'
    elif 'облач' in desc or 'пасмур' in desc:
        return '☁️'
    elif 'дождь' in desc:
        return '🌧'
    elif 'снег' in desc:
        return '❄️'
    elif 'гроза' in desc:
        return '⛈'
    return '🌡'

async def get_weather(city: str):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {'q': city, 'appid': WEATHER_API_KEY, 'units': 'metric', 'lang': 'ru'}
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
            return {'success': False, 'error': 'Город не найден'}
    except Exception:
        return {'success': False, 'error': 'Ошибка соединения'}

async def handle_start(chat_id):
    text = (
        "👋 <b>Привет! Я погодный бот.</b>\n\n"
        "Отправь название города, и я покажу погоду!\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать\n"
        "/help - Помощь\n"
        "/weather Москва - Погода в городе"
    )
    await send_message(chat_id, text, get_weather_keyboard())

async def handle_help(chat_id):
    text = "🔍 Отправь название города, например: Москва, London, Париж"
    await send_message(chat_id, text)

async def handle_weather_command(chat_id, text):
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        await send_typing(chat_id)
        await show_weather(chat_id, parts[1].strip())
    else:
        await send_message(chat_id, "ℹ️ Напиши: /weather Москва")

async def show_weather(chat_id, city):
    # Отправляем "Ищу..."
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": f"🔍 Ищу погоду в <b>{city}</b>...",
            "parse_mode": "HTML"
        })
        wait_msg_id = resp.json()['result']['message_id']

    weather = await get_weather(city)

    if weather['success']:
        emoji = get_weather_emoji(weather['description'])
        text = (
            f"{emoji} <b>Погода в {weather['city']}, {weather['country']}</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🌡 Температура: {weather['temp']:.1f}°C\n"
            f"🤔 Ощущается: {weather['feels_like']:.1f}°C\n"
            f"☁️ {weather['description'].capitalize()}\n"
            f"💧 Влажность: {weather['humidity']}%\n"
            f"💨 Ветер: {weather['wind_speed']:.1f} м/с\n"
            f"📊 Давление: {weather['pressure']} гПа"
        )
        async with httpx.AsyncClient() as client:
            await client.post(f"{TELEGRAM_API}/deleteMessage", json={
                "chat_id": chat_id, "message_id": wait_msg_id
            })
        await send_message(chat_id, text, get_weather_keyboard())
    else:
        async with httpx.AsyncClient() as client:
            await client.post(f"{TELEGRAM_API}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": wait_msg_id,
                "text": f"❌ Город '<b>{city}</b>' не найден",
                "parse_mode": "HTML"
            })

async def handle_message(chat_id, text):
    if text == "🌤 Узнать погоду":
        await send_message(chat_id, "🏙 Введи название города:", get_back_keyboard())
        user_states[chat_id] = "waiting_for_city"
    elif text == "🔙 Назад":
        user_states.pop(chat_id, None)
        await handle_start(chat_id)
    elif user_states.get(chat_id) == "waiting_for_city":
        user_states.pop(chat_id, None)
        await send_typing(chat_id)
        await show_weather(chat_id, text)
    elif not text.startswith('/'):
        await send_typing(chat_id)
        await show_weather(chat_id, text)

async def get_updates(offset=None):
    url = f"{TELEGRAM_API}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=35.0)
            if response.status_code == 200 and response.json()['ok']:
                return response.json()['result']
        except Exception:
            pass
        return []

async def main():
    print("=" * 40)
    print("✅ Погодный бот запущен!")
    print("=" * 40)
    last_update_id = 0
    while True:
        try:
            updates = await get_updates(last_update_id + 1)
            for update in updates:
                last_update_id = update['update_id']
                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']
                    text = msg.get('text', '')
                    if text == '/start':
                        await handle_start(chat_id)
                    elif text == '/help':
                        await handle_help(chat_id)
                    elif text.startswith('/weather'):
                        await handle_weather_command(chat_id, text)
                    else:
                        await handle_message(chat_id, text)
        except Exception as e:
            print(f"Ошибка: {e}")
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
