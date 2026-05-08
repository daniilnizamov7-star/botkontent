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

START_DATE = datetime.datetime(2026, 3, 5)
HISTORY_FILE = "posted_topics.json"

# ===== СИСТЕМНЫЙ ПРОМПТ — ЛИЧНОСТЬ ДАНИИЛА =====
SYSTEM_PROMPT = """Ты пишешь посты для Telegram канала "Путь с завода в IT" от лица Даниила.

КТО ДАНИИЛ:
- Живёт в Челябинске, работает на заводе посменно
- После смен в свободное время строит IT-продукты
- Женат, есть сын Вадим (первый класс, учит английский)
- Мусульманин, ведёт бизнес по халяль-принципам
- Отдаёт 10% дохода на благотворительность
- Ник в Telegram: @Aslyamov74, бот: @daniil74_bot

ЕГО РЕАЛЬНЫЕ ПРОДУКТЫ (упоминай органично, не рекламно):
- Lesso — PWA для репетиторов (учитель, родитель, ученик). Боль: WhatsApp + тетрадь = хаос
- FoodFlow — система заказов для кафе. Первый клиент — Царская кухня
- Забота — PWA для ветклиники брата в Уфе
- СтройПомощник — для строительных бригад
- Nizamov.tech — зонтичный бренд всех продуктов
- Осознанность — исламское PWA (намазы, зикр, дуа, кибла)
- Ракета — демо для парка аттракционов
- "Паспорт ПК" — HTML-файл с характеристиками ПК для мастеров по сборке

СТИЛЬ ПОСТОВ:
- Пишешь как живой человек, не как блогер-коуч
- Короткие абзацы, разговорный язык
- Конкретные детали (время, место, эмоции)
- Не пафосно, без "давайте разберёмся" и "итого"
- Эмодзи — 2-4 штуки, не больше, не в каждом предложении
- Длина: 150-350 слов
- Иногда ошибки в пунктуации — живой текст
- Заканчивай вопросом к читателям ИЛИ призывом ИЛИ просто мыслью
- НЕ используй markdown: **, ##, ` — только plain text

ЗАПРЕЩЕНО:
- "Привет, друзья!"
- "Итак, сегодня поговорим о..."
- "В заключение хочу сказать"
- Списки с bullet points
- Технические термины без объяснения живым языком"""

