from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from subscription_service import subscription_service

@Client.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    """Главное меню бота"""
    user_id = message.from_user.id
    user_info = subscription_service.get_subscription_info(user_id)
    
    # Определяем статус пользователя
    status_text = "🔒 FREE" if not user_info['is_pro'] else "💎 PRO"
    remaining = user_info['remaining_requests']
    limit = user_info['daily_limit']
    
    welcome_text = f"""👋 Добро пожаловать в TG Content Analyzer!

Я помогу тебе анализировать, генерировать и улучшать контент для Telegram-каналов.

📊 Твой статус: {status_text}
📈 Осталось запросов: {remaining}/{limit}

Выбери раздел ниже:"""

    # Создаем клавиатуру с основными разделами
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 POSTS", callback_data="menu_posts")],
        [InlineKeyboardButton("💰 ADS", callback_data="menu_ads")],
        [InlineKeyboardButton("📈 TRENDS", callback_data="menu_trends")],
        [InlineKeyboardButton("📊 ANALYZE", callback_data="menu_analyze")],
        [InlineKeyboardButton("💳 Подписка", callback_data="menu_subscription")]
    ])
    
    await message.reply_text(welcome_text, reply_markup=keyboard) 