import asyncio
import json
import re
from openai import OpenAI
from config import OPENAI_API_KEY
from data_analyzer import data_analyzer

client = OpenAI(api_key=OPENAI_API_KEY)

class GPTService:
    def __init__(self):
        self.client = client
    
    def validate_input(self, text: str) -> bool:
        """Проверяет, является ли ввод осмысленным"""
        if not text or len(text.strip()) < 3:
            return False
        
        # Проверяем на бессмысленные символы
        if re.match(r'^[^\w\s]+$', text.strip()):
            return False
        
        # Проверяем на повторяющиеся символы
        if len(set(text.strip())) < 3:
            return False
        
        return True
    
    async def generate_post_idea(self, category: str, additional_info: str = "") -> str:
        """Генерирует идею поста для заданной категории"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем реальные данные из БД для контекста
            trending_data = await data_analyzer.get_trending_topics(category, days=7)
            popular_posts = await data_analyzer.get_popular_posts_by_category(category, limit=5)
            
            # Формируем контекст на основе реальных данных
            context = ""
            if trending_data:
                context += f"\nАктуальные тренды в теме '{category}':\n"
                for trend in trending_data[:3]:
                    context += f"• {trend.get('topic', 'Н/Д')} - {trend.get('posts_count', 0)} постов\n"
            
            if popular_posts:
                context += f"\nПопулярные форматы в теме '{category}':\n"
                formats = {}
                for post in popular_posts:
                    fmt = post.get('format', 'unknown')
                    formats[fmt] = formats.get(fmt, 0) + 1
                for fmt, count in sorted(formats.items(), key=lambda x: x[1], reverse=True)[:3]:
                    context += f"• {fmt} - {count} постов\n"
            
            prompt = f"""Сгенерируй идею для поста в Telegram-канале на тему: «{category}».

Если тема не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Если это не конкретная тема, но из нее можно определить нишу (финансы, психология и т.п.), укажи ее.

Контекст на основе реальных данных:{context}

Дай:
• Краткий заголовок
• Основную мысль поста
• Рекомендуемый формат (сторителлинг, список, факт/вопрос, и т.п.)
• Советы по подаче (тон, структура, интерактив)

Ответ в формате:
  Идея: ...
  Суть: ...
  Формат: ...
  Советы: ..."""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка генерации идеи: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."
    
    async def generate_post_idea_pro(self, category: str, user_id: int) -> str:
        """Генерирует идею поста для PRO пользователей с анализом канала"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные о каналах пользователя
            user_channels = await data_analyzer.get_user_channels(user_id)
            channel_data = []
            
            if user_channels:
                for channel in user_channels[:3]:  # Берем первые 3 канала
                    posts = await data_analyzer.get_channel_posts(channel['channel_id'], limit=5)
                    if posts:
                        channel_data.append({
                            'title': channel.get('title', 'Н/Д'),
                            'description': channel.get('description', ''),
                            'posts': posts
                        })
            
            # Формируем контекст на основе каналов пользователя
            context = ""
            if channel_data:
                context += "\n\n**Информация о ваших каналах:**\n"
                for i, channel in enumerate(channel_data, 1):
                    context += f"\n{i}. **{channel['title']}**\n"
                    if channel['description']:
                        context += f"Описание: {channel['description']}\n"
                    
                    # Анализируем лучшие посты
                    top_posts = sorted(channel['posts'], key=lambda x: x.get('views', 0), reverse=True)[:2]
                    if top_posts:
                        context += "Лучшие посты:\n"
                        for post in top_posts:
                            views = post.get('views', 0)
                            text = post.get('text', '')[:100] + "..." if len(post.get('text', '')) > 100 else post.get('text', '')
                            er = post.get('er', 0)
                            context += f"• {text} (просмотры: {views}, ER: {er:.2f}%)\n"
            
            # Получаем тренды и популярные посты
            trending_data = await data_analyzer.get_trending_topics(category, days=7)
            popular_posts = await data_analyzer.get_popular_posts_by_category(category, limit=5)
            
            if trending_data:
                context += f"\n\n**Актуальные тренды в теме '{category}':**\n"
                for trend in trending_data[:3]:
                    context += f"• {trend.get('topic', 'Н/Д')} - {trend.get('posts_count', 0)} постов\n"
            
            if popular_posts:
                context += f"\n**Популярные форматы в теме '{category}':**\n"
                formats = {}
                for post in popular_posts:
                    fmt = post.get('format', 'unknown')
                    formats[fmt] = formats.get(fmt, 0) + 1
                for fmt, count in sorted(formats.items(), key=lambda x: x[1], reverse=True)[:3]:
                    context += f"• {fmt} - {count} постов\n"
            
            prompt = f"""Ты — эксперт по созданию контента для Telegram-каналов. Создай идею для поста на тему: «{category}».

{context}

**Требования к ответу:**
1. Учитывай стиль и формат постов из каналов пользователя
2. Анализируй тренды и популярные форматы в теме
3. Предложи уникальную идею, которая будет выделяться

**Структура ответа:**
**Идея:** [Краткий заголовок]
**Суть:** [Основная мысль поста]
**Формат:** [Рекомендуемый формат: сторителлинг, список, факт/вопрос, и т.п.]
**Советы:** [Советы по подаче: тон, структура, интерактив]
**Почему сработает:** [Обоснование на основе анализа данных]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка генерации PRO идеи: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."
    
    async def analyze_popular_posts(self, category: str, posts_data: list) -> str:
        """Анализирует популярные посты и дает рекомендации"""
        if not posts_data:
            return "Нет данных для анализа популярных постов."
        
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Подготавливаем данные для GPT в формате ТЗ
            top_posts = sorted(posts_data, key=lambda x: x.get('views', 0), reverse=True)[:5]
            posts_json = []
            
            for post in top_posts:
                views = post.get('views', 0)
                text = post.get('text', '')[:100] + "..." if len(post.get('text', '')) > 100 else post.get('text', '')
                er = post.get('er', 0)
                format_type = post.get('format', 'unknown')
                
                posts_json.append({
                    "title": text[:50] + "..." if len(text) > 50 else text,
                    "description": f"Пост в формате {format_type}",
                    "views": views,
                    "ER": f"{er:.1f}%",
                    "category": category.lower()
                })
            
            posts_str = ",\n".join([json.dumps(post, ensure_ascii=False) for post in posts_json])
            
            prompt = f"""Ты — эксперт по контенту в Telegram. У тебя есть список популярных постов из каналов на тему {category}.
