import os
import json
import time
import asyncio
import re
import uuid
import datetime
from pyrogram import Client
from tqdm import tqdm
from typing import List, Dict, Optional

api_id = 26333656
api_hash = "2c550faf732f3920b062006d9b7dfd55"

# --- Множественные аккаунты ---
ACCOUNTS = [
    {"phone": "+79001234567", "session": "account1"},
    {"phone": "+79001234568", "session": "account2"},
    {"phone": "+79001234569", "session": "account3"},
    # Добавьте до 15 аккаунтов
]

# --- Форматы постов ---
POST_FORMATS = {
    "list": {
        "name": "Список",
        "patterns": [r'\d+\.', r'[-•]', r'во-первых', r'далее'],
        "conditions": ["3+ строк с похожим шаблоном"]
    },
    "story": {
        "name": "История", 
        "patterns": [r'однажды', r'я помню', r'вчера', r'когда-то'],
        "conditions": ["нарратив", "личный рассказ", "временные указания"]
    },
    "analytics": {
        "name": "Аналитика",
        "patterns": [r'по данным', r'рост', r'%', r'исследование'],
        "conditions": ["факты", "цифры", "источники", "графики"]
    },
    "opinion": {
        "name": "Мнение/позиция",
        "patterns": [r'мне кажется', r'по моему мнению', r'я думаю'],
        "conditions": ["субъективные утверждения", "оценка событий"]
    },
    "howto": {
        "name": "Инструкция",
        "patterns": [r'сделай', r'настрой', r'скачай', r'шаг \d+'],
        "conditions": ["последовательные действия", "повелительное наклонение"]
    },
    "news": {
        "name": "Новость",
        "patterns": [r'произошло', r'в \d{4}', r'сегодня', r'по сообщениям'],
        "conditions": ["дата/время", "событие", "краткость"]
    },
    "motivation": {
        "name": "Вдохновение",
        "patterns": [r'ты можешь', r'поверь в себя', r'не сдавайся'],
        "conditions": ["пафос", "мотивационные слова", "призыв к действию"]
    },
    "fun": {
        "name": "Развлечение/юмор",
        "patterns": [r'лол', r'ахаха', r'мем', r'прикол'],
        "conditions": ["шутки", "неформальный стиль", "эмодзи"]
    },
    "quote": {
        "name": "Цитата",
        "patterns": [r'—', r'сказал', r'цитата'],
        "conditions": ["кавычки", "имя автора", "меньше 3 строк"]
    }
}

# --- CTA паттерны ---
CTA_PATTERNS = [
    r'подпишись', r'следи за', r'присоединяйся', r'жми подписаться',
    r'пиши в комменты', r'оцени', r'смотри дальше', r'сохрани',
    r'жми на ссылку', r'а ты как думаешь\?', r'пиши \+ если полезно',
    r'что скажешь\?', r'читай', r'узнай', r'начни', r'перейди',
    r'жми', r'вступай', r'переходи сюда', r'канал', r'бот'
]

# --- Детекция рекламных постов ---
AD_DETECTION = {
    "external_links": [r'https://', r't\.me/', r'@\w+', r'tg://', r'bit\.ly'],
    "brand_mentions": [r'@\w+', r't\.me/\w+', r'переходи сюда', r'канал', r'бот'],
    "cta_phrases": [r'подпишись', r'читай', r'узнай', r'начни', r'перейди', r'жми', r'вступай'],
    "brand_words": [],  # Будет заполнено известными брендами
    "emoji_threshold": 0.1,  # 10% эмодзи
    "caps_threshold": 0.3    # 30% заглавных букв
}

app = Client("userbot_session", api_id=api_id, api_hash=api_hash)

THEMES = {
    "Художество": ["картина", "живопись", "художник", "рисунок", "арт", "галерея"],
    "Литература": ["книга", "поэзия", "роман", "литература", "стих", "писатель"],
    "Кино": ["фильм", "кино", "режиссер", "актер", "сериал", "премьера"],
    "Музыка": ["музыка", "песня", "альбом", "концерт", "группа", "исполнитель"],
}

