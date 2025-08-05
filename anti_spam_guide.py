"""
Рекомендации по управлению Telegram аккаунтами для предотвращения банов
"""

class AntiSpamGuide:
    def __init__(self):
        self.account_limits = {
            "max_channels_per_account": 50,
            "max_requests_per_hour": 100,
            "max_requests_per_day": 1000,
            "max_posts_per_hour": 20,
            "max_posts_per_day": 200
        }
        
        self.warming_up_schedule = {
            "day_1": {"channels": 5, "posts": 10},
            "day_2": {"channels": 10, "posts": 20},
            "day_3": {"channels": 15, "posts": 30},
            "day_4": {"channels": 20, "posts": 40},
            "day_5": {"channels": 25, "posts": 50},
            "day_6": {"channels": 30, "posts": 60},
            "day_7": {"channels": 35, "posts": 70},
            "day_8": {"channels": 40, "posts": 80},
            "day_9": {"channels": 45, "posts": 90},
            "day_10": {"channels": 50, "posts": 100}
        }
    
    def get_account_management_tips(self) -> str:
        """Возвращает рекомендации по управлению аккаунтами"""
        return """
🔒 РЕКОМЕНДАЦИИ ПО УПРАВЛЕНИЮ TELEGRAM АККАУНТАМИ

📱 ПОДГОТОВКА АККАУНТОВ:
• Используйте только реальные номера телефонов
• Каждый аккаунт должен иметь уникальный IP-адрес
• Рекомендуется использовать прокси-серверы
• Аккаунты должны быть зарегистрированы вручную

🔥 РАЗОГРЕВ АККАУНТОВ (10 дней):
• День 1: 5 каналов, 10 постов
• День 2: 10 каналов, 20 постов
• День 3: 15 каналов, 30 постов
• День 4: 20 каналов, 40 постов
• День 5: 25 каналов, 50 постов
• День 6: 30 каналов, 60 постов
• День 7: 35 каналов, 70 постов
• День 8: 40 каналов, 80 постов
• День 9: 45 каналов, 90 постов
• День 10: 50 каналов, 100 постов

⚡ ЛИМИТЫ НА АККАУНТ:
• Максимум 50 каналов на аккаунт
• Максимум 100 запросов в час
• Максимум 1000 запросов в день
• Максимум 20 постов в час
• Максимум 200 постов в день

🛡️ АНТИСПАМ МЕРЫ:
• Делайте паузы между действиями (5-10 секунд)
• Не выполняйте массовые действия одновременно
• Используйте разные аккаунты для разных задач
• Регулярно проверяйте статус аккаунтов
• При ошибках делайте длительные паузы (1-2 часа)

🚨 ПРИЗНАКИ БЛОКИРОВКИ:
• Ошибка "Too Many Requests"
• Ошибка "Flood Wait"
• Аккаунт не может подписаться на каналы
• Ограничения на отправку сообщений

🔄 ВОССТАНОВЛЕНИЕ АККАУНТА:
• При блокировке сделайте паузу 24-48 часов
• Уменьшите количество действий в 2 раза
• Используйте другой IP-адрес
• Проверьте, не нарушены ли правила Telegram

📊 МОНИТОРИНГ:
• Проверяйте статус аккаунтов каждые 24 часа
• Ведите лог всех действий
• Отслеживайте ошибки и ограничения
• Автоматически помечайте проблемные аккаунты
"""
    
    def get_proxy_recommendations(self) -> str:
        """Рекомендации по использованию прокси"""
        return """
🌐 РЕКОМЕНДАЦИИ ПО ПРОКСИ

📋 ТИПЫ ПРОКСИ:
• HTTP/HTTPS прокси - для базового использования
• SOCKS5 прокси - для более стабильной работы
• Residential прокси - для максимальной безопасности

🔧 НАСТРОЙКА ПРОКСИ:
• Каждый аккаунт должен использовать уникальный IP
• Прокси должны быть из разных стран
• Рекомендуется ротация IP-адресов
• Проверяйте скорость и стабильность прокси

💰 РЕКОМЕНДУЕМЫЕ ПРОКСИ:
• Bright Data (бывший Luminati)
• Oxylabs
• Smartproxy
• IPRoyal
• ProxyMesh

⚙️ НАСТРОЙКА В PYROGRAM:
```python
client = Client(
    "session_name",
    api_id=API_ID,
    api_hash=API_HASH,
    proxy=dict(
        scheme="http",
        hostname="proxy_host",
        port=8080,
        username="proxy_user",
        password="proxy_pass"
    )
)
```

⚠️ ВАЖНЫЕ МОМЕНТЫ:
• Не используйте бесплатные прокси
• Регулярно меняйте IP-адреса
• Мониторьте качество прокси
• Имейте резервные прокси
"""
    
    def get_warming_up_plan(self, day: int) -> Dict:
        """Возвращает план разогрева для конкретного дня"""
        if day > 10:
            day = 10
        
        return self.warming_up_schedule[f"day_{day}"]
    
    def check_account_health(self, account_data: Dict) -> Dict:
        """Проверяет здоровье аккаунта"""
        health_score = 100
        warnings = []
        
        # Проверяем количество каналов
        if account_data.get("total_channels", 0) > self.account_limits["max_channels_per_account"]:
            health_score -= 20
            warnings.append("Превышен лимит каналов на аккаунт")
        
        # Проверяем количество запросов за час
        if account_data.get("requests_last_hour", 0) > self.account_limits["max_requests_per_hour"]:
            health_score -= 30
            warnings.append("Превышен лимит запросов за час")
        
        # Проверяем количество запросов за день
        if account_data.get("requests_last_day", 0) > self.account_limits["max_requests_per_day"]:
            health_score -= 40
            warnings.append("Превышен лимит запросов за день")
        
        # Проверяем статус аккаунта
        if account_data.get("status") == "Banned":
            health_score = 0
            warnings.append("Аккаунт заблокирован")
        elif account_data.get("status") == "Error":
            health_score -= 50
            warnings.append("Аккаунт имеет ошибки")
        
        # Проверяем время последнего использования
        last_used = account_data.get("last_used_at")
        if last_used:
            hours_since_last_use = (datetime.datetime.utcnow() - last_used).total_seconds() / 3600
            if hours_since_last_use > 24:
                health_score -= 10
                warnings.append("Аккаунт не использовался более 24 часов")
        
        return {
            "health_score": max(0, health_score),
            "status": "Healthy" if health_score >= 70 else "Warning" if health_score >= 40 else "Critical",
            "warnings": warnings,
            "recommendations": self.get_account_recommendations(health_score)
        }
    
    def get_account_recommendations(self, health_score: int) -> List[str]:
        """Возвращает рекомендации для аккаунта"""
        recommendations = []
        
        if health_score < 30:
            recommendations.extend([
                "Немедленно прекратите использование аккаунта",
                "Сделайте паузу на 24-48 часов",
                "Проверьте, не заблокирован ли аккаунт",
                "Используйте другой IP-адрес"
            ])
        elif health_score < 70:
            recommendations.extend([
                "Уменьшите количество действий",
                "Увеличьте паузы между действиями",
                "Мониторьте аккаунт более внимательно",
                "Подготовьте резервный аккаунт"
            ])
        else:
            recommendations.extend([
                "Аккаунт в хорошем состоянии",
                "Продолжайте использовать в обычном режиме",
                "Регулярно проверяйте статус"
            ])
        
        return recommendations
    
    def get_action_delays(self) -> Dict:
        """Возвращает рекомендуемые задержки между действиями"""
        return {
            "subscribe_to_channel": 5,  # секунд
            "get_chat_history": 3,
            "send_message": 10,
            "join_chat": 8,
            "leave_chat": 5,
            "get_chat_members": 15,
            "download_media": 2,
            "get_me": 1
        }
    
    def get_error_handling_strategy(self, error_type: str) -> Dict:
        """Стратегия обработки ошибок"""
        strategies = {
            "TooManyRequests": {
                "wait_time": 3600,  # 1 час
                "action": "pause_account",
                "message": "Превышен лимит запросов. Пауза 1 час."
            },
            "FloodWait": {
                "wait_time": 7200,  # 2 часа
                "action": "pause_account",
                "message": "Flood Wait. Пауза 2 часа."
            },
            "UserBanned": {
                "wait_time": 86400,  # 24 часа
                "action": "mark_banned",
                "message": "Аккаунт заблокирован. Требуется восстановление."
            },
            "ChannelPrivate": {
                "wait_time": 300,  # 5 минут
                "action": "skip_channel",
                "message": "Канал приватный. Пропускаем."
            },
            "ChatNotFound": {
                "wait_time": 60,  # 1 минута
                "action": "skip_channel",
                "message": "Канал не найден. Пропускаем."
            }
        }
        
        return strategies.get(error_type, {
            "wait_time": 300,
            "action": "retry",
            "message": "Неизвестная ошибка. Повтор через 5 минут."
        })

# Глобальный экземпляр антиспам гида
anti_spam_guide = AntiSpamGuide() 