Если тема не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Если это не конкретная тема, но из нее можно определить нишу (финансы, психология и т.п.), укажи ее.

Проанализируй их и оформи подборку лучших постов красиво и понятно для пользователя
Telegram-бота.

Сформируй:
• Заголовок и краткое описание каждого поста
• Укажи тему и уровень вовлеченности (ER)
• В конце — сделай вывод: что общего между этими постами и какой формат сейчас работает

Вот список постов:
{posts_str}"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа постов: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."
    
    async def suggest_post_format(self, format_type: str, topic: str = "") -> str:
        """Предлагает формат поста"""
        try:
            # Получаем реальные примеры постов в этом формате
            examples = await data_analyzer.get_popular_posts_by_category(topic if topic else "Общие", limit=10)
            format_examples = [p for p in examples if p.get('format') == format_type][:3]
            
            context = ""
            if format_examples:
                context += f"\nПримеры успешных постов в формате '{format_type}':\n"
                for i, example in enumerate(format_examples, 1):
                    text = example.get('text', '')[:100] + "..." if len(example.get('text', '')) > 100 else example.get('text', '')
                    views = example.get('views', 0)
                    context += f"{i}. {views:,} просмотров | {text}\n"
            
            prompt = f"""Ты — эксперт по продвижению Telegram-каналов. Пользователь хочет получить советы по структуре поста в формате "{format_type}".

Если формат не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите формат или переформулируйте.", "show_formats": true
}}

Контекст на основе реальных данных:{context}

Объясни:
• Что такое формат "{format_type}"
• Как правильно структурировать пост в этом формате
• Какие элементы обязательны
• Советы по написанию
• Примеры использования

Ответ должен быть структурированным и практичным."""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка генерации объяснения формата: {str(e)}\n\nПопробуйте другой формат или обратитесь в поддержку."
    
    async def analyze_post_feedback(self, post_text: str, category: str = "") -> str:
        """Анализирует пост пользователя и дает обратную связь"""
        try:
            if not self.validate_input(post_text):
                return "❌ Текст поста слишком короткий или не содержит осмысленного контента."
            
            # Получаем контекст из БД для сравнения
            context = ""
            if category:
                popular_posts = await data_analyzer.get_popular_posts_by_category(category, limit=3)
                if popular_posts:
                    context += f"\nДля сравнения, популярные посты в теме '{category}':\n"
                    for i, post in enumerate(popular_posts, 1):
                        text = post.get('text', '')[:50] + "..." if len(post.get('text', '')) > 50 else post.get('text', '')
                        context += f"{i}. {text}\n"
            
            prompt = f"""Ты — эксперт по контенту в Telegram. Проанализируй пост пользователя и дай детальную обратную связь.

Пост пользователя:
{post_text}

Контекст для сравнения:{context}

Проведи анализ по критериям:
1. Заголовок (цепляет ли внимание)
2. Основная мысль (понятна ли)
3. Структура и логика
4. Эмоциональное воздействие
5. Призыв к действию
6. Технические аспекты

Для каждого критерия дай:
• Оценку (1-10)
• Что хорошо
• Что можно улучшить
• Конкретные рекомендации

В конце дай общую оценку и 3 главных совета для улучшения."""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа поста: {str(e)}\n\nПопробуйте еще раз или обратитесь в поддержку."
    
    async def rewrite_post(self, post_text: str, style: str = "improved", category: str = "") -> str:
        """Улучшает пост пользователя"""
        try:
            if not self.validate_input(post_text):
                return "❌ Текст поста слишком короткий или не содержит осмысленного контента."
            
            # Получаем контекст из БД
            context = ""
            if category:
                popular_posts = await data_analyzer.get_popular_posts_by_category(category, limit=2)
                if popular_posts:
                    context += f"\nУчитывая успешные посты в теме '{category}':\n"
                    for post in popular_posts:
                        text = post.get('text', '')[:100] + "..." if len(post.get('text', '')) > 100 else post.get('text', '')
                        context += f"• {text}\n"
            
            prompt = f"""Ты — эксперт по контенту в Telegram. Улучши пост пользователя, сделав его более привлекательным и эффективным.

Оригинальный пост:
{post_text}

Контекст для улучшения:{context}

Создай улучшенную версию с:
• Более цепляющим заголовком
• Лучшей структурой
• Усиленным призывом к действию
• Добавлением эмодзи где уместно
• Повышением эмоциональности
• Сохранением основной мысли

Представь результат в формате:
📝 УЛУЧШЕННАЯ ВЕРСИЯ:

[улучшенный текст]

🔧 ЧТО ИЗМЕНЕНО:
• [список изменений]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка улучшения поста: {str(e)}\n\nПопробуйте еще раз или обратитесь в поддержку."
    
    async def generate_ad_ideas(self, category: str, product_info: str = "") -> str:
        """Генерирует рекламные идеи"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем реальные данные о рекламных креативах
            creatives = await data_analyzer.get_successful_creatives_by_category(category, limit=5)
            
            context = ""
            if creatives:
                context += f"\nУспешные рекламные креативы в теме '{category}':\n"
                for i, creative in enumerate(creatives, 1):
                    title = creative.get('ad_title', '')[:50] + "..." if len(creative.get('ad_title', '')) > 50 else creative.get('ad_title', '')
                    context += f"{i}. {title}\n"
            
            prompt = f"""Ты — маркетолог, специализирующийся на создании рекламных креативов для Telegram Ads. Создай 3 рекламные идеи для продвижения в теме "{category}".

Если тема не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай 3 рекламные идеи:
1. КЕЙС-ИСТОРИЯ - история успеха клиента
2. ПРОБЛЕМА-РЕШЕНИЕ - решение боли аудитории  
3. ОБЗОР И ЛИЧНЫЙ ОПЫТ - личный опыт эксперта

Для каждой идеи укажи:
• Заголовок
• Основную мысль
• Пример текста
• Целевую аудиторию
• Ожидаемый результат

Учитывай особенности Telegram-аудитории и тренды в теме."""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка генерации рекламных идей: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."
    
    async def generate_promo_text(self, category: str, product_info: str = "") -> str:
        """Генерирует промо-тексты для продвижения канала"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем реальные данные о промо-текстах
            promo_examples = await data_analyzer.get_successful_creatives_by_category(category, limit=3)
            
            context = ""
            if promo_examples:
                context += f"\nУспешные промо-тексты в теме '{category}':\n"
                for example in promo_examples:
                    text = example.get('ad_text', '')[:100] + "..." if len(example.get('ad_text', '')) > 100 else example.get('ad_text', '')
                    context += f"• {text}\n"
            
            prompt = f"""Ты — маркетолог, специализирующийся на создании рекламных креативов для Telegram Ads. Создай промо-текст для продвижения канала в теме "{category}".

