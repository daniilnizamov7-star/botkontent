import os
import asyncio
import aiohttp
import re
import datetime
import textwrap
import io

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
router = Router()

# ─── Данные по дням ───────────────────────────────────────────────────────────

DAY_META = {
    0: {"type": "КЕЙС",      "icon": ">>",  "subtitle": "Реальный опыт",   "day": "ПН"},
    1: {"type": "ЛАЙФХАК",   "icon": "//",  "subtitle": "Экономь время",   "day": "ВТ"},
    2: {"type": "ВОПРОС",    "icon": "??",  "subtitle": "Твоё мнение",     "day": "СР"},
    3: {"type": "ОФФЕР",     "icon": "**",  "subtitle": "Работаем вместе", "day": "ЧТ"},
    4: {"type": "УРОК",      "icon": "{}",  "subtitle": "Учимся вместе",   "day": "ПТ"},
    5: {"type": "МЕМ",       "icon": ":)",  "subtitle": "Узнаёшь себя?",  "day": "СБ"},
    6: {"type": "МОТИВАЦИЯ", "icon": "^^",  "subtitle": "Не сдавайся",     "day": "ВС"},
}

PUBLICATION_PLAN = {
    0: "Напиши пост-кейс для Telegram канала Python разработчика-фрилансера. Тема: выполненный заказ на парсинг сайта. Стиль: просто, по-человечески, без воды, как будто рассказываешь другу. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 150-200 слов.",
    1: "Напиши лайфхак по Python для Telegram канала разработчика. Один конкретный трюк который экономит время. Пример кода 3-5 строк. Объясни зачем это нужно. Стиль: просто и понятно. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 80-100 слов.",
    2: "Напиши вовлекающий вопрос для Telegram канала о Python разработке. Вопрос должен заставить подписчиков ответить в комментариях. Добавь эмодзи и варианты ответа. Не пиши контакты и ссылки. Объём: 30-50 слов.",
    3: "Напиши продающий пост для Telegram канала Python фрилансера из Челябинска. Услуги: парсинг сайтов, Telegram боты, автоматизация на Python. Цены от 2000 рублей. Стиль: ненавязчиво, с пользой для читателя. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 100-150 слов.",
    4: "Напиши мини-урок по Python для Telegram канала. Тема: что-то полезное из Selenium, requests, pandas или aiogram. Покажи только часть кода — намекни что в реальных проектах есть много нюансов и подводных камней которые знает только опытный разработчик. Стиль: как объясняешь другу. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 120-160 слов.",
    5: "Напиши смешной пост про жизнь программиста для Telegram канала. Тема: баги, заказчики, дедлайны или код в 2 ночи. Стиль: юмор, узнаваемая ситуация. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 50-80 слов.",
    6: "Напиши мотивационный пост для Telegram канала Python разработчика-фрилансера. Тема: почему стоит развиваться в IT даже когда тяжело. Добавь личный штрих от первого лица. Добавь эмодзи. Не пиши контакты и ссылки. Объём: 80-120 слов."
}

# ─── Вспомогательные функции ─────────────────────────────────────────────────

