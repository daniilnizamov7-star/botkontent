import os
import asyncio
import aiohttp
import re
import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
router = Router()

# Дата начала канала
START_DATE = datetime.datetime(2026, 3, 5)

# График работы: 4 дня работа / 4 дня отдых
WORK_CYCLE = 8
WORK_DAYS = 4


PUBLICATION_PLAN = {
    0: "Напиши пост для Telegram канала 'Даниил с завода'. Автор сегодня писал Python-скрипт для парсинга сайта. Расскажи как он разбирался и что получилось. Стиль личного дневника. 120-160 слов.",

    1: "Напиши пост для Telegram канала 'Даниил с завода'. Сегодня автор изучил небольшой лайфхак по Python который экономит время. Добавь короткий пример кода 3-5 строк.",

    2: "Напиши пост-вопрос для подписчиков. Автор учится Python и спрашивает совет у аудитории: какой инструмент изучать дальше или как люди учили программирование.",

    3: "Напиши пост о том как Python помогает автоматизировать работу. Представь что автор только сегодня это понял и делится открытием.",

    4: "Напиши мини-урок по Python который автор сегодня изучал. Например Selenium, requests или aiogram. Объясни как новичок который только разобрался.",

    5: "Напиши лёгкий пост про жизнь человека который учит программирование после работы на заводе. Можно добавить немного юмора.",

    6: "Напиши мотивационный пост о том как трудно учиться после работы, но автор продолжает идти к цели — уйти с завода и работать в IT."
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


async def generate_text_with_yandex_gpt(prompt: str):

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
            "maxTokens": 1000
        },
        "messages": [
            {
                "role": "system",
                "text": """
Ты пишешь посты для Telegram канала "Даниил с завода".

Контекст:
Автор канала — обычный человек который работает на заводе по производству алюминиевых банок.
После смены он изучает Python, AI и автоматизацию чтобы уйти с завода.

Стиль:
Пиши как личный блог.
Просто и по-человечески.
Не как учебник и не как статья.

Иногда упоминай:
— что автор учится после работы
— что не всё получается сразу
— что он только разбирается в программировании

Пост должен читаться как история дня или личный опыт обучения.
Можно иногда добавлять лёгкие эмоции и эмодзи.
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

            if response.status == 200:

                result = await response.json()

                return result["result"]["alternatives"][0]["message"]["text"]

            else:

                error_text = await response.text()

                print(f"Ошибка API Yandex GPT: {response.status} — {error_text}")

                return "Ошибка генерации текста"


async def publish_daily_post():

    print(f"[{datetime.datetime.now()}] Генерирую пост...")

    day_index = datetime.datetime.now().weekday()

    # Если рабочий день
    if is_work_day():

        prompt = (
            "Напиши пост для Telegram канала 'Даниил с завода'. "
            "Сегодня была 12-часовая смена на заводе. "
            "Автор устал, но всё равно вечером сел немного изучать Python или AI. "
            "Расскажи небольшую историю обучения после работы. "
            "Стиль личного дневника. 80-120 слов."
        )

    else:

        prompt = PUBLICATION_PLAN[day_index]

    content = await generate_text_with_yandex_gpt(prompt)

    content = clean_markdown(content)

    # удаляем контакты если модель их добавит
    content = re.sub(r"(?i)(ваш контакт|контакт|связаться со мной|напишите мне)[:\s]*", "", content)
    content = re.sub(r"@\w+", "", content)

    # считаем номер дня
    day_number = (datetime.datetime.now() - START_DATE).days + 1

    content = f"День {day_number}. Путь из завода в IT\n\n{content}"

    content = content.strip()

    content += "\n\n📩 @Aslyamov74"

    try:

        await bot.send_message(
            chat_id=os.getenv("CHANNEL_ID"),
            text=content
        )

        print(f"Пост опубликован: {datetime.datetime.now().strftime('%A %H:%M')}")

    except Exception as e:

        print(f"Ошибка при публикации: {e}")


@router.message(Command("start"))
@router.message(Command("help"))
async def send_welcome(message: Message):

    await message.answer(
        "Бот запущен! ✅\n"
        "Каждый день в 9:00 по Челябинску публикуется новый пост.\n\n"
        "/test_post — опубликовать пост прямо сейчас"
    )


@router.message(Command("test_post"))
async def test_post(message: Message):

    await message.answer("Генерирую пост... ⏳")

    await publish_daily_post()

    await message.answer("Пост опубликован! ✅")


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

    print("Бот запущен. Ожидаю команды...")

    await dp.start_polling(bot)


if __name__ == '__main__':

    asyncio.run(main())