Если тема не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай промо-текст который:
• Цепляет с первых строк (хороший "хук")
• Структурирован (интрига → ценность → призыв)
• Понятен и краток (до ~150 символов)
• Содержит конкретный call-to-action
• Подходит для Telegram-аудитории

Представь результат в формате:
📢 ПРОМО-ТЕКСТ:

[текст]

🎯 ЦЕЛЕВАЯ АУДИТОРИЯ: [описание]
💡 КЛЮЧЕВЫЕ ПРЕИМУЩЕСТВА: [список]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка генерации промо-текста: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."
    
    async def analyze_top_cta(self, category: str, posts_data: list) -> str:
        """Анализирует лучшие CTA по теме"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Извлекаем CTA из постов
            cta_examples = []
            for post in posts_data:
                cta = post.get('cta', '')
                if cta and len(cta.strip()) > 5:
                    views = post.get('views', 0)
                    cta_examples.append({
                        'cta': cta,
                        'views': views,
                        'er': post.get('er', 0)
                    })
            
            # Сортируем по эффективности
            cta_examples.sort(key=lambda x: x['views'] * x['er'], reverse=True)
            
            context = ""
            if cta_examples:
                context += f"\nЛучшие CTA в теме '{category}':\n"
                for i, cta in enumerate(cta_examples[:5], 1):
                    context += f"{i}. '{cta['cta']}' - {cta['views']:,} просмотров, ER: {cta['er']:.1f}%\n"
            
            prompt = f"""Ты — копирайтер, эксперт в написании Call-to-Action для постов и рекламы в Telegram.
