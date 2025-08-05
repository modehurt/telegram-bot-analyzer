import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI API
OPENAI_API_KEY = "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"

# Telegram Bot
BOT_TOKEN = "8049611910:AAEMgnKc7SB9sb8ytWfl7rQ1cNrC6JK8_Po"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://tguser:tgpass@localhost:5432/tgstat")

# Pyrogram
PYROGRAM_API_ID = int(os.getenv("PYROGRAM_API_ID", "26333656"))
PYROGRAM_API_HASH = os.getenv("PYROGRAM_API_HASH", "2c550faf732f3920b062006d9b7dfd55")

# Limits
FREE_LIMIT = 3  # 3 запроса в сутки для обычных пользователей
PRO_LIMIT = 100  # 100 запросов в сутки для PRO пользователей

# Categories
CATEGORIES = [
    "Маркетинг и продажи", "Бизнес и стартапы", "Психология и саморазвитие", 
    "Образование и курсы", "Технологии и IT", "Финансы и инвестиции", 
    "Мотивация и продуктивность", "Юмор и мемы", "Путешествия и география", 
    "Здоровье и спорт", "Книги и литература", "Кино и сериалы", 
    "Новости и события", "Дизайн и креатив", "Личный бренд и блогинг", 
    "Мода и стиль", "Еда и рецепты", "Игры и гейминг", "Музыка и культура", 
    "Питомцы и животные", "AI / ChatGPT / нейросети", "Разработка и кодинг", 
    "Таргет и реклама", "SMM / ведение соцсетей", "Контент-маркетинг"
]

# Post formats
FORMATS = [
    "Сторителлинг", "Список", "Интрига", "Проблема-решение", "Аналитика", "Образовательный"
]

# PRO features
PRO_FEATURES = [
    "Расширенная аналитика каналов",
    "Персональные отчеты",
    "Автоматическое планирование постов",
    "A/B тестирование контента",
    "Интеграция с другими платформами",
    "Разбор и улучшение постов",
    "Планы продвижения",
    "Анализ рекламных креативов",
    "Тренд-детектив",
    "Анализ падающих трендов"
]

# Payment settings
PAYMENT_TOKEN = "wEbvur-supre8-hygcow"  # Промокод для тестирования
PRO_PRICE = 999  # Цена PRO подписки в рублях
PRO_DURATION_DAYS = 30  # Длительность PRO подписки

# Admin settings
ADMIN_USERNAME = "tgfoundry88@gmail.com"
ADMIN_TELEGRAM_ID = 123456789  # Замените на реальный ID админа 