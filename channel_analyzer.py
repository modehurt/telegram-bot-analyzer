import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from gpt_service import gpt_service

class ChannelAnalyzer:
    def __init__(self):
        self.analysis_cache = {}
    
    async def analyze_channel_summary(self, channel_data: Dict) -> str:
        """PRO: Создает сводку по каналу"""
        try:
            prompt = f"""Создай подробную сводку по каналу на основе данных:

НАЗВАНИЕ: {channel_data.get('title', 'Неизвестно')}
ПОДПИСЧИКИ: {channel_data.get('subscribers', 0):,}
ПОСТОВ: {channel_data.get('posts_count', 0)}
СРЕДНИЕ ПРОСМОТРЫ: {channel_data.get('avg_views', 0):,}
ВОВЛЕЧЕННОСТЬ: {channel_data.get('engagement_rate', 0):.2f}%
КАТЕГОРИЯ: {channel_data.get('category', 'Не указана')}

Дай анализ в формате:
📊 СВОДКА ПО КАНАЛУ

🎯 ОБЩАЯ ОЦЕНКА:
• ...

📈 КЛЮЧЕВЫЕ МЕТРИКИ:
• ...

💡 СИЛЬНЫЕ СТОРОНЫ:
• ...

⚠️ ОБЛАСТИ ДЛЯ УЛУЧШЕНИЯ:
• ...

🚀 РЕКОМЕНДАЦИИ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа канала: {str(e)}"
    
    async def generate_audience_report(self, channel_data: Dict) -> str:
        """PRO: Создает отчет по аудитории"""
        try:
            prompt = f"""Создай детальный отчет по аудитории канала:

ДАННЫЕ КАНАЛА:
Название: {channel_data.get('title', 'Неизвестно')}
Подписчики: {channel_data.get('subscribers', 0):,}
Активные пользователи: {channel_data.get('active_users_percent', 0):.1f}%
Молчаливые пользователи: {channel_data.get('silent_users_percent', 0):.1f}%
Новые подписчики: {channel_data.get('new_followers', 0)}
Потерянные подписчики: {channel_data.get('lost_followers', 0)}

Создай отчет в формате:
👥 ОТЧЕТ ПО АУДИТОРИИ

📊 ДЕМОГРАФИЯ:
• ...

🎯 ПОВЕДЕНИЕ АУДИТОРИИ:
• ...

📈 ДИНАМИКА РОСТА:
• ...

💡 ИНСАЙТЫ:
• ...

🚀 СТРАТЕГИИ РАБОТЫ С АУДИТОРИЕЙ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка создания отчета по аудитории: {str(e)}"
    
    async def analyze_content_quality(self, posts_data: List[Dict]) -> str:
        """PRO: Анализирует качество контента"""
        if not posts_data:
            return "Нет данных для анализа качества контента."
        
        try:
            # Анализируем посты
            total_posts = len(posts_data)
            posts_with_images = len([p for p in posts_data if p.get('has_image')])
            avg_views = sum(p.get('views', 0) for p in posts_data) / total_posts if total_posts > 0 else 0
            avg_reactions = sum(p.get('reactions', 0) for p in posts_data) / total_posts if total_posts > 0 else 0
            
            # Топ посты
            top_posts = sorted(posts_data, key=lambda x: x.get('views', 0), reverse=True)[:5]
            
            prompt = f"""Проанализируй качество контента канала:

СТАТИСТИКА:
Всего постов: {total_posts}
Постов с изображениями: {posts_with_images} ({posts_with_images/total_posts*100:.1f}%)
Средние просмотры: {avg_views:,.0f}
Средние реакции: {avg_reactions:.1f}

ТОП-5 ПОСТОВ:
{chr(10).join([f"{i+1}. {p.get('views', 0):,} просмотров | {p.get('text', '')[:100]}..." for i, p in enumerate(top_posts)])}

Дай анализ качества в формате:
📝 АНАЛИЗ КАЧЕСТВА КОНТЕНТА

📊 ОБЩАЯ ОЦЕНКА: X/10

🎯 СИЛЬНЫЕ СТОРОНЫ:
• ...

⚠️ СЛАБЫЕ МЕСТА:
• ...

💡 РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ:
• ...

📈 ПЛАН РАЗВИТИЯ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа качества контента: {str(e)}"
    
    async def analyze_style_review(self, posts_data: List[Dict]) -> str:
        """PRO: Анализирует стиль контента"""
        if not posts_data:
            return "Нет данных для анализа стиля контента."
        
        try:
            # Анализируем стилистические особенности
            text_samples = [p.get('text', '')[:200] for p in posts_data[:10]]
            
            prompt = f"""Проанализируй стиль контента канала:

ОБРАЗЦЫ ТЕКСТОВ:
{chr(10).join([f"{i+1}. {text}" for i, text in enumerate(text_samples)])}

Дай анализ стиля в формате:
🎨 АНАЛИЗ СТИЛЯ КОНТЕНТА

📝 ТОН И ГОЛОС:
• ...

🎯 ЦЕЛЕВАЯ АУДИТОРИЯ:
• ...

💬 СТИЛИСТИЧЕСКИЕ ОСОБЕННОСТИ:
• ...

✅ ЧТО РАБОТАЕТ:
• ...

⚠️ ЧТО МОЖНО УЛУЧШИТЬ:
• ...

