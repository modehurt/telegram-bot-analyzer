from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.db import SessionLocal, Group, init_db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
import re

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

@Client.on_message(filters.command("addgroup"))
async def addgroup_handler(client: Client, message: Message):
    await init_db()
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.reply("Пожалуйста, укажи ссылку, username или ID группы после команды.")
        return
    group_input = text[1].strip()
    # Пробуем получить инфо о группе через Pyrogram по любому вводу
    try:
        chat = await client.get_chat(group_input)
    except Exception as e:
        await message.reply(f"Ошибка при получении информации о группе: {e}")
        return
    group_id = chat.id
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
        result = await session.execute(select(Group).where(Group.group_id == int(group_id)))
        group = result.scalar_one_or_none()
        if group:
            group.category = category
            await session.commit()
            await callback_query.edit_message_text(f"Категория для группы '{group.title}' установлена: {category}")
        else:
            await callback_query.edit_message_text("Группа не найдена в базе.") 