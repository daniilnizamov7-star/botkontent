import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import datetime
import re

def clean_markdown(text):
    text = re.sub(r"[*]{1,}", "", text)
    text = re.sub(r"#{1,}\s", "", text)
    text = re.sub(r"[`]{1,}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Загружаем переменные окружения
load_dotenv()

# Создаём бота и диспетчер
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
router = Router()

# План публикаций по дням недели
PUBLICATION_PLAN = {
    0: "Напиши пост-кейс для Telegram канала Python разработчика-фрилансера. Тема: выполненный заказ на парсинг сайта. Стиль: просто, по-человечески, без воды, как будто рассказываешь другу. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 150-200 слов.",
    1: "Напиши лайфхак по Python для Telegram канала разработчика. Один конкретный трюк который экономит время. Пример кода 3-5 строк. Объясни зачем это нужно. Стиль: просто и понятно. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 80-100 слов.",
    2: "Напиши вовлекающий вопрос для Telegram канала о Python разработке. Вопрос должен заставить подписчиков ответить в комментариях. Добавь эмодзи и вариианты ответа. Не пиши контакты и ссылки. Объём: 30-50 слов.",
    3: "Напиши продающий пост для Telegram канала Python фрилансера из Челябинска. Услуги: парсинг сайтов, Telegram боты, автоматизация на Python. Цены от 2000 рублей. Стиль: ненавязчиво, с пользой для читателя. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 100-150 слов.",
    4: "Напиши мини-урок по Python для Telegram канала. Тема: что-то полезное из Selenium, requests, pandas или aiogram. Покажи только часть кода — намекни что в реальных проектах есть много нюансов и подводных камней которые знает только опытный разработчик. Стиль: как объясняешь другу. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 120-160 слов.",
    5: "Напиши смешной пост про жизнь программиста для Telegram канала. Тема: баги, заказчики, дедлайны или код в 2 ночи. Стиль: юмор, узнаваемая ситуация. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 50-80 слов.",
    6: "Напиши мотивационный пост для Telegram канала Python разработчика-фрилансера. Тема: почему стоит развиваться в IT даже когда тяжело. Добавь личный штрих от первого лица. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 80-120 слов."
}

async def generate_text_with_yandex_gpt(prompt: str) -> str:
    """Генерирует текст через Yandex GPT API."""
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": f"Api-Key {os.getenv('YANDEX_GPT_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{os.getenv('FOLDER_ID')}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 1000
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты — помощник для создания контента в Telegram‑канале о программировании на Python. Пиши кратко, понятно и с примерами кода, где это уместно."
            },
            {
                "role": "user",
                "text": prompt
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["result"]["alternatives"][0]["message"]["text"]
            else:
                error_text = await response.text()
                print(f"Ошибка API Yandex GPT: статус {response.status}")
                print(f"Текст ошибки: {error_text}")
                return f"Не удалось сгенерировать контент. Ошибка API: {response.status}"


async def publish_daily_post():
    """Генерирует и публикует пост в канал."""
    day_index = datetime.datetime.now().weekday()  # 0 — понедельник, 6 — воскресенье
    prompt = PUBLICATION_PLAN[day_index]

    content = await generate_text_with_yandex_gpt(prompt)
    content = clean_markdown(content)
    # Убираем "Ваш контакт" и похожие фразы
    content = re.sub(r"(?i)(ваш контакт|контакт|связаться со мной|напишите мне)[:\s]*", "", content)
    content = re.sub(r"@\w+", "", content)  # убираем старые упоминания
    content = content.strip()
    content += "\n\n📩 @Aslyamov74"

    try:
        await bot.send_message(
            chat_id=os.getenv("CHANNEL_ID"),
            text=content
        )
        print(f"Пост опубликован: {datetime.datetime.now().strftime('%A')}")
    except Exception as e:
        print(f"Ошибка при публикации: {e}")

@router.message(Command("start"))
@router.message(Command("help"))
async def send_welcome(message: Message):
    await message.answer("Бот запущен! Ежедневно в 9:00 будет публиковаться новый пост.")

@router.message(Command("test_post"))
async def test_post(message: Message):
    """Команда для ручного запуска публикации."""
    await publish_daily_post()
    await message.answer("Тестовый пост опубликован!")

async def main():
    # Подключаем роутер к диспетчеру
    dp.include_router(router)

    # Запускаем планировщик (ежедневно в 9:00)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(publish_daily_post, 'cron', hour=4, minute=0, timezone='UTC')  # 9:00 Челябинск (UTC+5)
    scheduler.start()

    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
