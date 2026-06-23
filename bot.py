import os
import asyncio
import aiohttp
import re
import datetime
import json
import random
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
- После смен строит IT-продукты — сайты, PWA, приложения для малого бизнеса
- Женат, двое детей: сын Вадим (первый класс) и совсем маленькая дочка
- Мусульманин, ведёт бизнес по халяль-принципам, отдаёт 10% на садака
- Ник в Telegram: @Aslyamov74, бот: @daniil74_bot

ЕГО РЕАЛЬНЫЕ ПРОДУКТЫ (упоминай органично, только если уместно):
- Следопыт (sledopyts.ru) — GPS-квесты для корпоративов и городских приключений
- FlowCount — компьютерное зрение, считает посетителей в магазинах и заведениях
- Lesso — PWA для репетиторов, чтоб не вести учёт в WhatsApp
- FoodFlow — система заказов для кафе, первый клиент Царская кухня
- Забота — PWA для ветклиники брата в Уфе
- Намаз / Осознанность — исламские PWA которыми сам пользуется каждый день
- BYTELAB (sborki74.ru) — сборка ПК с партнёром Рифатом
- Nizamov.tech — зонтичный бренд всего

АКТУАЛЬНЫЙ КОНТЕКСТ (это происходит прямо сейчас):
- Написал 7 компаниям про FlowCount и Следопыт — пока тишина, ждёт ответов
- Ищет первых 3 платящих клиентов по 15 000 руб/мес
- 8-BiT (игровой клуб) — главный лид по FlowCount, пока молчат
- Арнест (завод дихлофоса) — корпоративный квест на Следопыте, переговоры зависли
- Думает как найти партнёра по продажам чтоб самому кодить а не продавать

СТИЛЬ — ЭТО ГЛАВНОЕ:
- Пишешь как другу в мессенджер, не как в блог
- Никакого "блогерского" тона — никаких выводов, никаких "итого", никаких поучений
- Короткие предложения. Иногда вообще одно слово на строку.
- Можно начать с середины истории — без вступления
- Эмодзи 1-3 штуки максимум, только если само просится
- Длина: 100-250 слов (короче лучше чем длиннее)
- Можно недосказать — пусть читатель додумает
- Заканчивай либо вопросом либо просто мыслью — без призывов "подписывайтесь"
- НЕ используй markdown: **, ##, ` — только plain text

