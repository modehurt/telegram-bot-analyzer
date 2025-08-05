from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.db import SessionLocal, Group, init_db, Message
from sqlalchemy.exc import IntegrityError
import re
from sqlalchemy import select, func

CATEGORIES = [
    "Маркетинг и продажи",
    "Бизнес и стартапы",
    "Психология и саморазвитие",
    "Образование и курсы",
    "Технологии и IT",
    "Финансы и инвестиции",
    "Мотивация и продуктивность",
    "Юмор и мемы",
    "Путешествия и география",
    "Здоровье и спорт",
    "Книги и литература",
    "Кино и сериалы",
    "Новости и события",
    "Дизайн и креатив",
    "Личный бренд и блогинг",
    "Мода и стиль",
    "Еда и рецепты",
    "Игры и гейминг",
    "Музыка и культура",
    "Питомцы и животные",
    "AI / ChatGPT / нейросети",
    "Разработка и кодинг",
    "Таргет и реклама",
    "SMM / ведение соцсетей",
    "Контент-маркетинг"
]

@Client.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    await message.reply("Привет! Я бот для сбора статистики по Telegram-группам. Добавь группу через /addgroup.")

@Client.on_message(filters.command("addgroup"))
async def addgroup_handler(client: Client, message: Message):
    await init_db()
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.reply("Пожалуйста, укажи ссылку или ID группы после команды.")
        return
    group_input = text[1].strip()
    match = re.search(r'-?\d+', group_input)
    if not match:
        await message.reply("Не удалось определить ID группы. Пришли ссылку или числовой ID.")
        return
    group_id = int(match.group())
    try:
        chat = await client.get_chat(group_id)
    except Exception as e:
        await message.reply(f"Ошибка при получении информации о группе: {e}")
        return
    # Сохраняем в БД без категории
    async with SessionLocal() as session:
        group = Group(group_id=group_id, title=chat.title, category=None)
        session.add(group)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.reply("Эта группа уже есть в базе.")
            return
        except Exception as e:
            await session.rollback()
            await message.reply(f"Ошибка при добавлении в базу: {e}")
            return
    # Предлагаем выбрать категорию
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(cat, callback_data=f"cat_{group_id}_{i}")]
        for i, cat in enumerate(CATEGORIES)
    ])
    await message.reply(f"Группа '{chat.title}' добавлена!\nВыбери категорию:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r"^cat_(-?\d+)_([0-9]+)$"))
async def category_callback_handler(client: Client, callback_query: CallbackQuery):
    group_id, cat_idx = callback_query.matches[0].group(1), int(callback_query.matches[0].group(2))
    category = CATEGORIES[cat_idx]
    async with SessionLocal() as session:
        group = await session.scalar(
            session.query(Group).filter_by(group_id=int(group_id))
        )
        if group:
            group.category = category
            await session.commit()
            await callback_query.edit_message_text(f"Категория для группы '{group.title}' установлена: {category}")
        else:
            await callback_query.edit_message_text("Группа не найдена в базе.")

@Client.on_message(filters.command("stats"))
async def stats_handler(client: Client, message: Message):
    # Предлагаем выбрать категорию
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(cat, callback_data=f"stats_cat_{i}")]
        for i, cat in enumerate(CATEGORIES)
    ])
    await message.reply("Выбери категорию:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r"^stats_cat_([0-9]+)$"))
async def stats_category_callback(client: Client, callback_query: CallbackQuery):
    cat_idx = int(callback_query.matches[0].group(1))
    category = CATEGORIES[cat_idx]
    # Получаем группы из этой категории
    async with SessionLocal() as session:
        result = await session.execute(select(Group).where(Group.category == category))
        groups = result.scalars().all()
    if not groups:
        await callback_query.edit_message_text(f"В категории '{category}' нет групп.")
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(g.title, callback_data=f"stats_group_{g.group_id}")]
        for g in groups
    ])
    await callback_query.edit_message_text(f"Выбери группу из категории '{category}':", reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r"^stats_group_(-?\d+)$"))
async def stats_group_callback(client: Client, callback_query: CallbackQuery):
    group_id = int(callback_query.matches[0].group(1))
    async with SessionLocal() as session:
        group = await session.scalar(select(Group).where(Group.group_id == group_id))
        if not group:
            await callback_query.edit_message_text("Группа не найдена в базе.")
            return
        # Считаем статистику
        total_msgs = await session.scalar(select(func.count()).select_from(Message).where(Message.group_id == group_id))
        top_users = await session.execute(
            select(Message.user_id, func.count().label('cnt'))
            .where(Message.group_id == group_id)
            .group_by(Message.user_id)
            .order_by(func.count().desc())
            .limit(3)
        )
        top_users = top_users.all()
    text = f"Статистика по группе '{group.title}':\n"
    text += f"Всего сообщений: {total_msgs}\n"
    if top_users:
        text += "Топ-3 активных пользователя (user_id):\n"
        for uid, cnt in top_users:
            text += f"- {uid}: {cnt} сообщений\n"
    else:
        text += "Нет сообщений в базе."
    await callback_query.edit_message_text(text)

@Client.on_message(filters.group)
async def log_group_message(client: Client, message: Message):
    # Проверяем, есть ли эта группа в базе
    async with SessionLocal() as session:
        group = await session.get(Group, message.chat.id)
        if not group:
            return  # Не логируем сообщения из неотслеживаемых групп
        msg = Message(
            group_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else None,
            text=message.text or message.caption or '',
            date=message.date
        )
        session.add(msg)
        try:
            await session.commit()
        except Exception:
            await session.rollback() 