# ===== РАСШИРЕННЫЙ ПУЛ ТЕМ =====
ALL_TOPICS = {
    # === ЛИЧНОЕ И ЗАВОД ===
    "work_life": [
        "вернулся со смены в 23:00 и сел за ноутбук — зачем я это делаю",
        "что думают коллеги на заводе когда узнают что я сайты делаю",
        "сын спросил папа ты программист — что ответить",
        "как жена относится к тому что вечера ухожу на проекты",
        "заснул за ноутбуком и проснулся с кодом на лбу",
        "почему не ухожу с завода прямо сейчас — честный ответ",
        "12 часов смена и потом 2 часа кода — как не сломаться",
        "первый раз заплатили за сайт — что почувствовал",
        "страшно ли уходить в IT когда есть семья и ипотека",
        "разговор с мастером на заводе про мои проекты",
    ],

    # === PWA И ЛЕНДИНГИ ===
    "pwa_landing": [
        "что такое PWA и почему делаю именно их а не обычные приложения",
        "лендинг за вечер — реально ли и что из этого получается",
        "почему малый бизнес не хочет платить за сайт — и как это изменить",
        "анимации на лендинге которые делают его живым — без библиотек",
        "как сделать что сайт добавлялся на главный экран телефона",
        "скорость загрузки важнее дизайна — убедился на практике",
        "разница между лендингом и полноценным PWA — когда что нужно",
        "сделал лендинг Ракете — поехал показывать лично",
        "почему выбрал Vercel для деплоя и не жалею",
        "как объяснить клиенту что такое PWA за 30 секунд",
    ],

    # === РЕАЛЬНЫЕ КЛИЕНТЫ И ПРОДАЖИ ===
    "clients_sales": [
        "первый клиент Царская кухня — как получил и что пошло не так",
        "как прийти к клиенту без портфолио и уйти с договором",
        "почему клиент пропал после демо — анализирую что сделал не так",
        "Татьяна из Ракеты не отвечает — что делать дальше",
        "как продавать боль а не функции — на примере Lesso",
        "звонок потенциальному клиенту — волнение и что из этого вышло",
        "почему демо важнее презентации — урок из своего опыта",
        "отказ клиента — как не сломаться и сделать выводы",
        "халяль-бизнес в IT — это ограничение или преимущество",
        "первые 10 тысяч рублей с фриланса — куда потратил",
    ],

    # === ПРОДУКТЫ — LESSO ===
    "lesso": [
        "Lesso — как родилась идея из хаоса репетитора жены",
        "почему репетиторы ведут учёт в WhatsApp и как это менять",
        "делал Lesso для сына — он первый студент на платформе",
        "300 рублей в месяц за порядок в работе репетитора — дорого ли",
        "как три роли в одном приложении — учитель, родитель, ученик",
        "домашнее задание с фото прямо в приложении — зачем это нужно",
        "уведомления в Lesso через Firebase — 3 дня разбирался",
        "конкурент Lesso — это тетрадь и WhatsApp а не Skysmart",
    ],

    # === ПРОДУКТЫ — ДРУГИЕ ===
    "other_products": [
        "Забота — как делал приложение для клиники брата",
        "Осознанность — приложение для намазов которым сам пользуюсь каждый день",
        "FoodFlow — первый настоящий SaaS и первые грабли",
        "СтройПомощник — как объяснил Зауру зачем ему это нужно",
        "Паспорт ПК — идея за 5 минут которая может стать продуктом",
        "зачем делаю столько разных продуктов — объясняю логику",
        "Nizamov.tech — что за зонтичный бренд и зачем он нужен",
    ],

    # === ПК И ЖЕЛЕЗО ===
    "pc_hardware": [
        "собрал ПК клиенту и придумал Паспорт ПК — что это такое",
        "почему мастера по ПК теряют клиентов после сборки",
        "какой ПК взять для разработки на бюджет до 50 тысяч",
        "мой рабочий стол — ноутбук с завода и второй монитор",
        "разница между SSD и HDD которую клиент чувствует сразу",
        "почему важно документировать что установил на ПК клиента",
        "первая сборка ПК — что пошло не так и как починил",
    ],

    # === ТЕХНОЛОГИИ (живо) ===
    "tech_human": [
        "Supabase — объясняю другу на заводе зачем мне это",
        "что такое база данных на примере журнала смен завода",
        "почему не использую React — и когда всё-таки буду",
        "Git спас мой проект ночью — история без лишних деталей",
        "деплой на Vercel за 3 минуты — магия или норма",
        "service worker и почему сайт работает без интернета",
        "Telegram бот за вечер — зачем и как это работает",
        "Supabase Realtime — когда сообщения появляются сами",
        "почему vanilla JS а не фреймворк — мой выбор",
        "Railway вместо VPS — как перенёс ботов и не пожалел",
    ],

    # === ИСЛАМ И ЦЕННОСТИ ===
    "islam_values": [
        "халяль в IT — это не только еда, объясняю принцип",
        "10 процентов с дохода на благотворительность — зачем и как",
        "баракят в работе — когда всё идёт хорошо и не понимаешь почему",
        "делаю Осознанность для себя — и оказалось нужно другим тоже",
        "как не брать риба в бизнесе и не умереть с голоду",
        "ния (намерение) перед проектом — звучит странно работает реально",
        "утренний азкар перед кодом — стало привычкой",
    ],

    # === МОТИВАЦИЯ И РОСТ ===
    "growth": [
        "год назад не знал что такое API — сравниваю себя с собой",
        "провалился на первом фриланс-заказе — что именно пошло не так",
        "каждый день по часу лучше чем выходной марафон — проверено",
        "синдром самозванца когда первый раз назвал себя разработчиком",
        "почему важно публиковать незаконченное — история из своего опыта",
        "сравнение с другими убивает прогресс — научился не сравнивать",
        "через год будешь рад что начал сегодня — банально но правда",
        "три месяца без результата и почему не бросил",
    ],

    # === ЮМОР ===
    "humor": [
        "когда деплоил в продакшн и всё упало в пятницу вечером",
        "клиент сказал сделай как у Apple — за 5000 рублей",
        "когда код работает и ты не понимаешь почему — страшнее чем баг",
        "написал 200 строк потом нашёл готовую функцию в 3 строки",
        "объяснял маме что такое PWA — она сказала молодец сынок",
        "забыл закоммитить и потерял час работы — классика",
        "первое демо клиенту когда всё зависло прямо в момент показа",
    ],

    # === ВОПРОСЫ К АУДИТОРИИ ===
    "questions": [
        "как вы объясняете родным чем занимаетесь в IT",
        "что помогает учиться когда работаешь на основной работе",
        "был ли у вас момент когда хотели всё бросить — что удержало",
        "ваш первый заработок в IT — сколько и за что",
        "как выбираете нишу для продукта или делаете для всех подряд",
        "PWA или нативное приложение — что выбрали бы для своего бизнеса",
        "что читаете или смотрите для развития в IT",
        "как относитесь к идее продавать локальному малому бизнесу",
    ],

    # === PYTHON (оставляем но меньше) ===
    "python_practical": [
        "написал скрипт который экономит мне 2 часа в неделю на заводе",
        "парсер вакансий чтобы следить за рынком IT в Челябинске",
        "автоматическая рассылка отчётов в Telegram — для чего использую",
        "async/await объясняю себе на примере завода с несколькими станками",
        "как я перестал бояться регулярных выражений — одна история",
    ],
}