На основе темы "{category}" и реальных данных, подбери 7 лучших вариантов CTA — фраз, которые:
• Короткие и цепляющие
• Побуждают к действию (подписаться, перейти, написать, проголосовать и т.п.)
• Подходят для размещения в конце поста, в кнопке, или в рекламном сообщении

Если тема не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Сгенерируй 7 лучших CTA для темы "{category}" в формате:

🔥 ТОП-7 CTA ДЛЯ ТЕМЫ "{category.upper()}":

1. [CTA вариант]
2. [CTA вариант]
...
7. [CTA вариант]

💡 СОВЕТЫ ПО ИСПОЛЬЗОВАНИЮ:
• [советы по применению]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа CTA: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."
    
    async def generate_trending_topics(self, category: str) -> str:
        """Генерирует анализ трендовых тем"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем реальные данные о трендах
            trending_data = await data_analyzer.get_trending_topics(category, days=7)
            
            if not trending_data:
                return f"📈 ТРЕНДОВЫЕ ТЕМЫ\n\nКатегория: {category}\n\n❌ Нет данных для анализа трендов за последние 7 дней.\n\nПопробуйте:\n• Другую категорию\n• Более широкий период\n• Добавьте больше каналов в базу"
            
            # Подготавливаем данные для GPT
            trends_summary = []
            for trend in trending_data[:5]:
                trends_summary.append({
                    'topic': trend.get('topic', 'Н/Д'),
                    'posts_count': trend.get('posts_count', 0),
                    'total_views': trend.get('total_views', 0),
                    'avg_er': trend.get('avg_er', 0),
                    'ad_percentage': trend.get('ad_percentage', 0)
                })
            
            trends_str = "\n".join([
                f"• {t['topic']} - {t['posts_count']} постов, {t['total_views']:,} просмотров, ER: {t['avg_er']:.1f}%"
                for t in trends_summary
            ])
            
            prompt = f"""Ты — эксперт по анализу трендов в Telegram. Проанализируй трендовые темы в категории "{category}" за последние 7 дней.

Если категория не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Данные о трендах:
{trends_str}

Создай анализ в формате:

📈 ТРЕНДОВЫЕ ТЕМЫ В КАТЕГОРИИ "{category.upper()}"

🔥 ТОП-5 ТРЕНДОВ:
[пронумерованный список с описанием каждого тренда]

📊 СТАТИСТИКА:
• Общее количество постов: [число]
• Средний ER: [число]%
• Процент рекламных постов: [число]%

