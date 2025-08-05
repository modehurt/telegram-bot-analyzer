import asyncio
import uuid
import datetime
from typing import Dict, List, Optional
from pyrogram import Client
from bot.db import SessionLocal, Account, AccountStatus, Channel, AccountChannel
from config import PYROGRAM_API_ID, PYROGRAM_API_HASH

class AccountManager:
    def __init__(self):
        self.accounts: Dict[str, Client] = {}
        self.account_limits = {
            "max_channels_per_account": 50,
            "max_requests_per_hour": 100,
            "max_requests_per_day": 1000
        }
    
    async def initialize_accounts(self):
        """Инициализирует все аккаунты"""
        async with SessionLocal() as session:
            # Получаем все активные аккаунты из БД
            accounts = await session.execute("SELECT * FROM accounts WHERE status = 'Active'")
            
            for account_data in accounts:
                account_id = account_data.account_id
                session_file = account_data.session_file_path
                
                try:
                    # Создаем клиент для аккаунта
                    client = Client(
                        session_file,
                        api_id=PYROGRAM_API_ID,
                        api_hash=PYROGRAM_API_HASH
                    )
                    
                    # Проверяем, что аккаунт работает
                    await client.start()
                    
                    self.accounts[account_id] = client
                    print(f"[account_manager] Аккаунт {account_id} инициализирован")
                    
                except Exception as e:
                    print(f"[account_manager] Ошибка инициализации аккаунта {account_id}: {e}")
                    # Помечаем аккаунт как неактивный
                    await self.update_account_status(account_id, AccountStatus.Error)
    
    async def get_available_account(self) -> Optional[str]:
        """Возвращает доступный аккаунт для работы"""
        async with SessionLocal() as session:
            # Ищем аккаунт с наименьшей нагрузкой
            accounts = await session.execute("""
                SELECT a.account_id, COUNT(ac.channel_id) as channel_count
                FROM accounts a
                LEFT JOIN account_channels ac ON a.account_id = ac.account_id
                WHERE a.status = 'Active'
                GROUP BY a.account_id
                ORDER BY channel_count ASC
                LIMIT 1
            """)
            
            for account in accounts:
                account_id = account.account_id
                channel_count = account.channel_count or 0
                
                # Проверяем лимиты
                if channel_count < self.account_limits["max_channels_per_account"]:
                    return account_id
        
        return None
    
    async def subscribe_to_channel(self, account_id: str, channel_username: str) -> bool:
        """Подписывает аккаунт на канал"""
        try:
            client = self.accounts.get(account_id)
            if not client:
                return False
            
            # Подписываемся на канал
            chat = await client.get_chat(channel_username)
            await client.join_chat(chat.id)
            
            # Сохраняем связь в БД
            async with SessionLocal() as session:
                # Получаем или создаем канал
                channel = await session.get(Channel, str(chat.id))
                if not channel:
                    channel = Channel(
                        channel_id=str(chat.id),
                        username=chat.username or str(chat.id),
                        title=chat.title or chat.username or str(chat.id),
                        description=getattr(chat, 'description', None),
                        is_bot_admin=False
                    )
                    session.add(channel)
                    await session.commit()
                
                # Создаем связь аккаунт-канал
                account_channel = AccountChannel(
                    id=str(uuid.uuid4()),
                    account_id=account_id,
                    channel_id=str(chat.id),
                    subscribed_at=datetime.datetime.utcnow()
                )
                session.add(account_channel)
                await session.commit()
            
            print(f"[account_manager] Аккаунт {account_id} подписан на {channel_username}")
            return True
            
        except Exception as e:
            print(f"[account_manager] Ошибка подписки {account_id} на {channel_username}: {e}")
            return False
    
    async def parse_channel_posts(self, account_id: str, channel_username: str, limit: int = 100) -> List[Dict]:
        """Парсит посты канала через указанный аккаунт"""
        try:
            client = self.accounts.get(account_id)
            if not client:
                return []
            
            posts = []
            async for message in client.get_chat_history(channel_username, limit=limit):
                if message.text or message.caption:
                    post_data = {
                        "id": message.id,
                        "text": message.text or message.caption or "",
                        "date": message.date.isoformat(),
                        "views": getattr(message, 'views', 0),
                        "reactions": {r.emoji: r.count for r in message.reactions.reactions} if message.reactions else {},
                        "forwards": getattr(message, 'forwards', 0),
                        "is_ad": self.detect_ad_post(message.text or message.caption or ""),
                        "format": self.detect_post_format(message.text or message.caption or ""),
                        "cta": self.extract_cta(message.text or message.caption or "")
                    }
                    posts.append(post_data)
            
            return posts
            
        except Exception as e:
            print(f"[account_manager] Ошибка парсинга {channel_username} через {account_id}: {e}")
            return []
    
    def detect_ad_post(self, text: str) -> bool:
        """Определяет, является ли пост рекламным"""
        if not text:
            return False
        
        score = 0
        text_lower = text.lower()
        
        # Проверяем внешние ссылки
        if any(pattern in text for pattern in ['https://', 't.me/', '@', 'tg://']):
            score += 2
        
        # Проверяем CTA фразы
        cta_phrases = ['подпишись', 'читай', 'узнай', 'начни', 'перейди', 'жми', 'вступай']
        if any(phrase in text_lower for phrase in cta_phrases):
            score += 1
        
        # Проверяем количество эмодзи
        emoji_count = len([c for c in text if c in '🔴🔵⚡❤️💙💚💛💜🖤🤍🤎'])
        if emoji_count / len(text) > 0.1:  # 10% эмодзи
            score += 1
        
        # Проверяем количество заглавных букв
        caps_count = len([c for c in text if c.isupper()])
        if caps_count / len(text) > 0.3:  # 30% заглавных
            score += 1
        
        return score >= 3
    
    def detect_post_format(self, text: str) -> str:
        """Определяет формат поста"""
        if not text:
            return "other"
        
        text_lower = text.lower()
        
        # Проверяем форматы
        if any(pattern in text_lower for pattern in ['1.', '2.', '3.', '-', '•']):
            return "list"
        elif any(pattern in text_lower for pattern in ['однажды', 'я помню', 'вчера', 'когда-то']):
            return "story"
        elif any(pattern in text_lower for pattern in ['по данным', 'рост', '%', 'исследование']):
            return "analytics"
        elif any(pattern in text_lower for pattern in ['мне кажется', 'по моему мнению', 'я думаю']):
            return "opinion"
        elif any(pattern in text_lower for pattern in ['сделай', 'настрой', 'скачай', 'шаг']):
            return "howto"
        elif any(pattern in text_lower for pattern in ['произошло', 'сегодня', 'по сообщениям']):
            return "news"
        elif any(pattern in text_lower for pattern in ['ты можешь', 'поверь в себя', 'не сдавайся']):
            return "motivation"
        elif any(pattern in text_lower for pattern in ['лол', 'ахаха', 'мем', 'прикол']):
            return "fun"
        elif any(pattern in text_lower for pattern in ['—', 'сказал', 'цитата']):
            return "quote"
        
        return "other"
    
    def extract_cta(self, text: str) -> Optional[str]:
        """Извлекает CTA из текста"""
        if not text:
            return None
        
        lines = text.split('\n')
        cta_patterns = [
            'подпишись', 'следи за', 'присоединяйся', 'жми подписаться',
            'пиши в комменты', 'оцени', 'смотри дальше', 'сохрани',
            'жми на ссылку', 'а ты как думаешь?', 'пиши + если полезно',
            'что скажешь?', 'читай', 'узнай', 'начни', 'перейди',
            'жми', 'вступай', 'переходи сюда', 'канал', 'бот'
        ]
        
        # Проверяем последние 1-3 строки
        for i in range(min(3, len(lines))):
            line = lines[-(i+1)].strip()
            for pattern in cta_patterns:
                if pattern in line.lower():
                    return line
        
        return None
    
    async def update_account_status(self, account_id: str, status: AccountStatus):
        """Обновляет статус аккаунта"""
        async with SessionLocal() as session:
            account = await session.get(Account, account_id)
            if account:
                account.status = status
                account.last_used_at = datetime.datetime.utcnow()
                await session.commit()
    
    async def monitor_accounts(self):
        """Мониторинг аккаунтов каждые 24 часа"""
        while True:
            try:
                async with SessionLocal() as session:
                    accounts = await session.execute("SELECT * FROM accounts")
                    
                    for account_data in accounts:
                        account_id = account_data.account_id
                        client = self.accounts.get(account_id)
                        
                        if client:
                            try:
                                # Проверяем, что аккаунт работает
                                me = await client.get_me()
                                print(f"[monitor] Аккаунт {account_id} активен: {me.username}")
                            except Exception as e:
                                print(f"[monitor] Аккаунт {account_id} неактивен: {e}")
                                await self.update_account_status(account_id, AccountStatus.Error)
                        else:
                            print(f"[monitor] Аккаунт {account_id} не инициализирован")
                
                # Ждем 24 часа
                await asyncio.sleep(24 * 60 * 60)
                
            except Exception as e:
                print(f"[monitor] Ошибка мониторинга: {e}")
                await asyncio.sleep(60 * 60)  # Ждем час при ошибке
    
    async def distribute_channels(self, channels: List[str]) -> Dict[str, List[str]]:
        """Равномерно распределяет каналы по аккаунтам"""
        distribution = {}
        
        async with SessionLocal() as session:
            # Получаем активные аккаунты с количеством каналов
            accounts = await session.execute("""
                SELECT a.account_id, COUNT(ac.channel_id) as channel_count
                FROM accounts a
                LEFT JOIN account_channels ac ON a.account_id = ac.account_id
                WHERE a.status = 'Active'
                GROUP BY a.account_id
                ORDER BY channel_count ASC
            """)
            
            account_list = [(acc.account_id, acc.channel_count or 0) for acc in accounts]
            
            if not account_list:
                print("[account_manager] Нет активных аккаунтов")
                return {}
            
            # Распределяем каналы
            for i, channel in enumerate(channels):
                account_id = account_list[i % len(account_list)][0]
                if account_id not in distribution:
                    distribution[account_id] = []
                distribution[account_id].append(channel)
        
        return distribution
    
    async def close_all_accounts(self):
        """Закрывает все аккаунты"""
        for account_id, client in self.accounts.items():
            try:
                await client.stop()
                print(f"[account_manager] Аккаунт {account_id} закрыт")
            except Exception as e:
                print(f"[account_manager] Ошибка закрытия аккаунта {account_id}: {e}")
        
        self.accounts.clear()

# Глобальный экземпляр менеджера аккаунтов
account_manager = AccountManager() 