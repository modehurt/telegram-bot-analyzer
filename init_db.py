#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from bot.db import Base, init_db
from config import DATABASE_URL

async def create_tables():
    """Создает все таблицы в базе данных"""
    try:
        # Создаем движок
        engine = create_async_engine(DATABASE_URL, echo=True)
        
        # Создаем все таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Все таблицы успешно созданы!")
        
        # Инициализируем базовые данные
        await init_db()
        print("✅ База данных инициализирована!")
        
    except Exception as e:
        print(f"❌ Ошибка создания таблиц: {e}")
        raise

async def main():
    """Основная функция"""
    print("🚀 Начинаю инициализацию базы данных...")
    
    # Проверяем переменные окружения
    if not DATABASE_URL:
        print("❌ Ошибка: DATABASE_URL не настроен")
        return
    
    print(f"📊 Подключение к БД: {DATABASE_URL}")
    
    try:
        await create_tables()
        print("🎉 База данных готова к работе!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 