💡 ВЫВОДЫ:
• [основные выводы о трендах]
• [рекомендации для контент-мейкеров]
• [прогноз на ближайшее время]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа трендов: {str(e)}\n\nПопробуйте другую категорию или обратитесь в поддержку."
    
    async def suggest_engagement_boost(self, category: str, current_engagement: str = "") -> str:
        """Предлагает идеи для повышения вовлеченности"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные о вовлеченности из БД
            engagement_data = await data_analyzer.get_engagement_analysis(category)
            
            context = ""
            if engagement_data:
                avg_er = engagement_data.get('avg_er', 0)
                best_formats = engagement_data.get('best_formats', [])
                context += f"\nТекущая статистика вовлеченности в теме '{category}':\n"
                context += f"• Средний ER: {avg_er:.1f}%\n"
                if best_formats:
                    context += f"• Лучшие форматы: {', '.join(best_formats[:3])}\n"
            
            prompt = f"""Ты — эксперт по повышению вовлеченности в Telegram-каналах. Предложи идеи для повышения вовлеченности в теме "{category}".

Если тема не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай план повышения вовлеченности в формате:

🚀 ИДЕИ ДЛЯ ПОВЫШЕНИЯ ВОВЛЕЧЕННОСТИ

📝 КОНТЕНТНЫЕ СТРАТЕГИИ:
• [3-4 идеи по улучшению контента]

🎯 ИНТЕРАКТИВНЫЕ ЭЛЕМЕНТЫ:
• [3-4 идеи для взаимодействия с аудиторией]

⏰ ТЕХНИЧЕСКИЕ ПРИЕМЫ:
• [3-4 технических приема]

📊 ИЗМЕРЕНИЕ РЕЗУЛЬТАТОВ:
• [метрики для отслеживания прогресса]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка генерации идей вовлеченности: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."

    # --- V2 МЕТОДЫ ---
    async def generate_ad_tips(self, category: str) -> str:
        """V2: Генерирует советы по рекламе"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные о рекламных креативах
            creatives = await data_analyzer.get_successful_creatives_by_category(category, limit=5)
            
            context = ""
            if creatives:
                context += f"\nУспешные рекламные креативы в теме '{category}':\n"
                for i, creative in enumerate(creatives, 1):
                    title = creative.get('ad_title', '')[:50] + "..." if len(creative.get('ad_title', '')) > 50 else creative.get('ad_title', '')
                    context += f"{i}. {title}\n"
            
            prompt = f"""Ты — эксперт по рекламе в Telegram. Создай практические советы по созданию эффективной рекламы для темы "{category}".

Если тема не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай советы в формате:

💡 СОВЕТЫ ПО РЕКЛАМЕ (V2)

🎯 ЦЕЛЕВАЯ АУДИТОРИЯ:
• [описание целевой аудитории]

📝 СТРУКТУРА РЕКЛАМНОГО ПОСТА:
• [элементы эффективного рекламного поста]

🔥 ПРИЕМЫ ПРИВЛЕЧЕНИЯ ВНИМАНИЯ:
• [3-4 приема для цепляющих заголовков]

💬 ПРИЗЫВЫ К ДЕЙСТВИЮ:
• [эффективные CTA для темы]

⚠️ ЧАСТЫЕ ОШИБКИ:
• [что избегать при создании рекламы]

✅ ЛУЧШИЕ ПРАКТИКИ:
• [проверенные методы]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка генерации советов по рекламе: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."

    async def generate_promo_plan(self, category: str) -> str:
        """V2: Генерирует план продвижения"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные о трендах
            trending_data = await data_analyzer.get_trending_topics(category, days=7)
            
            context = ""
            if trending_data:
                context += f"\nАктуальные тренды в теме '{category}':\n"
                for trend in trending_data[:3]:
                    context += f"• {trend.get('topic', 'Н/Д')} - {trend.get('posts_count', 0)} постов\n"
            
            prompt = f"""Ты — маркетолог, специализирующийся на продвижении в Telegram. Создай комплексный план продвижения для темы "{category}".

Если тема не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай план в формате:

📋 ПЛАН ПРОДВИЖЕНИЯ (V2)

🎯 ЦЕЛИ И ЗАДАЧИ:
• [конкретные цели продвижения]

📅 КАЛЕНДАРЬ ПРОДВИЖЕНИЯ:
• Неделя 1: [действия]
• Неделя 2: [действия]
• Неделя 3: [действия]
• Неделя 4: [действия]