# ===== ПРОМПТЫ ПО КАТЕГОРИЯМ =====
CATEGORY_PROMPTS = {
    "work_life": "Напиши личный искренний пост про: {topic}. Расскажи конкретную историю с деталями — время, место, эмоции. Без пафоса.",
    "pwa_landing": "Напиши пост про: {topic}. Объясни через реальный опыт, упомяни конкретный проект если уместно. Живо и без технического жаргона без объяснений.",
    "clients_sales": "Напиши пост про: {topic}. Это история с настоящими эмоциями — волнение, провал или победа. Конкретно и честно.",
    "lesso": "Напиши пост про Lesso и тему: {topic}. Расскажи как это связано с реальной болью репетиторов или с личным опытом (сын учится).",
    "other_products": "Напиши пост про: {topic}. Расскажи историю создания или продажи. Живо, с деталями.",
    "pc_hardware": "Напиши пост про: {topic}. Простым языком, как будто объясняешь другу с завода. Упомяни идею Паспорта ПК если уместно.",
    "tech_human": "Напиши пост про: {topic}. Объясни технологию через аналогию из обычной жизни или завода. Не технический мануал — живая история.",
    "islam_values": "Напиши пост про: {topic}. Искренне, без морализаторства. Это личная ценность а не урок для других.",
    "growth": "Напиши мотивационный пост про: {topic}. Честно и конкретно — без коучинговых клише. Из личного опыта.",
    "humor": "Напиши смешной пост про: {topic}. Ирония над собой, конкретная ситуация, живо.",
    "questions": "Напиши пост-вопрос: {topic}. Сначала поделись своим ответом или историей (3-4 предложения), потом спроси подписчиков.",
    "python_practical": "Напиши пост про: {topic}. Покажи реальную пользу для обычного человека. Можно добавить короткий пример кода но главное — зачем это нужно.",
}

# Веса категорий (чтобы технарщина не доминировала)
CATEGORY_WEIGHTS = {
    "work_life": 10,
    "pwa_landing": 10,
    "clients_sales": 10,
    "lesso": 8,
    "other_products": 7,
    "pc_hardware": 6,
    "tech_human": 8,
    "islam_values": 7,
    "growth": 8,
    "humor": 6,
    "questions": 8,
    "python_practical": 5,
}