os.makedirs("images", exist_ok=True)
os.makedirs("results", exist_ok=True)

TASKS_FILE = "tasks.json"
RESULTS_DIR = "results"

# --- SQLAlchemy async setup ---
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from bot.db import (
    SessionLocal, Channel, Post, ChannelSnapshot, PostSnapshot, Base, Account, AccountStatus
)

def detect_post_format(text: str) -> str:
    """Автоматически определяет формат поста"""
    if not text:
        return "other"
    
    text_lower = text.lower()
    lines = text.split('\n')
    
    # Проверяем каждый формат
    for format_key, format_data in POST_FORMATS.items():
        pattern_matches = 0
        condition_matches = 0
        
        # Проверяем паттерны
        for pattern in format_data["patterns"]:
            if re.search(pattern, text_lower):
                pattern_matches += 1
        
        # Проверяем условия
        for condition in format_data["conditions"]:
            if condition in text_lower:
                condition_matches += 1
        
        # Если найдено достаточно совпадений
        if pattern_matches >= 1 and condition_matches >= 1:
            return format_key
    
    return "other"

def extract_cta(text: str) -> Optional[str]:
    """Извлекает CTA из текста поста"""
    if not text:
        return None
    
    lines = text.split('\n')
    # Проверяем последние 1-3 строки
    for i in range(min(3, len(lines))):
        line = lines[-(i+1)].strip()
        for pattern in CTA_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return line
    
    return None

def detect_ad_post(text: str, title: str = None) -> bool:
    """Определяет, является ли пост рекламным"""
    if not text:
        return False
    
    text_lower = text.lower()
    score = 0
    
    # Проверяем внешние ссылки
    for pattern in AD_DETECTION["external_links"]:
        if re.search(pattern, text):
            score += 2
    
    # Проверяем упоминания каналов/ботов
    for pattern in AD_DETECTION["brand_mentions"]:
        if re.search(pattern, text):
            score += 2
    
    # Проверяем CTA фразы
    for pattern in AD_DETECTION["cta_phrases"]:
        if re.search(pattern, text):
            score += 1
    
    # Проверяем количество эмодзи
    emoji_count = len(re.findall(r'[^\w\s]', text))
    if emoji_count / len(text) > AD_DETECTION["emoji_threshold"]:
        score += 1
    
    # Проверяем количество заглавных букв
    caps_count = len(re.findall(r'[А-Я]', text))
    if caps_count / len(text) > AD_DETECTION["caps_threshold"]:
        score += 1
    
    # Проверяем структуру (1 абзац + призыв)
    paragraphs = text.split('\n\n')
    if len(paragraphs) == 2 and extract_cta(paragraphs[-1]):
        score += 2
    
    return score >= 3  # Если 3+ признака - это реклама

def extract_title_and_body(text: str) -> tuple:
    """Разделяет текст на заголовок и основной контент"""
    if not text:
        return None, text
    
    lines = text.split('\n')
    first_line = lines[0].strip()
    
    # Проверяем, является ли первая строка заголовком
    if (len(first_line) < 100 and 
        not re.search(r'[.!?]{2,}', first_line) and
        (first_line.startswith('🔴') or first_line.startswith('🔵') or 
         first_line.startswith('⚡') or first_line[0].isupper() or
         '!' in first_line)):
        
        title = first_line
        body = '\n'.join(lines[1:]).strip()
        return title, body
    
    return None, text

async def save_channel_and_snapshot(chat):
    async with SessionLocal() as session:
        # Проверяем, есть ли канал
        channel_id = str(chat.id)
        channel = await session.get(Channel, channel_id)
        if not channel:
            channel = Channel(
                channel_id=channel_id,
                username=chat.username or f"{chat.id}",
                title=chat.title or chat.first_name or chat.username or str(chat.id),
                description=getattr(chat, 'description', None),
                is_bot_admin=False
            )
            session.add(channel)
            await session.commit()
        
        # Сохраняем snapshot (если есть инфа о подписчиках)
        try:
            snapshot = ChannelSnapshot(
                channel_snapshot_id=str(uuid.uuid4()),
                channel_id=channel_id,
                snapshot_date=datetime.datetime.utcnow(),
                subscribers_count=getattr(chat, 'members_count', None),
                reach_rate=None, avg_reactions=None, avg_reposts=None, avg_post_comments=None,
                new_followers=None, lost_followers=None, silent_users_percent=None, active_users_percent=None,
                posts_count=None, total_views=None, engagement_rate=None, source_info=None,
                notification_percent=None, avg_positive_reactions=None, avg_negative_reactions=None
            )
            session.add(snapshot)
            await session.commit()
        except Exception as e:
            print(f"[userbot] Не удалось сохранить snapshot канала: {e}")