def clean_markdown(text):
    text = re.sub(r"[*]{1,}", "", text)
    text = re.sub(r"#{1,}\s", "", text)
    text = re.sub(r"[`]{1,}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def generate_text_with_yandex_gpt(prompt: str) -> str:
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
                print(f"Ошибка API Yandex GPT: {response.status} — {error_text}")
                return f"Ошибка генерации: {response.status}"


async def generate_title_for_image(post_text: str, day_type: str) -> str:
    prompt = (
        f"На основе этого поста придумай ОДИН короткий заголовок для картинки-анонса. "
        f"Тип поста: {day_type}. "
        f"Требования: максимум 8 слов, цепляющий, без кавычек, без точки в конце, на русском языке. "
        f"Верни ТОЛЬКО заголовок, ничего лишнего.\n\nПост:\n{post_text[:500]}"
    )
    title = await generate_text_with_yandex_gpt(prompt)
    title = title.strip().strip('"').strip("'").strip()
    title = title.split('\n')[0].strip()
    return title


def get_font(size: int):
    """Загружает системный шрифт с поддержкой кириллицы."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_story_image_pillow(title: str, day_index: int) -> bytes:
    """Генерирует картинку 1080x1920 через Pillow."""
    W, H = 1080, 1920
    meta = DAY_META[day_index]

    # Цвета
    BG       = (10, 10, 20)
    GREEN    = (0, 200, 140)
    GREEN_DK = (0, 120, 85)
    WHITE    = (255, 255, 255)
    GRAY     = (130, 130, 150)
    LINE_CLR = (25, 35, 45)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── Фоновая сетка ──
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=(20, 30, 25), width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=(20, 30, 25), width=1)

    # ── Верхняя полоса ──
    draw.rectangle([(0, 0), (W, 8)], fill=GREEN)

    # ── Левая боковая линия ──
    draw.rectangle([(36, 200), (42, H - 200)], fill=GREEN_DK)

    # ── Тип поста ──
    font_type = get_font(56)
    draw.text((85, 75), f"[ {meta['type']} ]", font=font_type, fill=GREEN)

    # ── Разделитель под типом ──
    draw.line([(85, 178), (W - 85, 178)], fill=LINE_CLR, width=2)

    # ── Символьная иконка по центру (ASCII-арт вместо эмодзи) ──
    font_icon = get_font(180)
    draw.text((W // 2, H // 2 - 340), meta["icon"],
              font=font_icon, fill=GREEN, anchor="mm")

    # ── Заголовок с переносом строк ──
    if len(title) <= 20:
        f = get_font(100)
        wrap_w = 12
    elif len(title) <= 40:
        f = get_font(82)
        wrap_w = 16
    elif len(title) <= 60:
        f = get_font(68)
        wrap_w = 20
    else:
        f = get_font(56)
        wrap_w = 24

    lines = textwrap.wrap(title, width=wrap_w)
    line_h = f.size + 24
    total_h = len(lines) * line_h
    y_start = H // 2 - total_h // 2 + 60

    for i, line in enumerate(lines):
        draw.text((W // 2, y_start + i * line_h), line,
                  font=f, fill=WHITE, anchor="mm")

    # ── Подзаголовок ──
    font_sub = get_font(42)
    draw.text((W // 2, y_start + total_h + 55), meta["subtitle"],
              font=font_sub, fill=GRAY, anchor="mm")

    # ── Нижняя линия ──
    draw.line([(85, H - 170), (W - 85, H - 170)], fill=LINE_CLR, width=2)

    # ── Канал слева, день справа ──
    font_bot = get_font(46)
    draw.text((85, H - 130), "@Daniil_dev74", font=font_bot, fill=GREEN)
    draw.text((W - 85, H - 130), meta["day"], font=font_bot, fill=GRAY, anchor="ra")

    # Сохраняем в байты
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── Основная функция публикации ─────────────────────────────────────────────

async def publish_daily_post():
    day_index = datetime.datetime.now().weekday()
    prompt = PUBLICATION_PLAN[day_index]
    meta = DAY_META[day_index]

    print(f"[{datetime.datetime.now()}] Начинаю генерацию поста ({meta['type']})...")

    # 1. Генерируем текст
    content = await generate_text_with_yandex_gpt(prompt)
    content = clean_markdown(content)
    content = re.sub(r"(?i)(ваш контакт|контакт|связаться со мной|напишите мне)[:\s]*", "", content)
    content = re.sub(r"@\w+", "", content)
    content = content.strip()
    content += "\n\n📩 @Aslyamov74"

    # 2. Генерируем заголовок для картинки
    title = await generate_title_for_image(content, meta["type"])
    print(f"Заголовок картинки: {title}")

    # 3. Генерируем картинку
    try:
        image_bytes = await asyncio.get_event_loop().run_in_executor(
            None, generate_story_image_pillow, title, day_index
        )
        print("Картинка сгенерирована ✅")
    except Exception as e:
        print(f"Ошибка генерации картинки: {e}")
        image_bytes = None

    # 4. Публикуем
    try:
        channel_id = os.getenv("CHANNEL_ID")
        if image_bytes:
            photo = BufferedInputFile(image_bytes, filename="post.png")
            await bot.send_photo(
                chat_id=channel_id,
                photo=photo,
                caption=content
            )
        else:
            await bot.send_message(chat_id=channel_id, text=content)
        print(f"Пост опубликован: {datetime.datetime.now().strftime('%A %H:%M')}")
    except Exception as e:
        print(f"Ошибка при публикации: {e}")


# ─── Команды бота ─────────────────────────────────────────────────────────────

@router.message(Command("start"))
@router.message(Command("help"))
async def send_welcome(message: Message):
    await message.answer(
        "Бот запущен! ✅\n"
        "Каждый день в 9:00 по Челябинску публикуется пост с картинкой.\n\n"
        "/test_post — опубликовать тестовый пост прямо сейчас"
    )


@router.message(Command("test_post"))
async def test_post(message: Message):
    await message.answer("Генерирую пост с картинкой... ⏳")
    await publish_daily_post()
    await message.answer("Готово! ✅")


# ─── Запуск ───────────────────────────────────────────────────────────────────

async def main():
    dp.include_router(router)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(publish_daily_post, 'cron', hour=4, minute=0, timezone='UTC')
    scheduler.start()
    print("Бот запущен. Ожидаю команды...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
