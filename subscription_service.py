import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import FREE_LIMIT, PRO_LIMIT, PRO_FEATURES

class SubscriptionService:
    def __init__(self):
        self.user_limits: Dict[int, Dict] = {}  # user_id -> {count, last_day, is_pro}
        self.pro_users: set = set()  # Множество PRO пользователей
    
    def is_pro_user(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь PRO"""
        return user_id in self.pro_users
    
    def add_pro_user(self, user_id: int):
        """Добавляет пользователя в PRO"""
        self.pro_users.add(user_id)
        if user_id in self.user_limits:
            self.user_limits[user_id]['is_pro'] = True
    
    def remove_pro_user(self, user_id: int):
        """Удаляет пользователя из PRO"""
        self.pro_users.discard(user_id)
        if user_id in self.user_limits:
            self.user_limits[user_id]['is_pro'] = False
    
    def check_limit(self, user_id: int) -> bool:
        """Проверяет лимит пользователя"""
        today = datetime.now().date()
        limit = PRO_LIMIT if self.is_pro_user(user_id) else FREE_LIMIT
        
        if user_id not in self.user_limits or self.user_limits[user_id]['last_day'] != today:
            self.user_limits[user_id] = {
                'count': 0,
                'last_day': today,
                'is_pro': self.is_pro_user(user_id)
            }
        
        if self.user_limits[user_id]['count'] >= limit:
            return False
        
        self.user_limits[user_id]['count'] += 1
        return True
    
    def get_remaining_requests(self, user_id: int) -> int:
        """Возвращает количество оставшихся запросов"""
        today = datetime.now().date()
        limit = PRO_LIMIT if self.is_pro_user(user_id) else FREE_LIMIT
        
        if user_id not in self.user_limits or self.user_limits[user_id]['last_day'] != today:
            return limit
        
        return max(0, limit - self.user_limits[user_id]['count'])
    
    def get_pro_features(self) -> List[str]:
        """Возвращает список PRO функций"""
        return PRO_FEATURES
    
    def get_subscription_info(self, user_id: int) -> Dict:
        """Возвращает информацию о подписке пользователя"""
        is_pro = self.is_pro_user(user_id)
        remaining = self.get_remaining_requests(user_id)
        limit = PRO_LIMIT if is_pro else FREE_LIMIT
        
        return {
            'is_pro': is_pro,
            'remaining_requests': remaining,
            'daily_limit': limit,
            'pro_features': PRO_FEATURES if is_pro else []
        }

# Глобальный экземпляр сервиса подписок
subscription_service = SubscriptionService()

# Добавляем тестовых PRO пользователей
subscription_service.add_pro_user(123456789)  # Замените на реальные ID 