async def save_post_and_snapshot(chat_id, msg):
    async with SessionLocal() as session:
        post_id = f"{chat_id}_{msg.id}"
        
        # Получаем текст поста
        post_text = msg.text or msg.caption or ""
        
        # Разделяем на заголовок и основной текст
        title, body = extract_title_and_body(post_text)
        
        # Определяем формат поста
        format_type = detect_post_format(post_text)
        
        # Извлекаем CTA
        cta = extract_cta(post_text)
        
        # Определяем, является ли рекламным
        is_ad = detect_ad_post(post_text, title)
        
        # Сохраняем пост
        post = await session.get(Post, post_id)
        if not post:
            post = Post(
                post_id=post_id,
                channel_id=str(chat_id),
                posted_at=msg.date,
                title=title,
                body=body,
                is_ad=is_ad,
                media_type='photo' if msg.photo else 'video' if msg.video else 'document' if msg.document else None,
                has_poll=bool(getattr(msg, 'poll', None)),
                format=format_type,
                cta=cta,
                topic=None,  # Можно реализовать автоопределение темы
                tags=None
            )
            session.add(post)
            await session.commit()
        
        # Сохраняем snapshot
        try:
            # Вычисляем ER (engagement rate)
            views = getattr(msg, 'views', 0)
            reactions = msg.reactions.reactions if msg.reactions else []
            total_reactions = sum(r.count for r in reactions)
            er = (total_reactions / views * 100) if views > 0 else 0
            
            snapshot = PostSnapshot(
                id=str(uuid.uuid4()),
                post_id=post_id,
                views_count=views,
                views_info=None,
                reactions=json.dumps({r.emoji: r.count for r in reactions}),
                comments=None,
                forwards=getattr(msg, 'forwards', None),
                forwards_private=None,
                er=er,
                snapshot_date=datetime.datetime.utcnow(),
                is_final=False
            )
            session.add(snapshot)
            await session.commit()
        except Exception as e:
            print(f"[userbot] Не удалось сохранить snapshot поста: {e}")

# --- Управление аккаунтами ---
async def check_account_status(account_id: str) -> bool:
    """Проверяет статус аккаунта"""
    async with SessionLocal() as session:
        account = await session.get(Account, account_id)
        if not account:
            return False
        
        # Проверяем, не забанен ли аккаунт
        if account.status == AccountStatus.Banned:
            return False
        
        # Проверяем, не было ли ошибок
        if account.status == AccountStatus.Error:
            return False
        
        return True

async def update_account_status(account_id: str, status: AccountStatus):
    """Обновляет статус аккаунта"""
    async with SessionLocal() as session:
        account = await session.get(Account, account_id)
        if account:
            account.status = status
            account.last_used_at = datetime.datetime.utcnow()
            await session.commit()

# --- Мониторинг аккаунтов ---
async def monitor_accounts():
    """Мониторинг аккаунтов каждые 24 часа"""
    while True:
        try:
            async with SessionLocal() as session:
                accounts = await session.execute("SELECT * FROM accounts")
                for account in accounts:
                    # Проверяем статус аккаунта
                    is_active = await check_account_status(account.account_id)
                    if not is_active:
                        await update_account_status(account.account_id, AccountStatus.Error)
                        print(f"[monitor] Аккаунт {account.account_id} помечен как неактивный")
            
            # Ждем 24 часа
            await asyncio.sleep(24 * 60 * 60)
        except Exception as e:
            print(f"[monitor] Ошибка мониторинга: {e}")
            await asyncio.sleep(60 * 60)  # Ждем час при ошибке