💰 РЕКЛАМНЫЙ БЮДЖЕТ:
• [распределение бюджета]

📊 КАНАЛЫ ПРОДВИЖЕНИЯ:
• [список каналов и стратегий]

📈 KPI И МЕТРИКИ:
• [ключевые показатели эффективности]

🔄 A/B ТЕСТИРОВАНИЕ:
• [планы тестирования]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка создания плана продвижения: {str(e)}\n\nПопробуйте другую тему или обратитесь в поддержку."

    async def analyze_content_trends(self, category: str) -> str:
        """V2: Анализирует тренды контента"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные о трендах контента
            content_data = await data_analyzer.analyze_content_trends(category)
            
            context = ""
            if content_data:
                formats = content_data.get('formats', [])
                if formats:
                    context += f"\nПопулярные форматы в теме '{category}':\n"
                    for fmt in formats[:3]:
                        context += f"• {fmt.get('format', 'Н/Д')} - {fmt.get('count', 0)} постов, ER: {fmt.get('avg_er', 0):.1f}%\n"
            
            prompt = f"""Ты — эксперт по анализу контент-трендов в Telegram. Проанализируй тренды контента для категории "{category}".

Если категория не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай анализ в формате:

📈 ТРЕНДЫ КОНТЕНТА (V2)

🔥 ПОПУЛЯРНЫЕ ФОРМАТЫ:
• [анализ популярных форматов]

📱 НОВЫЕ ТРЕНДЫ:
• [новые подходы к контенту]

💬 ТЕМЫ ДЛЯ ОБСУЖДЕНИЯ:
• [актуальные темы]

🚀 ИННОВАЦИОННЫЕ ПОДХОДЫ:
• [креативные решения]

🔮 ПРОГНОЗЫ:
• [прогнозы развития трендов]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа трендов контента: {str(e)}\n\nПопробуйте другую категорию или обратитесь в поддержку."

    async def analyze_trend_detective(self, category: str) -> str:
        """V2: Тренд-детектив анализ"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные для детектива
            trending_data = await data_analyzer.get_trending_topics(category, days=7)
            falling_data = await data_analyzer.get_falling_trends(category)
            
            context = ""
            if trending_data:
                context += f"\nТоп-3 тренда в '{category}':\n"
                for trend in trending_data[:3]:
                    context += f"• {trend.get('topic', 'Н/Д')} - {trend.get('posts_count', 0)} постов\n"
            
            if falling_data:
                context += f"\nПадающие тренды в '{category}':\n"
                for trend in falling_data[:2]:
                    context += f"• {trend.get('format', 'Н/Д')} - спад на {trend.get('decline_percent', 0):.1f}%\n"
            
            prompt = f"""Ты — тренд-детектив, эксперт по выявлению скрытых трендов в Telegram. Проведи детективное исследование трендов для категории "{category}".

Если категория не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай детективное исследование в формате:

🔍 ТРЕНД-ДЕТЕКТИВ (V2)

🕵️ СКРЫТЫЕ ТРЕНДЫ:
• [неочевидные тренды, которые вы обнаружили]

🔍 ПРИЗНАКИ РОСТА:
• [сигналы растущих трендов]

⚠️ ПРЕДУПРЕЖДАЮЩИЕ СИГНАЛЫ:
• [признаки падающих трендов]

💡 ИНСАЙТЫ:
• [неожиданные выводы]

🎯 РЕКОМЕНДАЦИИ:
• [что делать с полученной информацией]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка тренд-детектива: {str(e)}\n\nПопробуйте другую категорию или обратитесь в поддержку."

    async def analyze_falling_trends(self, category: str) -> str:
        """V2: Анализирует падающие тренды"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные о падающих трендах
            falling_data = await data_analyzer.get_falling_trends(category)
            
            context = ""
            if falling_data:
                context += f"\nПадающие тренды в '{category}':\n"
                for trend in falling_data[:3]:
                    context += f"• {trend.get('format', 'Н/Д')} - спад на {trend.get('decline_percent', 0):.1f}%\n"
            
            prompt = f"""Ты — эксперт по анализу падающих трендов в Telegram. Проанализируй падающие тренды для категории "{category}".

Если категория не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай анализ в формате:

