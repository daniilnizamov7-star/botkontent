import os
import asyncio
import aiohttp
import re
import datetime
import json
import random
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
router = Router()

START_DATE = datetime.datetime(2026, 4, 12)
HISTORY_FILE = "posted_topics.json"  # Файл для хранения истории

# ===== ОГРОМНЫЙ ПУЛ ТЕМ (50+ вариантов) =====
ALL_TOPICS = {
    "parsing": [
        "парсинг цен с Wildberries для мониторинга конкурентов",
        "сбор контактов стоматологий с Яндекс.Карт",
        "парсинг объявлений с Авито по недвижимости",
        "автоматический сбор курсов валют с ЦБ РФ",
        "парсинг отзывов с Ozon для анализа товаров",
        "сбор данных о вакансиях с HeadHunter",
        "парсинг расписания поездов с РЖД",
        "мониторинг наличия товаров в интернет-магазинах",
        "сбор email компаний с корпоративных сайтов",
        "парсинг прогноза погоды для анализа",
    ],
    "python_basics": [
        "f-strings vs format() — что быстрее и удобнее",
        "list comprehensions — красота Python в одну строку",
        "enumerate() чтобы не использовать range(len())",
        "zip() для параллельного перебора списков",
        "get() для безопасной работы со словарями",
        "срезы списков [start:stop:step] — мощь Python",
        "lambda функции когда они действительно нужны",
        "генераторы yield для экономии памяти",
        "контекстные менеджеры with open()",
        "args и kwargs для гибких функций",
    ],
    "libraries": [
        "requests — работа с API и HTTP запросами",
        "BeautifulSoup — парсинг HTML страниц",
        "pandas — анализ данных в таблицах",
        "aiogram — создание Telegram ботов",
        "asyncio — асинхронное программирование",
        "selenium — автоматизация браузера",
        "openpyxl — работа с Excel файлами",
        "python-telegram-bot — альтернатива aiogram",
        "lxml — быстрый парсинг XML/HTML",
        "json модуль — работа с JSON данными",
    ],
    "automation": [
        "автоматическое переименование 1000 файлов",
        "автозаполнение Google Forms через скрипт",
        "автоматическая отправка email с вложениями",
        "бэкап важных файлов по расписанию",
        "конвертация изображений PNG в JPG пакетно",
        "автоматическая выгрузка данных в Telegram",
        "парсинг + рассылка уведомлений в мессенджер",
        "автопостинг в социальные сети",
        "мониторинг сайтов и алерт при изменениях",
        "автоматическое создание отчетов Excel",
    ],
    "debugging": [
        "как я искал баг 3 часа а оказалось опечатка",
        "print() vs logging — правильный отладочный вывод",
        "try-except чтобы программа не падала",
        "дебаг асинхронного кода — это боль",
        "как читать traceback и не паниковать",
        "breakpoint() — встроенный дебаггер Python",
        "типичные ошибки новичков в Python",
        "как я случайно удалил не тот файл скриптом",
        "бесконечный цикл который я не заметил",
        "утечка памяти в моем парсере",
    ],
    "work_life": [
        "12 часов на заводе и вечером код — как выжить",
        "почему решил уйти из завода в IT",
        "как семья относится к моему увлечению программированием",
        "усталость после смены и мотивация учиться",
        "баланс работа-учеба-личная жизнь",
        "сколько реально нужно времени чтобы стать программистом",
        "первый заработанный рубль на коде",
        "как объясняю друзьям чем занимаюсь",
        "страх что ничего не получится",
        "маленькие победы которые мотивируют",
    ],
    "learning": [
        "какие курсы я проходил и стоит ли оно того",
        "YouTube каналы которые реально помогают",
        "книги по Python которые стоит прочитать",
        "как я учу английский для программирования",
        "важно ли знать математику для IT",
        "как запоминать синтаксис и функции",
        "почему важно писать код каждый день",
        "пет-проекты лучше чем просто смотреть туториалы",
        "как я читаю чужой код на GitHub",
        "важность комментариев в коде",
    ],
    "tools": [
        "VS Code — мои любимые расширения",
        "Git — как я научился не бояться коммитов",
        "GitHub — хостинг моих проектов",
        "PythonAnywhere — первый бесплатный хостинг",
        "Docker — пока сложно но интересно",
        "виртуальные окружения venv обязательно",
        "Black — автоформатирование кода",
        "Postman — тестирование API",
        "Regex101 — спасатель для регулярных выражений",
        "Stack Overflow — как правильно задавать вопросы",
    ],
    "projects": [
        "мой первый Telegram бот — что получилось",
        "парсер который реально использует знакомый",
        "скрипт который экономит мне 2 часа в неделю",
        "бот для учета личных финансов",
        "телеграм бот для напоминаний",
        "парсер вакансий для анализа рынка",
        "скрипт для автоматической сортировки файлов",
        "бот для розыгрышей в Telegram",
        "скрипт для скачивания видео с YouTube",
        "автоматизация рутины на работе",
    ],
    "motivation": [
        "никогда не поздно начать — мне 25/30/35 и я учусь",
        "сравниваю себя вчерашнего и сегодняшнего",
        "каждый день по часу лучше чем 7 часов в выходной",
        "не бойся задавать глупые вопросы",
        "ошибки — это нормально, это опыт",
        "главное не бросить после первого месяца",
        "все когда-то начинали с print('Hello World')",
        "прокрастинация vs дисциплина",
        "важно отмечать прогресс даже маленький",
        "через год будешь благодарен себе сегодняшнему",
    ],
    "humor": [
        "когда код работает но ты не понимаешь почему",
        "закомментированный код который страшно удалить",
        "копипаста со Stack Overflow — наш выбор",
        "когда забыл точку с запятой в другом языке",
        "бесконечный цикл в реальной жизни",
        "когда тестировщик нашел баг который ты искал неделю",
        "почему на моей машине все работало",
        "когда клиент меняет ТЗ в десятый раз",
        "дедлайн вчера — знакомая ситуация",
        "когда код работает на проде но не локально",
    ],
    "questions": [
        "какая была самая сложная тема которую вы изучали",
        "сколько времени в день вы уделяете учебе",
        "какой был ваш первый язык программирования",
        "работаете ли по специальности или самоучка",
        "какие ресурсы используете для обучения",
        "что мотивирует продолжать когда трудно",
        "какой проект был самым интересным",
        "советы тем кто только начинает",
        "как вы боретесь с выгоранием",
        "планируете ли переходить на другой язык кроме Python",
    ],
}

