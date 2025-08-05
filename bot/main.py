import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv
from bot.db import SessionLocal, init_db
from bot.handlers import start_handler, addgroup_handler, stats_handler
from tg_bot_parser import (
    post_idea, popular_posts, post_format, ad_ideas, promo_text, top_cta,
    trending_topics, engagement_boost, channel_summary, audience_report,
    content_quality, style_review, subscription_info, upgrade_pro,
    post_idea_cat_callback, popular_posts_cat_callback, post_format_callback,
    ad_ideas_cat_callback, promo_text_cat_callback, top_cta_cat_callback,
    trending_topics_cat_callback, engagement_boost_cat_callback,
    # V2 функции
    post_feedback, rewrite_post, ad_tips, promo_plan, ad_feedback,
    content_trends, trend_detective, falling_trends, growth_tips,
    trending_channels, best_times,
    ad_tips_cat_callback, promo_plan_cat_callback, content_trends_cat_callback,
    trend_detective_cat_callback, falling_trends_cat_callback,
    trending_channels_cat_callback, best_times_cat_callback
)
from gpt_service import gpt_service
from subscription_service import subscription_service

load_dotenv()

API_ID = int(os.getenv("PYROGRAM_API_ID", "0"))
API_HASH = os.getenv("PYROGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("PYROGRAM_BOT_TOKEN", "")

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Регистрируем обработчики
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await start_handler(client, message)

@app.on_message(filters.command("addgroup"))
async def addgroup_command(client: Client, message: Message):
    await addgroup_handler(client, message)

@app.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    await stats_handler(client, message)

# Команды POSTS
@app.on_message(filters.command("post_idea"))
async def post_idea_command(client: Client, message: Message):
    await post_idea(client, message)

@app.on_message(filters.command("popular_posts"))
async def popular_posts_command(client: Client, message: Message):
    await popular_posts(client, message)

@app.on_message(filters.command("post_format"))
async def post_format_command(client: Client, message: Message):
    await post_format(client, message)

# Команды ADS
@app.on_message(filters.command("ad_ideas"))
async def ad_ideas_command(client: Client, message: Message):
    await ad_ideas(client, message)

@app.on_message(filters.command("promo_text"))
async def promo_text_command(client: Client, message: Message):
    await promo_text(client, message)

@app.on_message(filters.command("top_cta"))
async def top_cta_command(client: Client, message: Message):
    await top_cta(client, message)

# Команды TRENDS
@app.on_message(filters.command("trending_topics"))
async def trending_topics_command(client: Client, message: Message):
    await trending_topics(client, message)

@app.on_message(filters.command("engagement_boost"))
async def engagement_boost_command(client: Client, message: Message):
    await engagement_boost(client, message)

# V2 команды TRENDS
@app.on_message(filters.command("content_trends"))
async def content_trends_command(client: Client, message: Message):
    await content_trends(client, message)

@app.on_message(filters.command("trend_detective"))
async def trend_detective_command(client: Client, message: Message):
    await trend_detective(client, message)

@app.on_message(filters.command("falling_trends"))
async def falling_trends_command(client: Client, message: Message):
    await falling_trends(client, message)

@app.on_message(filters.command("trending_channels"))
async def trending_channels_command(client: Client, message: Message):
    await trending_channels(client, message)

@app.on_message(filters.command("best_times"))
async def best_times_command(client: Client, message: Message):
    await best_times(client, message)

# Команды ANALYZE MY CHANNEL (PRO)
@app.on_message(filters.command("channel_summary"))
async def channel_summary_command(client: Client, message: Message):
    await channel_summary(client, message)

@app.on_message(filters.command("audience_report"))
async def audience_report_command(client: Client, message: Message):
    await audience_report(client, message)

@app.on_message(filters.command("content_quality"))
async def content_quality_command(client: Client, message: Message):
    await content_quality(client, message)

@app.on_message(filters.command("style_review"))
async def style_review_command(client: Client, message: Message):
    await style_review(client, message)

# V2 команды ANALYZE MY CHANNEL (PRO)
@app.on_message(filters.command("growth_tips"))
async def growth_tips_command(client: Client, message: Message):
    await growth_tips(client, message)

# V2 команды POSTS (PRO)
@app.on_message(filters.command("post_feedback"))
async def post_feedback_command(client: Client, message: Message):
    await post_feedback(client, message)

@app.on_message(filters.command("rewrite_post"))
async def rewrite_post_command(client: Client, message: Message):
    await rewrite_post(client, message)

# V2 команды ADS
@app.on_message(filters.command("ad_tips"))
async def ad_tips_command(client: Client, message: Message):
    await ad_tips(client, message)

@app.on_message(filters.command("promo_plan"))
async def promo_plan_command(client: Client, message: Message):
    await promo_plan(client, message)

@app.on_message(filters.command("ad_feedback"))
async def ad_feedback_command(client: Client, message: Message):
    await ad_feedback(client, message)

# Команды подписки
@app.on_message(filters.command("subscription"))
async def subscription_command(client: Client, message: Message):
    await subscription_info(client, message)

@app.on_message(filters.command("upgrade_pro"))
async def upgrade_pro_command(client: Client, message: Message):
    await upgrade_pro(client, message)

# Обработчики callback'ов
@app.on_callback_query(filters.regex(r"^post_idea_cat_"))
async def post_idea_callback(client: Client, callback_query: CallbackQuery):
    await post_idea_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^popular_posts_cat_"))
async def popular_posts_callback(client: Client, callback_query: CallbackQuery):
    await popular_posts_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^post_format_type_"))
async def post_format_callback(client: Client, callback_query: CallbackQuery):
    await post_format_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^ad_ideas_cat_"))
async def ad_ideas_callback(client: Client, callback_query: CallbackQuery):
    await ad_ideas_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^promo_text_cat_"))
async def promo_text_callback(client: Client, callback_query: CallbackQuery):
    await promo_text_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^top_cta_cat_"))
async def top_cta_callback(client: Client, callback_query: CallbackQuery):
    await top_cta_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^trending_topics_cat_"))
async def trending_topics_callback(client: Client, callback_query: CallbackQuery):
    await trending_topics_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^engagement_boost_cat_"))
async def engagement_boost_callback(client: Client, callback_query: CallbackQuery):
    await engagement_boost_cat_callback(client, callback_query)

# V2 callback обработчики
@app.on_callback_query(filters.regex(r"^ad_tips_cat_"))
async def ad_tips_callback(client: Client, callback_query: CallbackQuery):
    await ad_tips_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^promo_plan_cat_"))
async def promo_plan_callback(client: Client, callback_query: CallbackQuery):
    await promo_plan_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^content_trends_cat_"))
async def content_trends_callback(client: Client, callback_query: CallbackQuery):
    await content_trends_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^trend_detective_cat_"))
async def trend_detective_callback(client: Client, callback_query: CallbackQuery):
    await trend_detective_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^falling_trends_cat_"))
async def falling_trends_callback(client: Client, callback_query: CallbackQuery):
    await falling_trends_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^trending_channels_cat_"))
async def trending_channels_callback(client: Client, callback_query: CallbackQuery):
    await trending_channels_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^best_times_cat_"))
async def best_times_callback(client: Client, callback_query: CallbackQuery):
    await best_times_cat_callback(client, callback_query)

@app.on_callback_query(filters.regex(r"^main_menu$"))
async def main_menu_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.edit_message_text(
        "🏠 ГЛАВНОЕ МЕНЮ\n\n"
        "Выберите раздел:\n\n"
        "📝 POSTS - идеи постов, популярные посты, форматы\n"
        "💰 ADS - рекламные идеи, промо-тексты, CTA\n"
        "📈 TRENDS - трендовые темы, вовлеченность\n"
        "📊 ANALYZE - анализ канала (PRO)\n"
        "💳 Подписка - информация о подписке"
    )

# Обработчики меню разделов
@app.on_callback_query(filters.regex(r"^menu_"))
async def menu_callback(client: Client, callback_query: CallbackQuery):
    """Обработчик меню разделов"""
    await callback_query.answer()
    menu_type = callback_query.data.split('_')[1]
    
    if menu_type == "posts":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💡 Идея поста", callback_data="post_idea_cat_0")],
            [InlineKeyboardButton("📊 Популярные посты", callback_data="popular_posts_cat_0")],
            [InlineKeyboardButton("📝 Формат поста", callback_data="post_format_type_0")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ])
        await callback_query.edit_message_text(
            "📝 РАЗДЕЛ: POSTS\n\n"
            "Здесь ты можешь:\n"
            "• Получить идею для поста\n"
            "• Посмотреть популярные посты\n"
            "• Узнать форматы и советы",
            reply_markup=keyboard
        )
    
    elif menu_type == "ads":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Рекламные идеи", callback_data="ad_ideas_cat_0")],
            [InlineKeyboardButton("📢 Промо-тексты", callback_data="promo_text_cat_0")],
            [InlineKeyboardButton("🔥 Топ CTA", callback_data="top_cta_cat_0")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ])
        await callback_query.edit_message_text(
            "💰 РАЗДЕЛ: ADS\n\n"
            "Здесь ты можешь:\n"
            "• Получить идеи для рекламы\n"
            "• Узнать лучшие креативы и CTA\n"
            "• Получить советы по продвижению",
            reply_markup=keyboard
        )
    
    elif menu_type == "trends":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 Трендовые темы", callback_data="trending_topics_cat_0")],
            [InlineKeyboardButton("🚀 Идеи вовлеченности", callback_data="engagement_boost_cat_0")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ])
        await callback_query.edit_message_text(
            "📈 РАЗДЕЛ: TRENDS\n\n"
            "Здесь ты можешь:\n"
            "• Узнать трендовые темы и каналы\n"
            "• Посмотреть лучшее время для постов\n"
            "• Получить идеи для вовлечённости",
            reply_markup=keyboard
        )
    
    elif menu_type == "analyze":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Сводка по каналу (PRO)", callback_data="channel_summary")],
            [InlineKeyboardButton("👥 Отчет по аудитории (PRO)", callback_data="audience_report")],
            [InlineKeyboardButton("📝 Качество контента (PRO)", callback_data="content_quality")],
            [InlineKeyboardButton("🎨 Анализ стиля (PRO)", callback_data="style_review")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ])
        await callback_query.edit_message_text(
            "📊 РАЗДЕЛ: ANALYZE (PRO)\n\n"
            "Здесь ты можешь:\n"
            "• Получить сводку по своему каналу\n"
            "• Оценить качество и стиль контента\n"
            "• Получить советы по росту",
            reply_markup=keyboard
        )
    
    elif menu_type == "subscription":
        user_id = callback_query.from_user.id
        user_info = subscription_service.get_subscription_info(user_id)
        
        remaining = user_info['remaining_requests']
        limit = user_info['daily_limit']
        is_pro = user_info['is_pro']
        
        status_text = "🔒 FREE" if not is_pro else "💎 PRO"
        
        response_text = f"📊 ИНФОРМАЦИЯ О ПОДПИСКЕ\n\n"
        response_text += f"Статус: {status_text}\n"
        response_text += f"Осталось запросов: {remaining}/{limit}\n"
        
        if is_pro:
            response_text += f"\n✅ PRO функции:\n"
            for feature in user_info['pro_features']:
                response_text += f"• {feature}\n"
        else:
            response_text += f"\n💡 Обновитесь до PRO для:\n"
            response_text += f"• Неограниченных запросов\n"
            response_text += f"• Расширенной аналитики\n"
            response_text += f"• Персональных отчетов\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Обновиться до PRO", callback_data="upgrade_pro")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback_query.edit_message_text(response_text, reply_markup=keyboard)

# Обработчики текстовых сообщений для PRO функций
@app.on_message(filters.text & ~filters.command)
async def handle_text_message(client: Client, message: Message):
    """Обрабатывает текстовые сообщения для PRO функций"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Проверяем, ожидаем ли мы текст от пользователя
    # Здесь можно добавить логику для обработки текста постов для анализа
    
    # Если это не специальный текст, игнорируем
    if len(text) < 10:  # Слишком короткий текст
        return
    
    # Проверяем, является ли пользователь PRO
    user_info = subscription_service.get_subscription_info(user_id)
    if not user_info['is_pro']:
        await message.reply_text(
            "🔒 Эта функция доступна только в PRO версии!\n\n"
            "💡 Для анализа ваших постов обновитесь до PRO."
        )
        return
    
    # Здесь можно добавить обработку текста постов для PRO функций
    # Например, анализ поста, улучшение и т.д.

if __name__ == "__main__":
    app.run() 