def safe_truncate(text, max_length):
    """Безопасно обрезает текст"""
    if not text:
        return ""
    return text[:max_length] + "..." if len(text) > max_length else text

def classify_theme(text):
    """Классифицирует тему поста"""
    text_lower = text.lower()
    for theme, keywords in THEMES.items():
        if any(keyword in text_lower for keyword in keywords):
            return theme
    return "Другое"

def load_tasks():
    """Загружает задачи из файла"""
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_tasks(tasks):
    """Сохраняет задачи в файл"""
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def save_result(user_id, channel, stat_text, all_posts):
    """Сохраняет результат анализа"""
    result = {
        "user_id": user_id,
        "channel": channel,
        "stats": stat_text,
        "posts": all_posts,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    filename = f"results/analysis_{user_id}_{channel}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

async def process_task(task):
    """Обрабатывает задачу парсинга"""
    user_id = task.get('user_id')
    channel = task.get('channel')
    
    print(f"[parser] Начинаю парсинг канала: {channel}")
    
    try:
        # Получаем информацию о канале
        chat = await app.get_chat(channel)
        await save_channel_and_snapshot(chat)
        
        # Парсим посты
        posts = []
        async for message in app.get_chat_history(channel, limit=100):
            if message.text or message.caption:
                await save_post_and_snapshot(chat.id, message)
                
                post_data = {
                    "id": message.id,
                    "text": message.text or message.caption or "",
                    "date": message.date.isoformat(),
                    "views": getattr(message, 'views', 0),
                    "reactions": {r.emoji: r.count for r in message.reactions.reactions} if message.reactions else {},
                    "forwards": getattr(message, 'forwards', 0)
                }
                posts.append(post_data)
        
        # Анализируем статистику
        total_views = sum(p['views'] for p in posts)
        total_reactions = sum(sum(p['reactions'].values()) for p in posts)
        avg_views = total_views / len(posts) if posts else 0
        engagement_rate = (total_reactions / total_views * 100) if total_views > 0 else 0
        
        stat_text = f"""
📊 СТАТИСТИКА КАНАЛА: {chat.title}

👥 Подписчики: {getattr(chat, 'members_count', 'Неизвестно')}
📝 Постов проанализировано: {len(posts)}
👀 Общие просмотры: {total_views:,}
❤️ Общие реакции: {total_reactions}
📊 Средние просмотры: {avg_views:,.0f}
🎯 Вовлеченность: {engagement_rate:.2f}%

🔥 ТОП-5 ПОСТОВ ПО ПРОСМОТРАМ:
"""
        
        # Сортируем по просмотрам
        top_posts = sorted(posts, key=lambda x: x['views'], reverse=True)[:5]
        for i, post in enumerate(top_posts, 1):
            text_preview = safe_truncate(post['text'], 100)
            stat_text += f"{i}. {post['views']:,} просмотров | {text_preview}\n"
        
        # Сохраняем результат
        save_result(user_id, channel, stat_text, posts)
        
        print(f"[parser] Парсинг завершен: {channel}")
        return {"success": True, "stats": stat_text, "posts": posts}
        
    except Exception as e:
        print(f"[parser] Ошибка парсинга {channel}: {e}")
        return {"success": False, "error": str(e)}

async def main_loop():
    """Основной цикл парсинга"""
    print("[parser] Запуск парсера...")
    
    # Запускаем мониторинг аккаунтов
    asyncio.create_task(monitor_accounts())
    
    while True:
        try:
            tasks = load_tasks()
            if tasks:
                task = tasks.pop(0)
                save_tasks(tasks)
                
                result = await process_task(task)
                print(f"[parser] Результат: {result}")
            
            await asyncio.sleep(60)  # Проверяем каждую минуту
            
        except Exception as e:
            print(f"[parser] Ошибка в главном цикле: {e}")
            await asyncio.sleep(300)  # Ждем 5 минут при ошибке

if __name__ == "__main__":
    async def runner():
        async with app:
            await main_loop()
    
    asyncio.run(runner()) 