# ===== СОСТОЯНИЕ =====
posted_history = {
    "used_topics": [],
    "last_post_date": None,
    "total_posts": 0
}

def load_history():
    """Загружаем историю из файла"""
    global posted_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                posted_history = json.load(f)
            print(f"📚 Загружена история: {len(posted_history['used_topics'])} постов")
        except:
            print("⚠️ Не удалось загрузить историю, начинаем с нуля")

def save_history():
    """Сохраняем историю в файл"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(posted_history, f, ensure_ascii=False, indent=2)

def clean_markdown(text):
    text = re.sub(r"[*]{1,}", " ", text)
    text = re.sub(r"#{1,}\s", " ", text)
    text = re.sub(r"[`]{1,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def is_post_day():
    """Проверяем, нужно ли сегодня публиковать пост (через день)"""
    today = datetime.datetime.now()
    days_passed = (today - START_DATE).days
    return days_passed % 2 == 0

def get_unique_topic():
    """Выбираем тему которая еще не использовалась"""
    # Собираем все доступные темы
    all_available = []
    for category, topics in ALL_TOPICS.items():
        for topic in topics:
            if topic not in posted_history["used_topics"]:
                all_available.append((category, topic))
    
    # Если все темы использованы — начинаем новый круг
    if not all_available:
        print("🔄 Все темы использованы! Начинаем новый круг...")
        posted_history["used_topics"] = []
        save_history()
        # Снова собираем все темы
        for category, topics in ALL_TOPICS.items():
            for topic in topics:
                all_available.append((category, topic))
    
    # Выбираем случайную неиспользованную тему
    category, topic = random.choice(all_available)
    
    # Добавляем в историю
    posted_history["used_topics"].append(topic)
    posted_history["total_posts"] += 1
    save_history()
    
    return category, topic

def get_prompt_for_topic(category, topic):
    """Генерируем промпт на основе категории и темы"""
    prompts = {
        "parsing": f"Напиши пост про то как я делал {topic}. Расскажи про трудности, как их преодолел, покажи пример кода.",
        "python_basics": f"Напиши пост про {topic}. Объясни просто с примером кода до/после.",
        "libraries": f"Напиши пост про библиотеку {topic}. Зачем нужна, основные возможности, простой пример использования.",
        "automation": f"Напиши пост про {topic}. Опиши задачу, решение и сколько времени это экономит.",
        "debugging": f"Напиши пост про {topic}. Расскажи историю с юмором и жизненно.",
        "work_life": f"Напиши личный пост про {topic}. Честно и искренне.",
        "learning": f"Напиши пост про {topic}. Поделись опытом и дай конкретные рекомендации.",
        "tools": f"Напиши пост про инструмент {topic}. Почему использую, плюсы и минусы.",
        "projects": f"Напиши пост про проект: {topic}. Что получилось, что нет, чему научился.",
        "motivation": f"Напиши мотивационный пост про {topic}. Вдохновляюще и честно.",
        "humor": f"Напиши смешной пост про {topic}. С юмором и иронией над собой.",
        "questions": f"Напиши пост-вопрос: {topic}. Заинтересуй аудиторию чтобы отвечали.",
    }
    
    return prompts.get(category, f"Напиши пост про {topic}")

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
            "temperature": 0.8,
            "maxTokens": 900
        },
        "messages": [
            {
                "role": "system",
                "text": """Ты пишешь посты для Telegram канала "Даниил с завода".