🚀 РЕКОМЕНДАЦИИ ПО СТИЛЮ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа стиля: {str(e)}"
    
    async def generate_growth_tips(self, channel_data: Dict, posts_data: List[Dict]) -> str:
        """PRO: Генерирует советы по росту канала"""
        try:
            # Анализируем текущие показатели
            avg_views = sum(p.get('views', 0) for p in posts_data) / len(posts_data) if posts_data else 0
            engagement_rate = channel_data.get('engagement_rate', 0)
            subscribers = channel_data.get('subscribers', 0)
            
            prompt = f"""Создай персональные советы по росту канала:

ТЕКУЩИЕ ПОКАЗАТЕЛИ:
Подписчики: {subscribers:,}
Средние просмотры: {avg_views:,.0f}
Вовлеченность: {engagement_rate:.2f}%
Категория: {channel_data.get('category', 'Не указана')}

Дай советы в формате:
🚀 СОВЕТЫ ПО РОСТУ КАНАЛА

📈 КРАТКОСРОЧНЫЕ ЦЕЛИ (1-2 недели):
• ...

🎯 СРЕДНЕСРОЧНЫЕ ЦЕЛИ (1-2 месяца):
• ...

🌟 ДОЛГОСРОЧНЫЕ ЦЕЛИ (3-6 месяцев):
• ...

💡 КОНКРЕТНЫЕ ДЕЙСТВИЯ:
• ...

📊 KPI ДЛЯ ОТСЛЕЖИВАНИЯ:
• ...

🎯 ПРИОРИТЕТНЫЕ ЗАДАЧИ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка генерации советов по росту: {str(e)}"
    
    async def analyze_trending_channels(self, category: str) -> str:
        """PRO: Анализирует трендовые каналы в категории"""
        try:
            prompt = f"""Создай анализ трендовых каналов в категории "{category}":

Включи:
• 5-7 самых популярных каналов
• Их ключевые особенности
• Секреты успеха
• Что можно перенять
• Тренды в категории

Ответ в формате:
🔥 ТРЕНДОВЫЕ КАНАЛЫ В {category.upper()}

📊 ТОП КАНАЛОВ:
1. [Название канала]
   • Подписчики: X
   • Особенности: ...
   • Секреты успеха: ...

2. [Название канала]
   • Подписчики: X
   • Особенности: ...
   • Секреты успеха: ...

💡 ЧТО МОЖНО ПЕРЕНЯТЬ:
• ...

🎯 ТРЕНДЫ В КАТЕГОРИИ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа трендовых каналов: {str(e)}"
    
    async def analyze_best_times(self, category: str, posts_data: List[Dict]) -> str:
        """PRO: Анализирует лучшее время для публикаций"""
        if not posts_data:
            return "Нет данных для анализа времени публикаций."
        
        try:
            # Анализируем время публикаций (если есть данные)
            prompt = f"""Создай рекомендации по лучшему времени публикаций для категории "{category}":

Включи:
• Лучшие дни недели
• Оптимальные часы
• Сезонные особенности
• Особенности аудитории
• Конкретные рекомендации

Ответ в формате:
⏰ ЛУЧШЕЕ ВРЕМЯ ДЛЯ ПУБЛИКАЦИЙ

📅 ПО ДНЯМ НЕДЕЛИ:
• Понедельник: ...
• Вторник: ...
• ...

🕐 ПО ЧАСАМ:
• Утро (6:00-12:00): ...
• День (12:00-18:00): ...
• Вечер (18:00-24:00): ...

📊 ОСОБЕННОСТИ АУДИТОРИИ:
• ...

🎯 КОНКРЕТНЫЕ РЕКОМЕНДАЦИИ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа времени публикаций: {str(e)}"
    
    async def detect_content_trends(self, category: str) -> str:
        """PRO: Детектирует тренды контента"""
        try:
            prompt = f"""Создай анализ трендов контента для категории "{category}":

Включи:
• Актуальные тренды
• Форматы, которые набирают популярность
• Темы, которые обсуждаются
• Новые подходы к контенту
• Прогнозы на будущее

Ответ в формате:
📈 ТРЕНДЫ КОНТЕНТА В {category.upper()}

🔥 АКТУАЛЬНЫЕ ТРЕНДЫ:
• ...

📱 ПОПУЛЯРНЫЕ ФОРМАТЫ:
• ...

💬 ТЕМЫ ДЛЯ ОБСУЖДЕНИЯ:
• ...

🚀 НОВЫЕ ПОДХОДЫ:
• ...

🔮 ПРОГНОЗЫ НА БУДУЩЕЕ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка детекции трендов: {str(e)}"
    
    async def analyze_falling_trends(self, category: str) -> str:
        """PRO: Анализирует падающие тренды"""
        try:
            prompt = f"""Создай анализ падающих трендов для категории "{category}":

Включи:
• Что теряет популярность
• Устаревшие форматы
• Темы, которые перестали работать
• Причины падения трендов
• Как адаптироваться

Ответ в формате:
📉 ПАДАЮЩИЕ ТРЕНДЫ В {category.upper()}

❌ ЧТО ТЕРЯЕТ ПОПУЛЯРНОСТЬ:
• ...

📱 УСТАРЕВШИЕ ФОРМАТЫ:
• ...

💬 ТЕМЫ, КОТОРЫЕ НЕ РАБОТАЮТ:
• ...

🔍 ПРИЧИНЫ ПАДЕНИЯ:
• ...

🔄 КАК АДАПТИРОВАТЬСЯ:
• ..."""

            response = await asyncio.to_thread(
                gpt_service.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа падающих трендов: {str(e)}"

# Глобальный экземпляр анализатора каналов
channel_analyzer = ChannelAnalyzer() 