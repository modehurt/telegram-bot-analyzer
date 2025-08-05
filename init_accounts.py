#!/usr/bin/env python3
"""
Скрипт для инициализации множественных Telegram аккаунтов
"""

import asyncio
import uuid
import datetime
from typing import List, Dict
from pyrogram import Client
from bot.db import SessionLocal, Account, AccountStatus, init_db
from config import PYROGRAM_API_ID, PYROGRAM_API_HASH

# Список аккаунтов для инициализации
ACCOUNTS_DATA = [
    {
        "phone": "+79001234567",
        "session": "account1",
        "description": "Основной аккаунт 1"
    },
    {
        "phone": "+79001234568", 
        "session": "account2",
        "description": "Основной аккаунт 2"
    },
    {
        "phone": "+79001234569",
        "session": "account3", 
        "description": "Основной аккаунт 3"
    },
    {
        "phone": "+79001234570",
        "session": "account4",
        "description": "Основной аккаунт 4"
    },
    {
        "phone": "+79001234571",
        "session": "account5",
        "description": "Основной аккаунт 5"
    },
    {
        "phone": "+79001234572",
        "session": "account6",
        "description": "Основной аккаунт 6"
    },
    {
        "phone": "+79001234573",
        "session": "account7",
        "description": "Основной аккаунт 7"
    },
    {
        "phone": "+79001234574",
        "session": "account8",
        "description": "Основной аккаунт 8"
    },
    {
        "phone": "+79001234575",
        "session": "account9",
        "description": "Основной аккаунт 9"
    },
    {
        "phone": "+79001234576",
        "session": "account10",
        "description": "Основной аккаунт 10"
    },
    {
        "phone": "+79001234577",
        "session": "account11",
        "description": "Резервный аккаунт 1"
    },
    {
        "phone": "+79001234578",
        "session": "account12", 
        "description": "Резервный аккаунт 2"
    },
    {
        "phone": "+79001234579",
        "session": "account13",
        "description": "Резервный аккаунт 3"
    },
    {
        "phone": "+79001234580",
        "session": "account14",
        "description": "Резервный аккаунт 4"
    },
    {
        "phone": "+79001234581",
        "session": "account15",
        "description": "Резервный аккаунт 5"
    }
]

async def create_account_in_db(account_data: Dict) -> bool:
    """Создает запись аккаунта в базе данных"""
    try:
        async with SessionLocal() as session:
            # Проверяем, существует ли уже аккаунт
            existing_account = await session.get(Account, account_data["session"])
            if existing_account:
                print(f"[DB] Аккаунт {account_data['session']} уже существует в БД")
                return True
            
            # Создаем новый аккаунт
            account = Account(
                account_id=account_data["session"],
                phone_number=account_data["phone"],
                session_file_path=f"{account_data['session']}.session",
                status=AccountStatus.Active,
                is_logged_in=False,
                total_channels=0,
                last_used_at=None,
                created_at=datetime.datetime.utcnow()
            )
            
            session.add(account)
            await session.commit()
            
            print(f"[DB] Аккаунт {account_data['session']} создан в БД")
            return True
            
    except Exception as e:
        print(f"[DB] Ошибка создания аккаунта {account_data['session']}: {e}")
        return False

async def initialize_account(account_data: Dict) -> bool:
    """Инициализирует один аккаунт"""
    try:
        print(f"[INIT] Инициализация аккаунта {account_data['session']}...")
        
        # Создаем клиент
        client = Client(
            account_data["session"],
            api_id=PYROGRAM_API_ID,
            api_hash=PYROGRAM_API_HASH
        )
        
        # Запускаем клиент
        await client.start()
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        
        print(f"[INIT] Аккаунт {account_data['session']} успешно инициализирован: @{me.username}")
        
        # Останавливаем клиент
        await client.stop()
        
        # Создаем запись в БД
        await create_account_in_db(account_data)
        
        return True
        
    except Exception as e:
        print(f"[INIT] Ошибка инициализации аккаунта {account_data['session']}: {e}")
        return False

