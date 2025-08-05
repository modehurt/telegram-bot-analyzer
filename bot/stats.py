# Здесь будут функции для подсчёта и выдачи статистики по группам
from sqlalchemy import select, func
from bot.db import SessionLocal, Group, Message

async def get_group_stats(group_id: int):
    """Получает статистику по группе"""
    async with SessionLocal() as session:
        # Получаем группу
        group = await session.scalar(select(Group).where(Group.group_id == group_id))
        if not group:
            return None
        
        # Считаем общее количество сообщений
        total_messages = await session.scalar(
            select(func.count()).select_from(Message).where(Message.group_id == group_id)
        )
        
        # Топ пользователей по активности
        top_users = await session.execute(
            select(Message.user_id, func.count().label('message_count'))
            .where(Message.group_id == group_id)
            .group_by(Message.user_id)
            .order_by(func.count().desc())
            .limit(5)
        )
        
        # Статистика по дням
        daily_stats = await session.execute(
            select(
                func.date(Message.date).label('date'),
                func.count().label('messages')
            )
            .where(Message.group_id == group_id)
            .group_by(func.date(Message.date))
            .order_by(func.date(Message.date).desc())
            .limit(7)
        )
        
        return {
            "group": group,
            "total_messages": total_messages,
            "top_users": top_users.all(),
            "daily_stats": daily_stats.all()
        } 