from pyrogram import Client, filters
from pyrogram.types import Message
from bot.db import SessionLocal, Group, Message as DBMessage

@Client.on_message(filters.group)
async def log_group_message(client: Client, message: Message):
    async with SessionLocal() as session:
        group = await session.get(Group, message.chat.id)
        if not group:
            return
        msg = DBMessage(
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