# Правило: не повторять категорию 2 раза подряд
LAST_CATEGORY_FILE = "last_category.txt"

# ===== СОСТОЯНИЕ =====
posted_history = {
    "used_topics": [],
    "last_post_date": None,
    "total_posts": 0,
    "last_category": None
}

def load_history():
    global posted_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                posted_history = json.load(f)
            print(f"📚 Загружена история: {len(posted_history['used_topics'])} постов")
        except:
            print("⚠️ Не удалось загрузить историю, начинаем с нуля")

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(posted_history, f, ensure_ascii=False, indent=2)

def clean_markdown(text):
    text = re.sub(r"[*]{1,}", " ", text)
    text = re.sub(r"#{1,}\s", " ", text)
    text = re.sub(r"[`]{1,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def is_post_day():
    today = datetime.datetime.now()
    days_passed = (today - START_DATE).days
    return days_passed % 2 == 0

def get_unique_topic():
    """Выбираем тему с учётом весов и без повтора категории подряд"""
    last_cat = posted_history.get("last_category")

    # Собираем доступные темы по категориям
    available_by_cat = {}
    for category, topics in ALL_TOPICS.items():
        if category == last_cat:
            continue  # не повторяем категорию подряд
        unused = [t for t in topics if t not in posted_history["used_topics"]]
        if unused:
            available_by_cat[category] = unused

    # Если совсем ничего нет — сброс истории
    if not available_by_cat:
        print("🔄 Все темы использованы! Начинаем новый круг...")
        posted_history["used_topics"] = []
        save_history()
        for category, topics in ALL_TOPICS.items():
            if category != last_cat:
                available_by_cat[category] = list(topics)

    # Выбор категории с учётом весов
    cats = list(available_by_cat.keys())
    weights = [CATEGORY_WEIGHTS.get(c, 5) for c in cats]
    category = random.choices(cats, weights=weights, k=1)[0]
    topic = random.choice(available_by_cat[category])

    posted_history["used_topics"].append(topic)
    posted_history["last_category"] = category
    posted_history["total_posts"] += 1
    save_history()

    return category, topic

async def generate_text(category, topic):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    prompt_template = CATEGORY_PROMPTS.get(
        category,
        "Напиши живой личный пост про: {topic}"
    )
    prompt = prompt_template.format(topic=topic)

    headers = {
        "Authorization": f"Api-Key {os.getenv('YANDEX_GPT_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{os.getenv('FOLDER_ID')}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.85,
            "maxTokens": 900
        },
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": prompt}
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
        "completionOptions": {"temperature": 0.7, "maxTokens": 80},
        "messages": [
            {
                "role": "system",
                "text": "Сделай короткое описание картинки на английском для AI генерации. Максимум 8 слов. Стиль: реалистичный, тёплый, без текста на картинке."
            },
            {"role": "user", "text": post_text[:300]}
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
            return None

async def publish_daily_post():
    if not is_post_day():
        print("📅 Сегодня не день публикации")
        return

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    if posted_history["last_post_date"] == today_str:
        print("✅ Пост сегодня уже опубликован")
        return

    category, topic = get_unique_topic()
    print(f"📝 Генерирую пост: [{category}] {topic}")

    content = await generate_text(category, topic)
    content = clean_markdown(content)

    day_number = (datetime.datetime.now() - START_DATE).days + 1
    content = f"День {day_number}. Путь с завода в IT\n\n{content}"
    content += "\n\n📩 @Aslyamov74"

    image_prompt = await generate_image_prompt(content)
    image_path = await generate_image(image_prompt)

    try:
        if image_path:
            photo = FSInputFile(image_path)
            await bot.send_photo(
                chat_id=os.getenv("CHANNEL_ID"),
                photo=photo,
                caption=content[:1024]
            )
            os.remove(image_path)
        else:
            await bot.send_message(chat_id=os.getenv("CHANNEL_ID"), text=content)

        posted_history["last_post_date"] = today_str
        save_history()
        print(f"✅ Пост опубликован (День {day_number}, всего: {posted_history['total_posts']})")

    except Exception as e:
        print(f"❌ Ошибка публикации: {e}")

# ===== КОМАНДЫ =====

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

@router.message(Command("force_post"))
async def force_post(message: Message):
    """Принудительно опубликовать пост (игнорирует is_post_day и дату)"""
    category, topic = get_unique_topic()
    await message.answer(f"🔄 Генерирую: [{category}] {topic}")
    content = await generate_text(category, topic)
    content = clean_markdown(content)
    day_number = (datetime.datetime.now() - START_DATE).days + 1
    content = f"День {day_number}. Путь с завода в IT\n\n{content}"
    content += "\n\n📩 @Aslyamov74"
    image_prompt = await generate_image_prompt(content)
    image_path = await generate_image(image_prompt)
    try:
        if image_path:
            photo = FSInputFile(image_path)
            await bot.send_photo(chat_id=os.getenv("CHANNEL_ID"), photo=photo, caption=content[:1024])
            os.remove(image_path)
        else:
            await bot.send_message(chat_id=os.getenv("CHANNEL_ID"), text=content)
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        posted_history["last_post_date"] = today_str
        save_history()
        await message.answer("✅ Опубликовано!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("preview"))
async def preview_post(message: Message):
    """Показать следующий пост БЕЗ публикации в канал"""
    category, topic = get_unique_topic()
    # Откатываем счётчик (preview не считается)
    posted_history["used_topics"].pop()
    posted_history["total_posts"] -= 1
    save_history()
    await message.answer(f"🔍 Превью [{category}]: {topic}\n\nГенерирую...")
    content = await generate_text(category, topic)
    content = clean_markdown(content)
    await message.answer(content)

@router.message(Command("stats"))
async def stats(message: Message):
    days_passed = (datetime.datetime.now() - START_DATE).days
    total_topics = sum(len(topics) for topics in ALL_TOPICS.values())
    used = len(posted_history["used_topics"])
    remaining = total_topics - used

    # Статистика по категориям
    cat_stats = {}
    for topic in posted_history["used_topics"]:
        for cat, topics in ALL_TOPICS.items():
            if topic in topics:
                cat_stats[cat] = cat_stats.get(cat, 0) + 1

    cat_text = "\n".join([f"  {k}: {v}" for k, v in sorted(cat_stats.items(), key=lambda x: -x[1])])

    await message.answer(
        f"📊 Статистика:\n\n"
        f"Дней с начала: {days_passed}\n"
        f"Всего тем: {total_topics}\n"
        f"Использовано: {used}\n"
        f"Осталось: {remaining}\n"
        f"Постов опубликовано: {posted_history['total_posts']}\n"
        f"Последний пост: {posted_history['last_post_date'] or 'не было'}\n"
        f"Последняя категория: {posted_history.get('last_category', '—')}\n\n"
        f"По категориям:\n{cat_text}"
    )

@router.message(Command("topics"))
async def topics_cmd(message: Message):
    used = posted_history["used_topics"]
    if not used:
        await message.answer("Пока нет опубликованных постов")
        return
    recent = used[-20:]
    text = "📋 Последние 20 тем:\n\n"
    for i, topic in enumerate(recent, start=max(1, len(used) - 19)):
        text += f"{i}. {topic}\n"
    await message.answer(text)

async def main():
    load_history()
    dp.include_router(router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(publish_daily_post, 'cron', hour=4, minute=0, timezone='UTC')
    scheduler.start()

    print("🤖 Бот запущен!")
    print(f"📚 История: {len(posted_history['used_topics'])} постов")
    total_topics = sum(len(t) for t in ALL_TOPICS.values())
    print(f"📋 Тем в пуле: {total_topics}")

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