📉 ПАДАЮЩИЕ ТРЕНДЫ (V2)

❌ ЧТО ТЕРЯЕТ ПОПУЛЯРНОСТЬ:
• [список падающих трендов]

📱 УСТАРЕВШИЕ ФОРМАТЫ:
• [форматы, которые больше не работают]

💬 ТЕМЫ, КОТОРЫЕ НЕ РАБОТАЮТ:
• [темы с низкой вовлеченностью]

🔍 ПРИЧИНЫ ПАДЕНИЯ:
• [анализ причин]

🔄 КАК АДАПТИРОВАТЬСЯ:
• [стратегии адаптации]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа падающих трендов: {str(e)}\n\nПопробуйте другую категорию или обратитесь в поддержку."

    async def analyze_trending_channels(self, category: str) -> str:
        """V2: Анализирует трендовые каналы"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные о трендовых каналах
            channels_data = await data_analyzer.get_trending_channels(category, days=7)
            
            context = ""
            if channels_data:
                context += f"\nТрендовые каналы в '{category}':\n"
                for channel in channels_data[:3]:
                    context += f"• {channel.get('title', 'Н/Д')} - {channel.get('subscribers', 0):,} подписчиков\n"
            
            prompt = f"""Ты — эксперт по анализу Telegram-каналов. Проанализируй трендовые каналы в категории "{category}".

Если категория не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай анализ в формате:

🔥 ТРЕНДОВЫЕ КАНАЛЫ (V2)

📊 ТОП КАНАЛОВ:
• [анализ лучших каналов]

🎯 СЕКРЕТЫ УСПЕХА:
• [что делает эти каналы успешными]

💡 ЧТО МОЖНО ПЕРЕНЯТЬ:
• [идеи для собственного канала]

📈 ТРЕНДЫ В КАТЕГОРИИ:
• [общие тренды среди каналов]

🚀 РЕКОМЕНДАЦИИ:
• [как применить полученные знания]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа трендовых каналов: {str(e)}\n\nПопробуйте другую категорию или обратитесь в поддержку."

    async def analyze_best_times(self, category: str) -> str:
        """V2: Анализирует лучшее время для публикаций"""
        try:
            # Валидация входных данных согласно ТЗ
            if not self.validate_input(category):
                return json.dumps({
                    "status": "error",
                    "message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.",
                    "show_categories": True
                }, ensure_ascii=False)
            
            # Получаем данные о лучшем времени
            times_data = await data_analyzer.get_best_posting_times(category)
            
            context = ""
            if times_data:
                best_hours = times_data.get('best_hours', [])
                best_days = times_data.get('best_days', [])
                if best_hours:
                    context += f"\nЛучшие часы в '{category}':\n"
                    for hour in best_hours:
                        context += f"• {hour.get('hour', 0)}:00 - ER: {hour.get('avg_er', 0):.1f}%\n"
                if best_days:
                    context += f"\nЛучшие дни в '{category}':\n"
                    for day in best_days:
                        context += f"• {day.get('day', 'Н/Д')} - ER: {day.get('avg_er', 0):.1f}%\n"
            
            prompt = f"""Ты — эксперт по таймингу публикаций в Telegram. Проанализируй лучшее время для публикаций в категории "{category}".

Если категория не содержит осмысленного текста, является бессмысленным набором символов, абракадаброй или не поддается интерпретации, отправь именно такой JSON:

{{
"status": "error",
"message": "Запрос не распознан. Пожалуйста, выберите категорию или переформулируйте.", "show_categories": true
}}

Контекст на основе реальных данных:{context}

Создай анализ в формате:

⏰ ЛУЧШЕЕ ВРЕМЯ ДЛЯ ПУБЛИКАЦИЙ (V2)

📅 ПО ДНЯМ НЕДЕЛИ:
• [анализ по дням недели]

🕐 ПО ЧАСАМ:
• [анализ по часам]

📊 ОСОБЕННОСТИ АУДИТОРИИ:
• [поведение аудитории]

🎯 КОНКРЕТНЫЕ РЕКОМЕНДАЦИИ:
• [точное время для публикаций]

💡 СОВЕТЫ ПО ТАЙМИНГУ:
• [дополнительные рекомендации]"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка анализа времени публикаций: {str(e)}\n\nПопробуйте другую категорию или обратитесь в поддержку."

# Глобальный экземпляр GPT сервиса
gpt_service = GPTService() 