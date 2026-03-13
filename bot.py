import os
import asyncio
import aiohttp
import re
import datetime
import tempfile

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from playwright.async_api import async_playwright

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
router = Router()

# ─── HTML шаблон для картинки ────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Russo+One&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    width: 1080px;
    height: 1920px;
    background: #0a0a0f;
    font-family: 'Inter', sans-serif;
    color: white;
    overflow: hidden;
    position: relative;
  }}

  /* Фоновые элементы */
  .bg-grid {{
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,255,180,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,255,180,0.04) 1px, transparent 1px);
    background-size: 60px 60px;
  }}

  .bg-glow {{
    position: absolute;
    width: 900px;
    height: 900px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(0,200,150,0.12) 0%, transparent 70%);
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }}

  .bg-accent {{
    position: absolute;
    width: 400px;
    height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(80,120,255,0.15) 0%, transparent 70%);
    top: 100px;
    right: -100px;
  }}

  /* Верхняя полоса */
  .top-bar {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 6px;
    background: linear-gradient(90deg, #00c896, #5078ff, #00c896);
    background-size: 200% 100%;
  }}

  /* Тип поста */
  .post-type {{
    position: absolute;
    top: 80px;
    left: 80px;
    font-size: 28px;
    font-weight: 600;
    color: #00c896;
    letter-spacing: 4px;
    text-transform: uppercase;
    opacity: 0.9;
  }}

  .post-type::before {{
    content: '';
    display: inline-block;
    width: 10px;
    height: 10px;
    background: #00c896;
    border-radius: 50%;
    margin-right: 14px;
    vertical-align: middle;
    box-shadow: 0 0 12px #00c896;
  }}

  /* Разделитель */
  .divider {{
    position: absolute;
    top: 160px;
    left: 80px;
    right: 80px;
    height: 1px;
    background: linear-gradient(90deg, #00c896, transparent);
    opacity: 0.3;
  }}

  /* Центральная область */
  .content {{
    position: absolute;
    top: 50%;
    left: 80px;
    right: 80px;
    transform: translateY(-50%);
    text-align: center;
  }}

  .icon {{
    font-size: 100px;
    margin-bottom: 60px;
    filter: drop-shadow(0 0 20px rgba(0,200,150,0.5));
  }}

  .title {{
    font-family: 'Russo One', sans-serif;
    font-size: {font_size}px;
    line-height: 1.2;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #ffffff 0%, #00c896 50%, #5078ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 50px;
    text-shadow: none;
    padding: 0 20px;
  }}

  .subtitle {{
    font-size: 34px;
    color: rgba(255,255,255,0.45);
    font-weight: 400;
    letter-spacing: 1px;
  }}

  /* Нижняя часть */
  .bottom {{
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 60px 80px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}

  .channel {{
    font-size: 36px;
    font-weight: 600;
    color: #00c896;
    letter-spacing: 1px;
  }}

  .channel span {{
    color: rgba(255,255,255,0.3);
    font-weight: 400;
  }}

  .day-badge {{
    background: rgba(0,200,150,0.1);
    border: 1px solid rgba(0,200,150,0.3);
    border-radius: 50px;
    padding: 16px 36px;
    font-size: 30px;
    font-weight: 600;
    color: rgba(255,255,255,0.6);
    letter-spacing: 2px;
  }}

  /* Боковые декоры */
  .side-line {{
    position: absolute;
    left: 40px;
    top: 200px;
    bottom: 200px;
    width: 2px;
    background: linear-gradient(180deg, transparent, rgba(0,200,150,0.3), transparent);
  }}
</style>
</head>
<body>
  <div class="bg-grid"></div>
  <div class="bg-glow"></div>
  <div class="bg-accent"></div>
  <div class="top-bar"></div>
  <div class="side-line"></div>

  <div class="post-type">{post_type}</div>
  <div class="divider"></div>

  <div class="content">
    <div class="icon">{icon}</div>
    <div class="title">{title}</div>
    <div class="subtitle">{subtitle}</div>
  </div>

  <div class="bottom">
    <div class="channel"><span>канал</span> @Daniil_dev74</div>
    <div class="day-badge">{day_name}</div>
  </div>
</body>
</html>"""

# ─── Данные по дням ───────────────────────────────────────────────────────────

DAY_META = {
    0: {"type": "КЕЙС",      "icon": "💼", "subtitle": "Реальный опыт",    "day": "ПН"},
    1: {"type": "ЛАЙФХАК",   "icon": "⚡", "subtitle": "Экономь время",    "day": "ВТ"},
    2: {"type": "ВОПРОС",    "icon": "🤔", "subtitle": "Твоё мнение",      "day": "СР"},
    3: {"type": "ОФФЕР",     "icon": "🚀", "subtitle": "Работаем вместе",  "day": "ЧТ"},
    4: {"type": "УРОК",      "icon": "📚", "subtitle": "Учимся вместе",    "day": "ПТ"},
    5: {"type": "МЕМ",       "icon": "😄", "subtitle": "Узнаёшь себя?",   "day": "СБ"},
    6: {"type": "МОТИВАЦИЯ", "icon": "🔥", "subtitle": "Не сдавайся",      "day": "ВС"},
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

# ─── Вспомогательные функции ──────────────────────────────────────────────────

def clean_markdown(text):
    text = re.sub(r"[*]{1,}", "", text)
    text = re.sub(r"#{1,}\s", "", text)
    text = re.sub(r"[`]{1,}", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_font_size(text: str) -> int:
    """Подбирает размер шрифта по длине заголовка."""
    length = len(text)
    if length <= 30:
        return 110
    elif length <= 60:
        return 85
    elif length <= 90:
        return 68
    else:
        return 54


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
                print(f"Ошибка API Yandex GPT: {response.status} — {error_text}")
                return f"Ошибка генерации: {response.status}"


async def generate_title_for_image(post_text: str, day_type: str) -> str:
    """Генерирует короткий заголовок для картинки на основе поста."""
    prompt = (
        f"На основе этого поста придумай ОДИН короткий заголовок для картинки-анонса. "
        f"Тип поста: {day_type}. "
        f"Требования: максимум 8 слов, цепляющий, без кавычек, без точки в конце, на русском языке. "
        f"Верни ТОЛЬКО заголовок, ничего лишнего.\n\nПост:\n{post_text[:500]}"
    )
    title = await generate_text_with_yandex_gpt(prompt)
    # Чистим на случай если GPT добавил лишнее
    title = title.strip().strip('"').strip("'").strip()
    # Берём только первую строку
    title = title.split('\n')[0].strip()
    return title


async def generate_story_image(title: str, day_index: int) -> bytes:
    """Генерирует PNG картинку 1080x1920 через Playwright."""
    meta = DAY_META[day_index]
    font_size = get_font_size(title)

    html = HTML_TEMPLATE.format(
        post_type=meta["type"],
        icon=meta["icon"],
        title=title,
        subtitle=meta["subtitle"],
        day_name=meta["day"],
        font_size=font_size,
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.set_content(html, wait_until="networkidle")
        # Ждём загрузки Google Fonts
        await asyncio.sleep(1)
        screenshot = await page.screenshot(type="png")
        await browser.close()

    return screenshot


# ─── Основная функция публикации ──────────────────────────────────────────────

async def publish_daily_post():
    """Генерирует картинку + текст и публикует в канал."""
    day_index = datetime.datetime.now().weekday()
    prompt = PUBLICATION_PLAN[day_index]
    meta = DAY_META[day_index]

    print(f"[{datetime.datetime.now()}] Начинаю генерацию поста ({meta['type']})...")

    # 1. Генерируем текст поста
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
        image_bytes = await generate_story_image(title, day_index)
        print("Картинка сгенерирована успешно")
    except Exception as e:
        print(f"Ошибка генерации картинки: {e}")
        image_bytes = None

    # 4. Публикуем в канал
    try:
        channel_id = os.getenv("CHANNEL_ID")

        if image_bytes:
            # Отправляем картинку с текстом как подпись
            photo = BufferedInputFile(image_bytes, filename="post.png")
            await bot.send_photo(
                chat_id=channel_id,
                photo=photo,
                caption=content
            )
        else:
            # Если картинка не сгенерировалась — отправляем только текст
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
