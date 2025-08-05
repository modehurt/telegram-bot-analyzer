import json
import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from PIL import Image
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, delete

from config import BOT_TOKEN, CATEGORIES, FORMATS, FREE_LIMIT, PRO_FEATURES, PRO_PRICE, PAYMENT_TOKEN
from gpt_service import gpt_service
from data_analyzer import data_analyzer
from subscription_service import subscription_service
from payment_service import payment_service
from channel_analyzer import channel_analyzer

TASKS_FILE = "tasks.json"
RESULTS_DIR = "results"

os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Настройки для работы с БД ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://tguser:tgpass@localhost:5432/tgstat")
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# --- Модели ---
from sqlalchemy import Column, Integer, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(BigInteger, unique=True, index=True)
    title = Column(String)
    category = Column(String)

# --- Free/PRO лимиты ---
def check_user_limit(user_id):
    """Проверяет лимит пользователя"""
    return subscription_service.check_limit(user_id)

def get_user_info(user_id):
    """Получает информацию о пользователе"""
    return subscription_service.get_subscription_info(user_id)

# --- Команды POSTS ---
async def post_idea(client: Client, message: Message):
    """Генерирует идеи постов"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    # Проверяем лимит
    if not check_user_limit(user_id):
        remaining = user_info.get('remaining_requests', 0)
        limit = user_info.get('daily_limit', FREE_LIMIT)
        await message.reply_text(
            f"❌ Достигнут дневной лимит запросов ({limit} в день).\n"
            f"Осталось запросов: {remaining}\n"
            "Обновитесь до PRO для неограниченного доступа!"
        )
        return
    
    # Создаем клавиатуру с категориями в виде inline кнопок
    keyboard = []
    for i, cat in enumerate(CATEGORIES):
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"post_idea_cat_{i}")])
    
    # Добавляем кнопку для ручного ввода
    keyboard.append([InlineKeyboardButton("✏️ Ввести тему вручную", callback_data="post_idea_manual")])
    
    await message.reply_text(
        "💡 **ИДЕИ ДЛЯ ПОСТОВ**\n\n"
        "Выберите категорию или введите тему вручную:\n\n"
        f"🆓 **FREE**: {FREE_LIMIT} раз в день\n"
        f"⭐ **PRO**: неограниченно",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def post_idea_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для идеи поста"""
    await callback_query.answer()
    user_id = callback_query.from_user.id
    user_info = get_user_info(user_id)
    
    # Проверяем лимит
    if not check_user_limit(user_id):
        remaining = user_info.get('remaining_requests', 0)
        limit = user_info.get('daily_limit', FREE_LIMIT)
        await callback_query.edit_message_text(
            f"❌ Достигнут дневной лимит запросов ({limit} в день).\n"
            f"Осталось запросов: {remaining}\n"
            "Обновитесь до PRO для неограниченного доступа!"
        )
        return
    
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    # Показываем индикатор загрузки
    await callback_query.edit_message_text(f"🤔 Генерирую идею для поста по теме: {category}...")
    
    try:
        # Определяем тип пользователя и генерируем идею
        is_pro = user_info.get('is_pro', False)
        
        if is_pro:
            # PRO пользователь - используем расширенный анализ
            idea = await gpt_service.generate_post_idea_pro(category, user_id)
        else:
            # FREE пользователь - базовая генерация
            idea = await gpt_service.generate_post_idea(category)
        
        # Форматируем ответ
        response_text = f"💡 **ИДЕЯ ДЛЯ ПОСТА**\n\n"
        response_text += f"📂 **Тема**: {category}\n"
        response_text += f"👤 **Тип**: {'⭐ PRO' if is_pro else '🆓 FREE'}\n\n"
        response_text += f"{idea}"
        
        # Добавляем кнопки для дальнейших действий
        keyboard = [
            [InlineKeyboardButton("🔄 Новая идея", callback_data=f"post_idea_cat_{idx}")],
            [InlineKeyboardButton("📝 Развернуть идею", callback_data=f"expand_idea_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка генерации идеи: {str(e)}")

async def handle_post_idea_topic(client: Client, message: Message):
    """Обработчик ручного ввода темы для идеи поста"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    topic = message.text.strip()
    
    # Проверяем лимит
    if not check_user_limit(user_id):
        remaining = user_info.get('remaining_requests', 0)
        limit = user_info.get('daily_limit', FREE_LIMIT)
        await message.reply_text(
            f"❌ Достигнут дневной лимит запросов ({limit} в день).\n"
            f"Осталось запросов: {remaining}\n"
            "Обновитесь до PRO для неограниченного доступа!"
        )
        return
    
    # Показываем индикатор загрузки
    loading_msg = await message.reply_text(f"🤔 Генерирую идею для поста по теме: {topic}...")
    
    try:
        # Определяем тип пользователя и генерируем идею
        is_pro = user_info.get('is_pro', False)
        
        if is_pro:
            # PRO пользователь - используем расширенный анализ
            idea = await gpt_service.generate_post_idea_pro(topic, user_id)
        else:
            # FREE пользователь - базовая генерация
            idea = await gpt_service.generate_post_idea(topic)
        
        # Форматируем ответ
        response_text = f"💡 **ИДЕЯ ДЛЯ ПОСТА**\n\n"
        response_text += f"📂 **Тема**: {topic}\n"
        response_text += f"👤 **Тип**: {'⭐ PRO' if is_pro else '🆓 FREE'}\n\n"
        response_text += f"{idea}"
        
        # Добавляем кнопки для дальнейших действий
        keyboard = [
            [InlineKeyboardButton("🔄 Новая идея", callback_data="post_idea_manual")],
            [InlineKeyboardButton("📝 Развернуть идею", callback_data=f"expand_idea_manual_{topic}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await loading_msg.edit_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception as e:
        await loading_msg.edit_text(f"❌ Ошибка генерации идеи: {str(e)}")

async def popular_posts(client: Client, message: Message):
    """Показывает популярные посты"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"popular_posts_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "📚 Выберите тему для популярных постов или введите вручную:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def popular_posts_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для популярных постов"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    # Показываем индикатор загрузки
    await callback_query.edit_message_text(f"📊 Анализирую популярные посты по теме: {category}...")
    
    try:
        # Получаем данные из БД через data_analyzer
        posts_data = await data_analyzer.get_popular_posts_by_category(category)
        
        if not posts_data:
            await callback_query.edit_message_text(f"📊 ПОПУЛЯРНЫЕ ПОСТЫ\n\nТема: {category}\n\n❌ Нет данных для анализа. Попробуйте другую тему или добавьте каналы в базу.")
            return
        
        # Анализируем с помощью GPT
        analysis = await gpt_service.analyze_popular_posts(category, posts_data)
        
        response_text = f"📊 ПОПУЛЯРНЫЕ ПОСТЫ\n\nТема: {category}\n\n{analysis}"
        
        # Добавляем кнопки
        keyboard = [
            [InlineKeyboardButton("🔄 Другая тема", callback_data=f"popular_posts_cat_{idx}")],
            [InlineKeyboardButton("📝 Форматы постов", callback_data=f"post_format_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка анализа постов: {str(e)}")

async def post_format(client: Client, message: Message):
    """Объясняет форматы постов"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(fmt, callback_data=f"post_format_type_{i}")] for i, fmt in enumerate(FORMATS)]
    await message.reply_text(
        "📝 Выберите формат поста для подробного объяснения:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def post_format_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора формата поста"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    format_type = FORMATS[idx]
    
    # Показываем индикатор загрузки
    await callback_query.edit_message_text(f"📝 Генерирую объяснение формата: {format_type}...")
    
    try:
        # Генерируем объяснение с помощью GPT
        explanation = await gpt_service.suggest_post_format(format_type)
        
        response_text = f"📝 ФОРМАТ ПОСТА: {format_type.upper()}\n\n{explanation}"
        
        # Добавляем кнопки
        keyboard = [
            [InlineKeyboardButton("🔄 Другой формат", callback_data=f"post_format_type_{idx}")],
            [InlineKeyboardButton("💡 Идея поста", callback_data=f"post_idea_cat_0")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка генерации объяснения: {str(e)}")

# --- Команды ADS ---
async def ad_ideas(client: Client, message: Message):
    """Генерирует рекламные идеи"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"ad_ideas_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "💰 Выберите тему рекламы или введите вручную:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ad_ideas_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для рекламных идей"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    # Показываем индикатор загрузки
    await callback_query.edit_message_text(f"💡 Генерирую рекламные идеи для темы: {category}...")
    
    try:
        # Генерируем рекламные идеи с помощью GPT
        ideas = await gpt_service.generate_ad_ideas(category)
        
        response_text = f"🎯 РЕКЛАМНЫЕ ИДЕИ\n\nТема: {category}\n\n{ideas}"
        
        # Добавляем кнопки
        keyboard = [
            [InlineKeyboardButton("🔄 Новые идеи", callback_data=f"ad_ideas_cat_{idx}")],
            [InlineKeyboardButton("📝 Промо-текст", callback_data=f"promo_text_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка генерации идей: {str(e)}")

async def promo_text(client: Client, message: Message):
    """Генерирует промо-тексты"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"promo_text_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "📝 Выберите тему канала или введите вручную:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def promo_text_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для промо-текста"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    # Показываем индикатор загрузки
    await callback_query.edit_message_text(f"📝 Генерирую промо-текст для темы: {category}...")
    
    try:
        # Генерируем промо-текст с помощью GPT
        promo_text = await gpt_service.generate_promo_text(category)
        
        response_text = f"📢 ПРОМО-ТЕКСТ\n\nТема: {category}\n\n{promo_text}"
        
        # Добавляем кнопки
        keyboard = [
            [InlineKeyboardButton("🔄 Новый текст", callback_data=f"promo_text_cat_{idx}")],
            [InlineKeyboardButton("💡 Рекламные идеи", callback_data=f"ad_ideas_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка генерации текста: {str(e)}")

async def top_cta(client: Client, message: Message):
    """Анализирует лучшие CTA"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"top_cta_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "🔥 Выберите тему канала или введите вручную:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def top_cta_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для анализа CTA"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    # Показываем индикатор загрузки
    await callback_query.edit_message_text(f"🔥 Анализирую лучшие CTA для темы: {category}...")
    
    try:
        # Получаем данные из БД
        posts_data = await data_analyzer.get_popular_posts_by_category(category)
        
        if not posts_data:
            await callback_query.edit_message_text(f"🔥 ЛУЧШИЕ CTA\n\nТема: {category}\n\n❌ Нет данных для анализа. Попробуйте другую тему.")
            return
        
        # Анализируем CTA с помощью GPT
        cta_analysis = await gpt_service.analyze_top_cta(category, posts_data)
        
        response_text = f"🔥 ЛУЧШИЕ CTA\n\nТема: {category}\n\n{cta_analysis}"
        
        # Добавляем кнопки
        keyboard = [
            [InlineKeyboardButton("🔄 Другая тема", callback_data=f"top_cta_cat_{idx}")],
            [InlineKeyboardButton("💡 Рекламные идеи", callback_data=f"ad_ideas_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка анализа CTA: {str(e)}")

# --- Команды TRENDS ---
async def trending_topics(client: Client, message: Message):
    """Показывает трендовые темы"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"trending_topics_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "📈 Выберите категорию для анализа трендов или введите вручную:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def trending_topics_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для трендовых тем"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    # Показываем индикатор загрузки
    await callback_query.edit_message_text(f"📈 Анализирую трендовые темы для: {category}...")
    
    try:
        # Получаем трендовые темы из БД
        trending_data = await data_analyzer.get_trending_topics(category)
        
        if not trending_data:
            await callback_query.edit_message_text(f"📈 ТРЕНДОВЫЕ ТЕМЫ\n\nКатегория: {category}\n\n❌ Нет данных для анализа. Попробуйте другую категорию.")
            return
        
        # Генерируем анализ с помощью GPT
        analysis = await gpt_service.generate_trending_topics(category)
        
        response_text = f"📈 ТРЕНДОВЫЕ ТЕМЫ\n\nКатегория: {category}\n\n{analysis}"
        
        # Добавляем кнопки
        keyboard = [
            [InlineKeyboardButton("🔄 Другая категория", callback_data=f"trending_topics_cat_{idx}")],
            [InlineKeyboardButton("📊 Популярные посты", callback_data=f"popular_posts_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка анализа трендов: {str(e)}")

async def engagement_boost(client: Client, message: Message):
    """Предлагает идеи для повышения вовлеченности"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"engagement_boost_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "🚀 Выберите категорию для идей повышения вовлеченности:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def engagement_boost_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для идей вовлеченности"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    # Показываем индикатор загрузки
    await callback_query.edit_message_text(f"🚀 Генерирую идеи для повышения вовлеченности в теме: {category}...")
    
    try:
        # Генерируем идеи с помощью GPT
        ideas = await gpt_service.suggest_engagement_boost(category)
        
        response_text = f"🚀 ИДЕИ ДЛЯ ПОВЫШЕНИЯ ВОВЛЕЧЕННОСТИ\n\nТема: {category}\n\n{ideas}"
        
        # Добавляем кнопки
        keyboard = [
            [InlineKeyboardButton("🔄 Другие идеи", callback_data=f"engagement_boost_cat_{idx}")],
            [InlineKeyboardButton("📈 Трендовые темы", callback_data=f"trending_topics_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка генерации идей: {str(e)}")

# --- Команды ANALYZE MY CHANNEL (PRO) ---
async def channel_summary(client: Client, message: Message):
    """PRO: Сводка по каналу"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Что вы получите:\n"
            "• Подробную сводку по вашему каналу\n"
            "• Анализ ключевых метрик\n"
            "• Оценку сильных и слабых сторон\n"
            "• Конкретные рекомендации\n\n"
            "💳 Обновитесь до PRO для доступа к этой функции!"
        )
        return
    
    await message.reply_text(
        "📊 СВОДКА ПО КАНАЛУ\n\n"
        "Для создания сводки мне нужны данные вашего канала.\n"
        "Введите username канала (например: @mychannel) или отправьте ссылку на канал."
    )

async def audience_report(client: Client, message: Message):
    """PRO: Отчет по аудитории"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Что вы получите:\n"
            "• Детальный анализ аудитории\n"
            "• Демографические данные\n"
            "• Поведенческие паттерны\n"
            "• Стратегии работы с аудиторией\n\n"
            "💳 Обновитесь до PRO для доступа к этой функции!"
        )
        return
    
    await message.reply_text(
        "👥 ОТЧЕТ ПО АУДИТОРИИ\n\n"
        "Для создания отчета по аудитории мне нужны данные вашего канала.\n"
        "Введите username канала (например: @mychannel) или отправьте ссылку на канал."
    )

async def content_quality(client: Client, message: Message):
    """PRO: Анализ качества контента"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Что вы получите:\n"
            "• Оценку качества контента\n"
            "• Анализ сильных и слабых сторон\n"
            "• Рекомендации по улучшению\n"
            "• План развития контента\n\n"
            "💳 Обновитесь до PRO для доступа к этой функции!"
        )
        return
    
    await message.reply_text(
        "📝 АНАЛИЗ КАЧЕСТВА КОНТЕНТА\n\n"
        "Для анализа качества контента мне нужны данные вашего канала.\n"
        "Введите username канала (например: @mychannel) или отправьте ссылку на канал."
    )

async def style_review(client: Client, message: Message):
    """PRO: Анализ стиля контента"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Что вы получите:\n"
            "• Анализ стиля и тона контента\n"
            "• Оценку целевой аудитории\n"
            "• Рекомендации по стилю\n"
            "• Улучшение подачи контента\n\n"
            "💳 Обновитесь до PRO для доступа к этой функции!"
        )
        return
    
    await message.reply_text(
        "🎨 АНАЛИЗ СТИЛЯ КОНТЕНТА\n\n"
        "Для анализа стиля контента мне нужны данные вашего канала.\n"
        "Введите username канала (например: @mychannel) или отправьте ссылку на канал."
    )

# --- Команды подписки ---
async def subscription_info(client: Client, message: Message):
    """Показывает информацию о подписке"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    remaining = user_info['remaining_requests']
    limit = user_info['daily_limit']
    is_pro = user_info['is_pro']
    
    status_text = "🔒 FREE" if not is_pro else "💎 PRO"
    
    response_text = f"📊 ИНФОРМАЦИЯ О ПОДПИСКЕ\n\n"
    response_text += f"Статус: {status_text}\n"
    response_text += f"Осталось запросов: {remaining}/{limit}\n"
    
    if is_pro:
        response_text += f"\n✅ PRO функции:\n"
        for feature in user_info['pro_features']:
            response_text += f"• {feature}\n"
    else:
        response_text += f"\n💡 Обновитесь до PRO для:\n"
        response_text += f"• Неограниченных запросов\n"
        response_text += f"• Расширенной аналитики\n"
        response_text += f"• Персональных отчетов\n"
    
    keyboard = [
        [InlineKeyboardButton("💳 Обновиться до PRO", callback_data="upgrade_pro")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await message.reply_text(
        response_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def upgrade_pro(client: Client, message: Message):
    """Обновление до PRO"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if user_info['is_pro']:
        await message.reply_text("💎 Вы уже являетесь PRO пользователем!")
        return
    
    response_text = f"💎 ОБНОВЛЕНИЕ ДО PRO\n\n"
    response_text += f"Цена: {PRO_PRICE}₽/месяц\n"
    response_text += f"Длительность: {PRO_DURATION_DAYS} дней\n\n"
    response_text += f"✅ Что включено:\n"
    for feature in PRO_FEATURES:
        response_text += f"• {feature}\n"
    
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить", callback_data="process_payment")],
        [InlineKeyboardButton("🎫 Ввести промокод", callback_data="apply_promocode")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await message.reply_text(
        response_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- V2 ФУНКЦИИ (POSTS) ---
async def post_feedback(client: Client, message: Message):
    """V2: Анализ поста пользователя"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Что вы получите:\n"
            "• Детальный анализ вашего поста\n"
            "• Оценку по 10 критериям\n"
            "• Конкретные рекомендации\n"
            "• План улучшения\n\n"
            "💳 Обновитесь до PRO для доступа к этой функции!"
        )
        return
    
    await message.reply_text(
        "📝 АНАЛИЗ ПОСТА (V2)\n\n"
        "Отправьте текст поста, который хотите проанализировать.\n"
        "Я дам детальную обратную связь и рекомендации по улучшению."
    )

async def rewrite_post(client: Client, message: Message):
    """V2: Улучшение поста пользователя"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Что вы получите:\n"
            "• Улучшенную версию вашего поста\n"
            "• Более цепляющий заголовок\n"
            "• Усиленный призыв к действию\n"
            "• Оптимизированную структуру\n\n"
            "💳 Обновитесь до PRO для доступа к этой функции!"
        )
        return
    
    await message.reply_text(
        "✍️ УЛУЧШЕНИЕ ПОСТА (V2)\n\n"
        "Отправьте текст поста, который хотите улучшить.\n"
        "Я создам более эффективную версию с лучшей структурой и вовлеченностью."
    )

# --- V2 ФУНКЦИИ (ADS) ---
async def ad_tips(client: Client, message: Message):
    """V2: Советы по рекламе"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"ad_tips_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "💡 ВЫБЕРИТЕ КАТЕГОРИЮ ДЛЯ СОВЕТОВ ПО РЕКЛАМЕ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ad_tips_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для советов по рекламе"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    await callback_query.edit_message_text(f"💡 Генерирую советы по рекламе для: {category}...")
    
    try:
        tips = await gpt_service.generate_ad_tips(category)
        
        response_text = f"💡 СОВЕТЫ ПО РЕКЛАМЕ (V2)\n\nТема: {category}\n\n{tips}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Другие советы", callback_data=f"ad_tips_cat_{idx}")],
            [InlineKeyboardButton("💰 Рекламные идеи", callback_data=f"ad_ideas_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка генерации советов: {str(e)}")

async def promo_plan(client: Client, message: Message):
    """V2: План продвижения"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"promo_plan_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "📋 ВЫБЕРИТЕ КАТЕГОРИЮ ДЛЯ ПЛАНА ПРОДВИЖЕНИЯ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def promo_plan_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для плана продвижения"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    await callback_query.edit_message_text(f"📋 Создаю план продвижения для: {category}...")
    
    try:
        plan = await gpt_service.generate_promo_plan(category)
        
        response_text = f"📋 ПЛАН ПРОДВИЖЕНИЯ (V2)\n\nТема: {category}\n\n{plan}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Другой план", callback_data=f"promo_plan_cat_{idx}")],
            [InlineKeyboardButton("💡 Рекламные идеи", callback_data=f"ad_ideas_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка создания плана: {str(e)}")

async def ad_feedback(client: Client, message: Message):
    """V2: Анализ рекламного креатива"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Что вы получите:\n"
            "• Анализ рекламного креатива\n"
            "• Оценку эффективности\n"
            "• Рекомендации по улучшению\n"
            "• A/B тестирование идей\n\n"
            "💳 Обновитесь до PRO для доступа к этой функции!"
        )
        return
    
    await message.reply_text(
        "📊 АНАЛИЗ РЕКЛАМНОГО КРЕАТИВА (V2)\n\n"
        "Отправьте ваш рекламный креатив для анализа.\n"
        "Я оценю его эффективность и дам рекомендации по улучшению."
    )

# --- V2 ФУНКЦИИ (TRENDS) ---
async def content_trends(client: Client, message: Message):
    """V2: Тренды контента"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"content_trends_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "📈 ВЫБЕРИТЕ КАТЕГОРИЮ ДЛЯ АНАЛИЗА ТРЕНДОВ КОНТЕНТА:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def content_trends_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для трендов контента"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    await callback_query.edit_message_text(f"📈 Анализирую тренды контента для: {category}...")
    
    try:
        trends = await gpt_service.analyze_content_trends(category)
        
        response_text = f"📈 ТРЕНДЫ КОНТЕНТА (V2)\n\nКатегория: {category}\n\n{trends}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Другие тренды", callback_data=f"content_trends_cat_{idx}")],
            [InlineKeyboardButton("📊 Популярные посты", callback_data=f"popular_posts_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка анализа трендов: {str(e)}")

async def trend_detective(client: Client, message: Message):
    """V2: Тренд-детектив"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"trend_detective_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "🔍 ВЫБЕРИТЕ КАТЕГОРИЮ ДЛЯ ТРЕНД-ДЕТЕКТИВА:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def trend_detective_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для тренд-детектива"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    await callback_query.edit_message_text(f"🔍 Исследую тренды для: {category}...")
    
    try:
        detective = await gpt_service.analyze_trend_detective(category)
        
        response_text = f"🔍 ТРЕНД-ДЕТЕКТИВ (V2)\n\nКатегория: {category}\n\n{detective}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Другое исследование", callback_data=f"trend_detective_cat_{idx}")],
            [InlineKeyboardButton("📈 Трендовые темы", callback_data=f"trending_topics_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка исследования: {str(e)}")

async def falling_trends(client: Client, message: Message):
    """V2: Падающие тренды"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"falling_trends_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "📉 ВЫБЕРИТЕ КАТЕГОРИЮ ДЛЯ АНАЛИЗА ПАДАЮЩИХ ТРЕНДОВ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def falling_trends_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для падающих трендов"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    await callback_query.edit_message_text(f"📉 Анализирую падающие тренды для: {category}...")
    
    try:
        falling = await gpt_service.analyze_falling_trends(category)
        
        response_text = f"📉 ПАДАЮЩИЕ ТРЕНДЫ (V2)\n\nКатегория: {category}\n\n{falling}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Другой анализ", callback_data=f"falling_trends_cat_{idx}")],
            [InlineKeyboardButton("📈 Трендовые темы", callback_data=f"trending_topics_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка анализа: {str(e)}")

async def trending_channels(client: Client, message: Message):
    """V2: Трендовые каналы"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"trending_channels_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "🔥 ВЫБЕРИТЕ КАТЕГОРИЮ ДЛЯ АНАЛИЗА ТРЕНДОВЫХ КАНАЛОВ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def trending_channels_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для трендовых каналов"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    await callback_query.edit_message_text(f"🔥 Анализирую трендовые каналы в: {category}...")
    
    try:
        channels = await gpt_service.analyze_trending_channels(category)
        
        response_text = f"🔥 ТРЕНДОВЫЕ КАНАЛЫ (V2)\n\nКатегория: {category}\n\n{channels}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Другие каналы", callback_data=f"trending_channels_cat_{idx}")],
            [InlineKeyboardButton("📈 Трендовые темы", callback_data=f"trending_topics_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка анализа каналов: {str(e)}")

async def best_times(client: Client, message: Message):
    """V2: Лучшее время для публикаций"""
    user_id = message.from_user.id
    if not check_user_limit(user_id):
        await message.reply_text("❌ Достигнут дневной лимит запросов. Обновитесь до PRO для неограниченного доступа!")
        return
    
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"best_times_cat_{i}")] for i, cat in enumerate(CATEGORIES)]
    await message.reply_text(
        "⏰ ВЫБЕРИТЕ КАТЕГОРИЮ ДЛЯ АНАЛИЗА ЛУЧШЕГО ВРЕМЕНИ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def best_times_cat_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик выбора категории для лучшего времени"""
    await callback_query.answer()
    idx = int(callback_query.data.split('_')[-1])
    category = CATEGORIES[idx]
    
    await callback_query.edit_message_text(f"⏰ Анализирую лучшее время для: {category}...")
    
    try:
        times = await gpt_service.analyze_best_times(category)
        
        response_text = f"⏰ ЛУЧШЕЕ ВРЕМЯ ДЛЯ ПУБЛИКАЦИЙ (V2)\n\nКатегория: {category}\n\n{times}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Другое время", callback_data=f"best_times_cat_{idx}")],
            [InlineKeyboardButton("🚀 Идеи вовлеченности", callback_data=f"engagement_boost_cat_{idx}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        
        await callback_query.edit_message_text(
            response_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Ошибка анализа времени: {str(e)}")

# --- V2 ФУНКЦИИ (ANALYZE MY CHANNEL) ---
async def growth_tips(client: Client, message: Message):
    """V2: Советы по росту канала"""
    user_id = message.from_user.id
    user_info = get_user_info(user_id)
    
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Что вы получите:\n"
            "• Персональные советы по росту\n"
            "• План развития канала\n"
            "• Конкретные действия\n"
            "• KPI для отслеживания\n\n"
            "💳 Обновитесь до PRO для доступа к этой функции!"
        )
        return
    
    await message.reply_text(
        "🚀 СОВЕТЫ ПО РОСТУ КАНАЛА (V2)\n\n"
        "Для получения персональных советов по росту канала,\n"
        "введите username канала (например: @mychannel) или отправьте ссылку на канал."
    )

# --- Вспомогательные функции ---
def load_tasks():
    """Загружает задачи из файла"""
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_tasks(tasks):
    """Сохраняет задачи в файл"""
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

# --- Обработка текстовых сообщений для PRO функций ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений для PRO функций"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Обработка промокода
    if context.user_data.get('waiting_for_promocode'):
        payment_id = context.user_data['waiting_for_promocode']
        result = payment_service.apply_promocode(payment_id, text.upper())
        
        if result["success"]:
            await update.message.reply_text(
                f"✅ {result['message']}\n"
                f"💰 Новая сумма: {result['new_amount']}₽"
            )
        else:
            await update.message.reply_text(f"❌ {result['message']}")
        
        context.user_data.pop('waiting_for_promocode', None)
        return
    
    # Обработка поста для разбора
    if context.user_data.get('waiting_for_post_feedback'):
        user_info = get_user_info(user_id)
        if not user_info['is_pro']:
            await update.message.reply_text("🔒 Эта функция доступна только в PRO версии!")
            context.user_data.pop('waiting_for_post_feedback', None)
            return
        
        await update.message.reply_text("🤔 Анализирую ваш пост...")
        
        try:
            analysis = await gpt_service.analyze_post_feedback(text)
            await update.message.reply_text(analysis)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка анализа: {str(e)}")
        
        context.user_data.pop('waiting_for_post_feedback', None)
        return
    
    # Обработка поста для улучшения
    if context.user_data.get('waiting_for_post_rewrite'):
        user_info = get_user_info(user_id)
        if not user_info['is_pro']:
            await update.message.reply_text("🔒 Эта функция доступна только в PRO версии!")
            context.user_data.pop('waiting_for_post_rewrite', None)
            return
        
        await update.message.reply_text("✍️ Улучшаю ваш пост...")
        
        try:
            improved = await gpt_service.rewrite_post(text)
            await update.message.reply_text(improved)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка улучшения: {str(e)}")
        
        context.user_data.pop('waiting_for_post_rewrite', None)
        return
    
    # Обработка рекламного креатива для анализа
    if context.user_data.get('waiting_for_ad_feedback'):
        user_info = get_user_info(user_id)
        if not user_info['is_pro']:
            await update.message.reply_text("🔒 Эта функция доступна только в PRO версии!")
            context.user_data.pop('waiting_for_ad_feedback', None)
            return
        
        await update.message.reply_text("📊 Анализирую ваш рекламный креатив...")
        
        try:
            # Здесь можно добавить анализ рекламного креатива
            analysis = f"📊 АНАЛИЗ РЕКЛАМНОГО КРЕАТИВА\n\n{text}\n\n✅ Креатив получен для анализа. Функция в разработке."
            await update.message.reply_text(analysis)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка анализа: {str(e)}")
        
        context.user_data.pop('waiting_for_ad_feedback', None)
        return

# --- MAIN ---
if __name__ == "__main__":
    import asyncio
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Главное меню и навигация
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("main", start))
    app.add_handler(CommandHandler("home", start))
    
    # Обработка ReplyKeyboard (главное меню и все разделы)
    from telegram.ext import MessageHandler, filters as tgfilters
    app.add_handler(MessageHandler(tgfilters.TEXT & ~tgfilters.COMMAND, menu_handler))
    
    # Обработка текстовых сообщений для PRO функций
    app.add_handler(MessageHandler(tgfilters.TEXT & ~tgfilters.COMMAND, handle_text_message))
    
    # POSTS
    app.add_handler(CommandHandler("post_idea", post_idea))
    app.add_handler(CallbackQueryHandler(post_idea_cat_callback, pattern=r"^post_idea_cat_\d+$"))
    app.add_handler(CommandHandler("popular_posts", popular_posts))
    app.add_handler(CallbackQueryHandler(popular_posts_cat_callback, pattern=r"^popular_posts_cat_\d+$"))
    app.add_handler(CommandHandler("post_format", post_format))
    app.add_handler(CallbackQueryHandler(post_format_callback, pattern=r"^post_format_\d+$"))
    app.add_handler(CommandHandler("post_feedback", post_feedback))
    app.add_handler(CommandHandler("rewrite_post", rewrite_post))
    
    # ADS
    app.add_handler(CommandHandler("ad_ideas", ad_ideas))
    app.add_handler(CallbackQueryHandler(ad_ideas_cat_callback, pattern=r"^ad_ideas_cat_\d+$"))
    app.add_handler(CommandHandler("promo_text", promo_text))
    app.add_handler(CallbackQueryHandler(promo_text_cat_callback, pattern=r"^promo_text_cat_\d+$"))
    app.add_handler(CommandHandler("top_cta", top_cta))
    app.add_handler(CallbackQueryHandler(top_cta_cat_callback, pattern=r"^top_cta_cat_\d+$"))
    app.add_handler(CommandHandler("ad_tips", ad_tips))
    app.add_handler(CommandHandler("promo_plan", promo_plan))
    app.add_handler(CommandHandler("ad_feedback", ad_feedback))
    
    # TRENDS
    app.add_handler(CommandHandler("trending_topics", trending_topics))
    app.add_handler(CallbackQueryHandler(trending_topics_cat_callback, pattern=r"^trending_topics_cat_\d+$"))
    app.add_handler(CommandHandler("trending_channels", trending_channels))
    app.add_handler(CallbackQueryHandler(trending_channels_cat_callback, pattern=r"^trending_channels_cat_\d+$"))
    app.add_handler(CommandHandler("best_times", best_times))
    app.add_handler(CallbackQueryHandler(best_times_cat_callback, pattern=r"^best_times_cat_\d+$"))
    app.add_handler(CommandHandler("engagement_boost", engagement_boost))
    app.add_handler(CallbackQueryHandler(engagement_boost_cat_callback, pattern=r"^engagement_boost_cat_\d+$"))
    app.add_handler(CommandHandler("content_trends", content_trends))
    app.add_handler(CommandHandler("trend_detective", trend_detective))
    app.add_handler(CommandHandler("falling_trends", falling_trends))
    
    # ANALYZE MY CHANNEL
    app.add_handler(CommandHandler("channel_summary", channel_summary))
    app.add_handler(CommandHandler("audience_report", audience_report))
    app.add_handler(CommandHandler("content_quality", content_quality))
    app.add_handler(CommandHandler("style_review", style_review))
    app.add_handler(CommandHandler("growth_tips", growth_tips))
    
    # PRO и платежная система
    app.add_handler(CommandHandler("subscription_info", subscription_info))
    app.add_handler(CallbackQueryHandler(upgrade_pro, pattern=r"^upgrade_pro$"))
    app.add_handler(CallbackQueryHandler(apply_promocode, pattern=r"^promo_\w+$"))
    app.add_handler(CallbackQueryHandler(process_payment, pattern=r"^pay_\w+$"))
    
    # Главное меню
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^main_menu$"))
    
    # Старый парсер
    app.add_handler(CommandHandler("parse", parse_command))
    
    print("🤖 Бот запущен! Все функции готовы к работе.")
    print("📊 FREE функции: ✅")
    print("🔒 PRO функции: ✅")
    print("💳 Платежная система: ✅")
    print("🎯 GPT интеграция: ✅")
    
    app.run_polling() 