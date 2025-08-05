from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.db import SessionLocal, Group, Message as DBMessage
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

@Client.on_message(filters.command("stats"))
async def stats_handler(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(cat, callback_data=f"stats_cat_{i}")]
        for i, cat in enumerate(CATEGORIES)
    ])
    await message.reply("Выбери категорию:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r"^stats_cat_([0-9]+)$"))
async def stats_category_callback(client: Client, callback_query: CallbackQuery):
    cat_idx = int(callback_query.matches[0].group(1))
    category = CATEGORIES[cat_idx]
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
        total_msgs = await session.scalar(select(func.count()).select_from(DBMessage).where(DBMessage.group_id == group_id))
        top_users = await session.execute(
            select(DBMessage.user_id, func.count().label('cnt'))
            .where(DBMessage.group_id == group_id)
            .group_by(DBMessage.user_id)
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