Автор — обычный человек который работает на заводе
и после смены изучает Python и AI.

Пиши как личный блог:
- Просто и по-человечески
- С конкретными примерами
- Честно про трудности
- С эмодзи где уместно
- Не слишком длинно (200-400 слов)
- Добавляй код когда нужно
- Задавай вопросы подписчикам"""
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
                "text": "Сделай короткое описание картинки на английском для AI генерации. Максимум 10 слов."
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
                filename = f"image_{datetime.datetime.now().timestamp()}.jpg"
                with open(filename, "wb") as f:
                    f.write(image_data)
                return filename
            else:
                return None

async def publish_daily_post():
    # Проверяем, день ли поста
    if not is_post_day():
        print("📅 Сегодня не день публикации (через день)")
        return
    
    # Проверяем, не публиковали ли сегодня уже
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    if posted_history["last_post_date"] == today_str:
        print("✅ Пост сегодня уже опубликован")
        return
    
    # Выбираем уникальную тему
    category, topic = get_unique_topic()
    print(f"📝 Генерирую пост: [{category}] {topic}")
    
    # Генерируем промпт и текст
    prompt = get_prompt_for_topic(category, topic)
    content = await generate_text(prompt)
    content = clean_markdown(content)
    
    # Добавляем номер дня
    day_number = (datetime.datetime.now() - START_DATE).days + 1
    content = f"День {day_number}. Путь из завода в IT\n\n{content}"
    content += "\n\n📩 @Aslyamov74"
    
    # Генерируем и публикуем картинку
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
            # Удаляем файл картинки
            os.remove(image_path)
        else:
            await bot.send_message(
                chat_id=os.getenv("CHANNEL_ID"),
                text=content
            )
        
        # Обновляем дату последнего поста
        posted_history["last_post_date"] = today_str
        save_history()
        
        print(f"✅ Пост опубликован (День {day_number}, всего постов: {posted_history['total_posts']})")
        
    except Exception as e:
        print(f"❌ Ошибка публикации: {e}")

@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        f"Бот автопостинга работает ✅\n"
        f"Посты публикуются через день в 04:00 UTC\n"
        f"Опубликовано постов: {posted_history['total_posts']}"
    )

@router.message(Command("test_post"))
async def test_post(message: Message):
    await message.answer("🔄 Генерирую пост...")
    await publish_daily_post()
    await message.answer("✅ Готово!")

@router.message(Command("stats"))
async def stats(message: Message):
    days_passed = (datetime.datetime.now() - START_DATE).days
    total_topics = sum(len(topics) for topics in ALL_TOPICS.values())
    used = len(posted_history["used_topics"])
    remaining = total_topics - used
    
    await message.answer(
        f"📊 Статистика:\n\n"
        f"Дней с начала: {days_passed}\n"
        f"Всего тем в пуле: {total_topics}\n"
        f"Использовано: {used}\n"
        f"Осталось: {remaining}\n"
        f"Опубликовано постов: {posted_history['total_posts']}\n"
        f"Последний пост: {posted_history['last_post_date'] or 'не было'}"
    )

@router.message(Command("used_topics"))
async def used_topics_cmd(message: Message):
    """Показывает использованные темы"""
    used = posted_history["used_topics"]
    if not used:
        await message.answer("Пока нет опубликованных постов")
        return
    
    # Показываем последние 20 тем
    recent = used[-20:]
    text = "📋 Последние использованные темы:\n\n"
    for i, topic in enumerate(recent, start=len(used)-19):
        text += f"{i}. {topic}\n"
    
    await message.answer(text)

async def main():
    # Загружаем историю
    load_history()
    
    dp.include_router(router)
    
    scheduler = AsyncIOScheduler()
    
    # Публикация каждый день в 04:00, но внутри проверяем is_post_day()
    scheduler.add_job(
        publish_daily_post,
        'cron',
        hour=4,
        minute=0,
        timezone='UTC'
    )
    
    scheduler.start()
    print("🤖 Бот автопостинга запущен!")
    print(f"📚 Загружено {len(posted_history['used_topics'])} постов из истории")
    print("📅 Посты будут публиковаться через день")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