async def initialize_all_accounts():
    """Инициализирует все аккаунты"""
    print("🚀 Начинаю инициализацию Telegram аккаунтов...")
    
    # Инициализируем базу данных
    await init_db()
    print("✅ База данных инициализирована")
    
    success_count = 0
    total_count = len(ACCOUNTS_DATA)
    
    for i, account_data in enumerate(ACCOUNTS_DATA, 1):
        print(f"\n[{i}/{total_count}] Обработка аккаунта {account_data['session']}...")
        
        if await initialize_account(account_data):
            success_count += 1
            print(f"✅ Аккаунт {account_data['session']} успешно инициализирован")
        else:
            print(f"❌ Ошибка инициализации аккаунта {account_data['session']}")
        
        # Делаем паузу между аккаунтами
        await asyncio.sleep(5)
    
    print(f"\n🎉 Инициализация завершена!")
    print(f"✅ Успешно: {success_count}/{total_count}")
    print(f"❌ Ошибок: {total_count - success_count}")
    
    if success_count > 0:
        print(f"\n📋 Следующие шаги:")
        print(f"1. Проверьте session файлы в корневой папке")
        print(f"2. Запустите мониторинг аккаунтов: python monitor_accounts.py")
        print(f"3. Начните парсинг: python userbot_stats.py")

async def check_accounts_status():
    """Проверяет статус всех аккаунтов"""
    print("🔍 Проверка статуса аккаунтов...")
    
    async with SessionLocal() as session:
        accounts = await session.execute("SELECT * FROM accounts")
        
        active_count = 0
        banned_count = 0
        error_count = 0
        
        for account_data in accounts:
            status = account_data.status
            if status == AccountStatus.Active:
                active_count += 1
            elif status == AccountStatus.Banned:
                banned_count += 1
            elif status == AccountStatus.Error:
                error_count += 1
        
        print(f"📊 Статистика аккаунтов:")
        print(f"✅ Активные: {active_count}")
        print(f"🚫 Заблокированные: {banned_count}")
        print(f"⚠️ С ошибками: {error_count}")
        print(f"📈 Всего: {active_count + banned_count + error_count}")

async def test_account_connection(account_id: str):
    """Тестирует подключение конкретного аккаунта"""
    try:
        print(f"🔍 Тестирование подключения аккаунта {account_id}...")
        
        client = Client(
            account_id,
            api_id=PYROGRAM_API_ID,
            api_hash=PYROGRAM_API_HASH
        )
        
        await client.start()
        me = await client.get_me()
        await client.stop()
        
        print(f"✅ Аккаунт {account_id} работает: @{me.username}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения аккаунта {account_id}: {e}")
        return False

async def main():
    """Главная функция"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            await initialize_all_accounts()
        elif command == "status":
            await check_accounts_status()
        elif command == "test":
            if len(sys.argv) > 2:
                account_id = sys.argv[2]
                await test_account_connection(account_id)
            else:
                print("❌ Укажите ID аккаунта для тестирования")
                print("Пример: python init_accounts.py test account1")
        else:
            print("❌ Неизвестная команда")
            print("Доступные команды:")
            print("  init   - Инициализировать все аккаунты")
            print("  status - Проверить статус аккаунтов")
            print("  test   - Тестировать подключение аккаунта")
    else:
        print("🔧 Скрипт инициализации Telegram аккаунтов")
        print("\nДоступные команды:")
        print("  python init_accounts.py init   - Инициализировать все аккаунты")
        print("  python init_accounts.py status - Проверить статус аккаунтов")
        print("  python init_accounts.py test account1 - Тестировать аккаунт")
        print("\n⚠️ Внимание: Для инициализации потребуется ввести код подтверждения для каждого аккаунта")

if __name__ == "__main__":
    asyncio.run(main()) 