ЗАПРЕЩЕНО ВСЕГДА:
- "Привет, друзья!" и любые приветствия
- "Итак", "таким образом", "в заключение", "подводя итог"
- "Давайте разберёмся"
- Нумерованные списки и bullet points
- Слово "контент"
- Фраза "путь в IT" в самом тексте (это название канала, не мантра)"""

# ===== РАСШИРЕННЫЙ ПУЛ ТЕМ =====
ALL_TOPICS = {
    # === ЛИЧНОЕ И ЗАВОД ===
    "work_life": [
        "вернулся со смены в 23:00 и сел за ноутбук — зачем я это делаю",
        "что думают коллеги на заводе когда узнают что я сайты делаю",
        "Вадим спросил папа ты программист — что ответить",
        "как жена относится к тому что вечера ухожу на проекты",
        "заснул за ноутбуком и проснулся с кодом на лбу",
        "почему не ухожу с завода прямо сейчас — честный ответ",
        "12 часов смена и потом 2 часа кода — как не сломаться",
        "первый раз заплатили за сайт — что почувствовал",
        "страшно ли менять жизнь когда есть семья",
        "разговор с мастером на заводе про мои проекты",
        "дочка не спит — сижу кодю рядом с кроваткой в тишине",
        "двое детей и завод — когда вообще на проекты время находить",
        "малышка уснула и у меня есть час — как трачу это время",
        "пишу фэнтези-роман для сына — зачем разработчику это нужно",
    ],

    # === ЖИВЫЕ ПРОДАЖИ (хроника в реальном времени) ===
    "live_sales": [
        "написал 7 компаниям про FlowCount и Следопыт — тишина третий день",
        "8-БиТ молчит — продолжаю писать другим или жду",
        "Арнест завис на середине переговоров — что с этим делать",
        "хочу кодить а не продавать — ищу партнёра по продажам",
        "холодное сообщение в Telegram директору магазина — как написал и что ответил",
        "получил первый отказ на этой неделе — дословно что сказали",
        "почему не могу дожать проект до продажи — честно себе признался",
        "7 написал — надо 100 — понял это только сейчас",
        "демо показал — клиент сказал интересно — и пропал",
        "как объяснить FlowCount директору магазина за 2 предложения",
        "Следопыт против GooseChase — американцы берут 649 долларов я пока ноль",
        "первый платящий клиент — когда это случится и что я сделаю",
        "почему легче начать новый проект чем продать готовый",
    ],

    # === СЛЕДОПЫТ ===
    "sledopyt": [
        "Следопыт — как придумал GPS-квесты для корпоративов",
        "квест Путь банки для Арнест — 14 точек по заводу",
        "почему корпоративный тимбилдинг это боль HR-отдела",
        "Следопыт vs GooseChase — в чём реальная разница",
        "как команда из 20 человек проходит квест одновременно",
        "детектив-режим в Следопыте — идея которая мне самому нравится",
        "сезоны и ачивки — зачем это в корпоративном квесте",
    ],

    # === FLOWCOUNT ===
    "flowcount": [
        "FlowCount — как за один вечер собрал систему компьютерного зрения",
        "YOLOv8 на GTX 1660 Super — объясняю другу с завода что это",
        "зачем магазину знать сколько человек зашло — реальные цифры",
        "виртуальная линия которая считает людей — как это работает",
        "8-БиТ — почему игровой клуб идеальный первый клиент для FlowCount",
        "разница между дорогим оборудованием и моим решением на камере",
        "дашборд для клиента — что владелец магазина видит каждый день",
    ],

    # === PWA И ЛЕНДИНГИ ===
    "pwa_landing": [
        "что такое PWA и почему делаю именно их а не обычные приложения",
        "лендинг за вечер — реально ли и что получается",
        "почему малый бизнес не хочет платить за сайт",
        "как сайт добавляется на главный экран телефона",
        "скорость загрузки важнее дизайна — убедился на практике",
        "как объяснить клиенту что такое PWA за 30 секунд",
        "почему выбрал Vercel для деплоя и не жалею",
    ],

    # === ПРОДУКТЫ — ДРУГИЕ ===
    "other_products": [
        "Забота — как делал приложение для клиники брата в Уфе",
        "Намаз PWA — приложение которым сам пользуюсь каждый намаз",
        "FoodFlow — первый настоящий SaaS и первые грабли",
        "Lesso — почему репетиторы ведут учёт в WhatsApp",
        "BYTELAB — как с Рифатом запустили сборку ПК",
        "зачем делаю столько разных продуктов — объясняю логику",
        "Nizamov.tech — что за зонтичный бренд и зачем он нужен",
    ],

    # === ТЕХНОЛОГИИ (живо) ===
    "tech_human": [
        "Supabase — объясняю другу на заводе зачем мне это",
        "что такое база данных на примере журнала смен завода",
        "почему не использую React — и когда всё-таки буду",
        "Git спас мой проект ночью — история",
        "деплой на Vercel за 3 минуты — магия или норма",
        "service worker и почему сайт работает без интернета",
        "Telegram бот за вечер — зачем и как это работает",
        "почему vanilla JS а не фреймворк — мой выбор",
        "компьютерное зрение — объясняю маме что это такое",
    ],

    # === ИСЛАМ И ЦЕННОСТИ ===
    "islam_values": [
        "халяль в IT — это не только еда, объясняю принцип",
        "садака 10% с дохода — зачем и как это работает на практике",
        "баракят в работе — когда всё идёт хорошо и не понимаешь почему",
        "делаю Намаз PWA для себя — и оказалось нужно другим тоже",
        "ния (намерение) перед проектом — звучит странно работает реально",
        "утренний азкар перед кодом — стало привычкой",
        "как отказать клиенту если его бизнес противоречит ценностям",
    ],

    # === МОТИВАЦИЯ И РОСТ ===
    "growth": [
        "год назад не знал что такое API — сравниваю себя с собой",
        "каждый день по часу лучше чем выходной марафон — проверено",
        "синдром самозванца когда первый раз назвал себя разработчиком",
        "сравнение с другими убивает прогресс — научился не сравнивать",
        "три месяца без результата и почему не бросил",
        "новая идея каждую неделю — болезнь или суперсила",
        "дофамин от новой идеи и скука от доведения до конца — как с этим жить",
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

    # === МИНИ-ПРОЕКТЫ И ЭКСПЕРИМЕНТЫ ===
    "mini_projects": [
        "сделал за вечер инструмент для себя — и понял что это уже продукт",
        "мини-PWA за 3 часа — что получается когда не думаешь о монетизации",
        "Электросчёт — смета для электриков прямо в браузере без установки",
        "экстренные службы PWA — кнопки 101 102 103 для пожилых родственников",
        "FitCore — фитнес-приложение которое сам использую между сменами",
        "Следопыт — квест-игра для детей которую делал ради удовольствия",
        "идея мини-продукта которую придумал за завтраком — стоит ли делать",
        "за сколько часов реально собрать MVP — честный хронометраж",
        "почему мини-проекты учат быстрее чем большие",
        "когда мини-проект становится настоящим продуктом — где граница",
        "Can Rush — 3D-игра для завода которую сделал за неделю на Three.js",
        "BYTELAB — как придумали бренд для ПК-мастерской за один вечер",
        "Осознанность как мини-проект для себя который выложил публично",
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
    "work_life": "Напиши пост про: {topic}. Конкретная история — время, место, одна деталь которая делает её живой. Без выводов и морали в конце.",
    "live_sales": "Напиши пост про: {topic}. Это хроника реального момента — что происходит прямо сейчас, что чувствуешь, что неясно. Никаких выводов — только срез момента.",
    "sledopyt": "Напиши пост про Следопыт и тему: {topic}. Расскажи через конкретную историю или деталь. Не рекламируй — просто покажи что за этим стоит.",
    "flowcount": "Напиши пост про FlowCount и тему: {topic}. Объясни просто — как будто другу который вообще не в теме. Можно через аналогию.",
    "pwa_landing": "Напиши пост про: {topic}. Через реальный случай из практики. Коротко, без жаргона без объяснений.",
    "other_products": "Напиши пост про: {topic}. История создания или реального использования. Детали важнее общих слов.",
    "tech_human": "Напиши пост про: {topic}. Объясни через аналогию из обычной жизни или завода. Не инструкция — история.",
    "islam_values": "Напиши пост про: {topic}. Личное, без морализаторства. Не учи — делись.",
    "growth": "Напиши пост про: {topic}. Честно, из конкретного опыта. Никаких коучинговых фраз.",
    "humor": "Напиши смешной пост про: {topic}. Ирония над собой. Конкретная ситуация без объяснений почему это смешно.",
    "questions": "Напиши пост-вопрос: {topic}. Сначала 2-3 предложения от себя — честно, не поучая. Потом вопрос к читателям.",
    "python_practical": "Напиши пост про: {topic}. Реальная польза для обычного человека. Коротко.",
    "mini_projects": "Напиши пост про: {topic}. Что толкнуло на идею, сколько заняло, что получилось. Цифры если есть.",
}

# Веса категорий (чтобы технарщина не доминировала)
CATEGORY_WEIGHTS = {
    "work_life": 10,
    "live_sales": 12,
    "sledopyt": 9,
    "flowcount": 9,
    "pwa_landing": 7,
    "other_products": 6,
    "tech_human": 7,
    "islam_values": 8,
    "growth": 8,
    "humor": 6,
    "questions": 8,
    "python_practical": 4,
    "mini_projects": 6,
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

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                result = await response.json()
                return result["result"]["alternatives"][0]["message"]["text"]
    except Exception as e:
        print(f"❌ Ошибка генерации текста YandexGPT: {e}")
        return None

async def generate_image_prompt(post_text, category="", topic=""):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": f"Api-Key {os.getenv('YANDEX_GPT_API_KEY')}",
        "Content-Type": "application/json"
    }

    context = f"Категория поста: {category}. Тема: {topic}.\n\nТекст поста: {post_text[:400]}"

    data = {
        "modelUri": f"gpt://{os.getenv('FOLDER_ID')}/yandexgpt/latest",
        "completionOptions": {"temperature": 0.7, "maxTokens": 60},
        "messages": [
            {
                "role": "system",
                "text": (
                    "Придумай описание иллюстрации для поста на английском. "
                    "Максимум 10 слов. Картинка должна отражать конкретную суть этого поста — "
                    "не абстракцию, а конкретный образ (человек за ноутбуком ночью, камера над входом в магазин, и тп). "
                    "Стиль: реалистичный, тёплый, без текста на картинке. Только описание, без лишних слов."
                )
            },
            {"role": "user", "text": context}
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=15)) as response:
                result = await response.json()
                return result["result"]["alternatives"][0]["message"]["text"].strip()
    except Exception as e:
        print(f"⚠️ Ошибка генерации промпта картинки: {e}")
        return "developer working late night laptop warm light"

async def generate_image(prompt):
    from urllib.parse import quote
    encoded_prompt = quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&width=1024&height=576&seed={random.randint(1,9999)}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=45)) as response:
                if response.status == 200:
                    image_data = await response.read()
                    if len(image_data) < 5000:  # слишком маленький файл = ошибка
                        print(f"⚠️ Картинка слишком маленькая ({len(image_data)} байт) — возможно ошибка Pollinations")
                        return None
                    filename = f"image_{datetime.datetime.now().timestamp()}.jpg"
                    with open(filename, "wb") as f:
                        f.write(image_data)
                    print(f"🖼 Картинка сохранена: {filename} ({len(image_data)//1024}KB)")
                    return filename
                else:
                    print(f"⚠️ Pollinations вернул статус {response.status}")
                    return None
    except asyncio.TimeoutError:
        print("⚠️ Таймаут генерации картинки (45 сек)")
        return None
    except Exception as e:
        print(f"⚠️ Ошибка генерации картинки: {e}")
        return None

async def post_to_vk(text: str, image_path: str = None) -> bool:
    """Публикует пост в группу ВКонтакте. Возвращает True если успешно."""
    token = os.getenv("VK_ACCESS_TOKEN")
    group_id = os.getenv("VK_GROUP_ID")
    if not token or not group_id:
        print("⚠️ VK не настроен — пропускаем")
        return False

    attachment = None

    # Загружаем фото если есть
    if image_path:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.vk.com/method/photos.getWallUploadServer",
                    params={"group_id": group_id, "access_token": token, "v": "5.199"}
                ) as r:
                    upload_data = await r.json()
                upload_url = upload_data["response"]["upload_url"]

            async with aiohttp.ClientSession() as session:
                with open(image_path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field("photo", f, filename="photo.jpg", content_type="image/jpeg")
                    async with session.post(upload_url, data=form) as r:
                        uploaded = await r.json()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.vk.com/method/photos.saveWallPhoto",
                    params={
                        "group_id": group_id,
                        "photo": uploaded["photo"],
                        "server": uploaded["server"],
                        "hash": uploaded["hash"],
                        "access_token": token,
                        "v": "5.199"
                    }
                ) as r:
                    saved = await r.json()
            photo_obj = saved["response"][0]
            attachment = f"photo{photo_obj['owner_id']}_{photo_obj['id']}"
        except Exception as e:
            print(f"⚠️ Ошибка загрузки фото в VK: {e} — постим без картинки")
            attachment = None

    params = {
        "owner_id": f"-{group_id}",
        "from_group": 1,
        "message": text,
        "access_token": token,
        "v": "5.199"
    }
    if attachment:
        params["attachments"] = attachment

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.vk.com/method/wall.post",
                data=params
            ) as r:
                result = await r.json()
        if "error" in result:
            print(f"❌ VK API ошибка: {result['error']['error_msg']}")
            return False
        print(f"✅ VK: пост опубликован (post_id={result['response']['post_id']})")
        return True
    except Exception as e:
        print(f"❌ Ошибка публикации в VK: {e}")
        return False


# ===== ОЧЕРЕДЬ НА МОДЕРАЦИЮ =====
# pending_post = {"content": str, "image_path": str|None, "day_number": int, "category": str, "topic": str}
pending_post = {}

def make_moderation_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data="mod_approve"),
            InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="mod_regen"),
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать текст", callback_data="mod_edit"),
            InlineKeyboardButton(text="🖼 Новая картинка", callback_data="mod_new_image"),
        ],
        [
            InlineKeyboardButton(text="❌ Пропустить", callback_data="mod_skip"),
        ]
    ])

async def send_for_moderation(category: str, topic: str, is_scheduled: bool = False):
    """Генерирует пост и отправляет на модерацию в личку владельцу."""
    admin_id = os.getenv("ADMIN_CHAT_ID")
    if not admin_id:
        print("⚠️ ADMIN_CHAT_ID не задан — модерация невозможна")
        return

    day_number = (datetime.datetime.now() - START_DATE).days + 1
    content = await generate_text(category, topic)
    if not content:
        await bot.send_message(chat_id=admin_id, text=f"❌ YandexGPT не ответил для темы: [{category}] {topic}\nПопробуй /force_post снова.")
        return
    content = clean_markdown(content)
    content = f"День {day_number}. Путь с завода в IT\n\n{content}"
    content += "\n\n📩 @Aslyamov74"

    image_prompt = await generate_image_prompt(content, category, topic)
    image_path = await generate_image(image_prompt)

    pending_post.clear()
    pending_post.update({
        "content": content,
        "image_path": image_path,
        "day_number": day_number,
        "category": category,
        "topic": topic,
        "is_scheduled": is_scheduled,
    })

    source_label = "⏰ Автопост по расписанию" if is_scheduled else "🔧 Ручной запуск"
    caption = f"{source_label}\nКатегория: {category}\nТема: {topic}\n\n{content}"

    try:
        if image_path:
            photo = FSInputFile(image_path)
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo,
                caption=caption[:1024],
                reply_markup=make_moderation_keyboard()
            )
        else:
            await bot.send_message(
                chat_id=admin_id,
                text=caption,
                reply_markup=make_moderation_keyboard()
            )
        print(f"📬 Пост отправлен на модерацию [{category}]: {topic}")
    except Exception as e:
        print(f"❌ Ошибка отправки на модерацию: {e}")

async def do_publish():
    """Публикует pending_post в канал и ВК."""
    content = pending_post.get("content", "")
    image_path = pending_post.get("image_path")
    day_number = pending_post.get("day_number", 0)

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        if image_path and os.path.exists(image_path):
            photo = FSInputFile(image_path)
            await bot.send_photo(
                chat_id=os.getenv("CHANNEL_ID"),
                photo=photo,
                caption=content[:1024]
            )
            await post_to_vk(content, image_path)
            os.remove(image_path)
        else:
            await bot.send_message(chat_id=os.getenv("CHANNEL_ID"), text=content)
            await post_to_vk(content)

        posted_history["last_post_date"] = today_str
        save_history()
        print(f"✅ Опубликовано (День {day_number})")
        pending_post.clear()
        return True
    except Exception as e:
        print(f"❌ Ошибка публикации: {e}")
        return False

async def publish_daily_post():
    if not is_post_day():
        print("📅 Сегодня не день публикации")
        return

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    if posted_history["last_post_date"] == today_str:
        print("✅ Пост сегодня уже опубликован")
        return

    category, topic = get_unique_topic()
    print(f"📝 Генерирую пост на модерацию: [{category}] {topic}")
    await send_for_moderation(category, topic, is_scheduled=True)

# ===== КОМАНДЫ =====

@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        f"Бот автопостинга работает ✅\n"
        f"Посты публикуются через день в 04:00 UTC\n"
        f"Опубликовано постов: {posted_history['total_posts']}"
    )

@router.message(Command("myid"))
async def myid(message: Message):
    admin_id = os.getenv("ADMIN_CHAT_ID", "не задан")
    await message.answer(
        f"Твой Telegram ID: {message.from_user.id}\n"
        f"ADMIN_CHAT_ID в Railway: {admin_id}\n\n"
        f"{'✅ Совпадают' if str(message.from_user.id) == str(admin_id) else '❌ НЕ совпадают — скопируй твой ID в Railway'}"
    )

@router.message(Command("test_post"))
async def test_post(message: Message):
    await message.answer("🔄 Генерирую пост...")
    await publish_daily_post()
    await message.answer("✅ Готово!")

@router.message(Command("force_post"))
async def force_post(message: Message):
    """Генерирует пост и отправляет на модерацию (игнорирует расписание)"""
    category, topic = get_unique_topic()
    await message.answer(f"🔄 Генерирую на модерацию: [{category}] {topic}")
    await send_for_moderation(category, topic, is_scheduled=False)
    await message.answer("📬 Отправлено на модерацию — проверь личку бота!")

# ===== ОБРАБОТЧИКИ МОДЕРАЦИИ =====

@router.callback_query(lambda c: c.data and c.data.startswith("mod_"))
async def handle_moderation(callback: CallbackQuery):
    action = callback.data
    admin_id = os.getenv("ADMIN_CHAT_ID")

    # Защита: только владелец
    if str(callback.from_user.id) != str(admin_id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    if not pending_post:
        await callback.answer("Нет поста на модерации", show_alert=True)
        return

    if action == "mod_approve":
        await callback.answer("Публикую...")
        ok = await do_publish()
        status = "✅ Опубликовано в канал и ВК!" if ok else "❌ Ошибка при публикации"
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(status)

    elif action == "mod_regen":
        await callback.answer("Перегенерирую...")
        await callback.message.edit_reply_markup(reply_markup=None)
        cat = pending_post.get("category")
        topic = pending_post.get("topic")
        # Удаляем старый файл если есть
        old_img = pending_post.get("image_path")
        if old_img and os.path.exists(old_img):
            os.remove(old_img)
        await callback.message.answer(f"🔄 Перегенерирую: [{cat}] {topic}")
        await send_for_moderation(cat, topic, is_scheduled=pending_post.get("is_scheduled", False))

    elif action == "mod_new_image":
        await callback.answer("Генерирую новую картинку...")
        old_img = pending_post.get("image_path")
        if old_img and os.path.exists(old_img):
            os.remove(old_img)
        content = pending_post.get("content", "")
        cat = pending_post.get("category", "")
        topic = pending_post.get("topic", "")
        image_prompt = await generate_image_prompt(content, cat, topic)
        new_image = await generate_image(image_prompt)
        pending_post["image_path"] = new_image
        await callback.message.edit_reply_markup(reply_markup=None)
        caption = f"🖼 Новая картинка\nКатегория: {cat}\nТема: {topic}\n\n{content}"
        if new_image:
            photo = FSInputFile(new_image)
            await callback.message.answer_photo(
                photo=photo,
                caption=caption[:1024],
                reply_markup=make_moderation_keyboard()
            )
        else:
            await callback.message.answer(caption, reply_markup=make_moderation_keyboard())

    elif action == "mod_edit":
        await callback.answer()
        pending_post["awaiting_edit"] = True
        await callback.message.answer(
            "✏️ Отправь новый текст поста следующим сообщением.\n"
            "(Без заголовка «День N» — он добавится автоматически)"
        )

    elif action == "mod_skip":
        await callback.answer("Пропущено")
        old_img = pending_post.get("image_path")
        if old_img and os.path.exists(old_img):
            os.remove(old_img)
        pending_post.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("❌ Пост пропущен. Тема уже списана из пула.")

@router.message(lambda m: pending_post.get("awaiting_edit") and str(m.from_user.id) == str(os.getenv("ADMIN_CHAT_ID")))
async def handle_edit_text(message: Message):
    """Принимает отредактированный текст поста."""
    day_number = pending_post.get("day_number", (datetime.datetime.now() - START_DATE).days + 1)
    new_content = f"День {day_number}. Путь с завода в IT\n\n{message.text}"
    new_content += "\n\n📩 @Aslyamov74"
    pending_post["content"] = new_content
    pending_post["awaiting_edit"] = False

    image_path = pending_post.get("image_path")
    cat = pending_post.get("category", "")
    topic = pending_post.get("topic", "")
    caption = f"✏️ Отредактировано\nКатегория: {cat}\nТема: {topic}\n\n{new_content}"

    if image_path and os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await message.answer_photo(
            photo=photo,
            caption=caption[:1024],
            reply_markup=make_moderation_keyboard()
        )
    else:
        await message.answer(caption, reply_markup=make_moderation_keyboard())

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
