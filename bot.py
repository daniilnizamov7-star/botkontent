import os
import asyncio
import aiohttp
import re
import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
router = Router()

START_DATE = datetime.datetime(2026, 3, 5)

WORK_CYCLE = 8
WORK_DAYS = 4


PUBLICATION_PLAN = {
    0: "Напиши пост про то как автор делал Python скрипт для парсинга сайта.",
    1: "Напиши пост про маленький лайфхак Python который экономит время.",
    2: "Напиши пост-вопрос подписчикам про изучение программирования.",
    3: "Напиши пост про автоматизацию задач с помощью Python.",
    4: "Напиши мини урок по Python библиотеке.",
    5: "Напиши смешной пост про жизнь программиста.",
    6: "Напиши мотивационный пост про путь в IT."
}


def clean_markdown(text):

    text = re.sub(r"[*]{1,}", "", text)
    text = re.sub(r"#{1,}\s", "", text)
    text = re.sub(r"[`]{1,}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def is_work_day():

    today = datetime.datetime.now()
    days_passed = (today - START_DATE).days

    cycle_day = days_passed % WORK_CYCLE

    return cycle_day < WORK_DAYS


async def generate_text(prompt):

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": f"Api-Key {os.getenv('YANDEX_GPT_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{os.getenv('FOLDER_ID')}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 800
        },
        "messages": [
            {
                "role": "system",
                "text": """
Ты пишешь посты для Telegram канала "Даниил с завода".

Автор — обычный человек который работает на заводе
и после смены изучает Python и AI.

Пиши как личный блог.
Просто и по-человечески.
"""
            },
            {
                "role": "user",
                "text": prompt
            }
        ]
    }

    async with aiohttp.ClientSession() as session:

        async with session.post(url, headers=headers, json=data) as response:

            result = await response.json()

            return result["result"]["alternatives"][0]["message"]["text"]


async def generate_image_prompt(post_text):

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": f"Api-Key {os.getenv('YANDEX_GPT_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{os.getenv('FOLDER_ID')}/yandexgpt/latest",
        "completionOptions": {
            "temperature": 0.7,
            "maxTokens": 100
        },
        "messages": [
            {
                "role": "system",
                "text": "Сделай короткое описание картинки для AI генерации."
            },
            {
                "role": "user",
                "text": post_text
            }
        ]
    }

    async with aiohttp.ClientSession() as session:

        async with session.post(url, headers=headers, json=data) as response:

            result = await response.json()

            return result["result"]["alternatives"][0]["message"]["text"]


async def generate_image(prompt):

    url = f"https://image.pollinations.ai/prompt/{prompt}"

    async with aiohttp.ClientSession() as session:

        async with session.get(url) as response:

            if response.status == 200:

                image_data = await response.read()

                with open("image.jpg", "wb") as f:

                    f.write(image_data)

                return "image.jpg"

            else:

                return None


async def publish_daily_post():

    day_index = datetime.datetime.now().weekday()

    if is_work_day():

        prompt = (
            "Напиши пост про рабочую смену 12 часов на заводе и "
            "как автор вечером немного учит Python."
        )

    else:

        prompt = PUBLICATION_PLAN[day_index]

    content = await generate_text(prompt)

    content = clean_markdown(content)

    day_number = (datetime.datetime.now() - START_DATE).days + 1

    content = f"День {day_number}. Путь из завода в IT\n\n{content}"

    content += "\n\n📩 @Aslyamov74"

    image_prompt = await generate_image_prompt(content)

    image_path = await generate_image(image_prompt)

    try:

        if image_path:

            photo = FSInputFile(image_path)

            await bot.send_photo(
                chat_id=os.getenv("CHANNEL_ID"),
                photo=photo,
                caption=content
            )

        else:

            await bot.send_message(
                chat_id=os.getenv("CHANNEL_ID"),
                text=content
            )

    except Exception as e:

        print(f"Ошибка публикации: {e}")


@router.message(Command("start"))
async def start(message: Message):

    await message.answer("Бот работает ✅")


@router.message(Command("test_post"))
async def test_post(message: Message):

    await message.answer("Генерирую пост...")

    await publish_daily_post()

    await message.answer("Готово")


async def main():

    dp.include_router(router)

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        publish_daily_post,
        'cron',
        hour=4,
        minute=0,
        timezone='UTC'
    )

    scheduler.start()

    await dp.start_polling(bot)


if __name__ == '__main__':

    asyncio.run(main())
