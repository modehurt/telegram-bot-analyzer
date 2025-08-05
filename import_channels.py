import os
import re
import asyncio
from dotenv import load_dotenv
from pyrogram import Client
from bot.db import SessionLocal, Group, init_db
from sqlalchemy import select

load_dotenv()
API_ID = int(os.getenv("PYROGRAM_API_ID", "0"))
API_HASH = os.getenv("PYROGRAM_API_HASH", "" )

CHANNELS_FILE = "channels.txt"

async def import_channels():
    await init_db()
    app = Client("importer", api_id=API_ID, api_hash=API_HASH)
    await app.start()
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    current_category = None
    url_pattern = re.compile(r"https://t\.me/([a-zA-Z0-9_]+)")
    async with SessionLocal() as session:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Если строка не ссылка — это категория
            if not line.startswith("https://t.me/"):
                current_category = line
                continue
            # Иначе это ссылка
            for match in url_pattern.finditer(line):
                username = match.group(1)
                try:
                    chat = await app.get_chat(username)
                    group_id = chat.id
                    title = chat.title or chat.first_name or username
                except Exception as e:
                    print(f"[!] Не удалось получить {username}: {e}")
                    group_id = None
                    title = username
                # Проверяем, есть ли уже такой канал
                result = await session.execute(select(Group).where(Group.group_id == group_id))
                group = result.scalar_one_or_none()
                if group:
                    group.category = current_category
                    group.title = title
                else:
                    group = Group(group_id=group_id, title=title, category=current_category)
                    session.add(group)
                print(f"Добавлено: {title} (@{username}) — категория: {current_category}")
        await session.commit()
    await app.stop()
    print("Импорт завершён!")

if __name__ == "__main__":
    asyncio.run(import_channels()) 