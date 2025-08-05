import asyncio
from gpt_service import gpt_service

async def test_gpt_functions():
    """Тестирует основные функции GPT"""
    print("🧪 Тестирование GPT функций...")
    
    # Тест 1: Генерация идеи поста
    print("\n1. Тест генерации идеи поста:")
    try:
        idea = await gpt_service.generate_post_idea("Маркетинг и продажи")
        print("✅ Успешно сгенерирована идея:")
        print(idea[:200] + "..." if len(idea) > 200 else idea)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 2: Анализ формата поста
    print("\n2. Тест анализа формата поста:")
    try:
        format_analysis = await gpt_service.suggest_post_format("Сторителлинг")
        print("✅ Успешно сгенерирован шаблон:")
        print(format_analysis[:200] + "..." if len(format_analysis) > 200 else format_analysis)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 3: Генерация рекламных идей
    print("\n3. Тест генерации рекламных идей:")
    try:
        ad_ideas = await gpt_service.generate_ad_ideas("Бизнес и стартапы")
        print("✅ Успешно сгенерированы рекламные идеи:")
        print(ad_ideas[:200] + "..." if len(ad_ideas) > 200 else ad_ideas)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 4: Генерация трендовых тем
    print("\n4. Тест генерации трендовых тем:")
    try:
        trends = await gpt_service.generate_trending_topics("Технологии и IT")
        print("✅ Успешно сгенерированы тренды:")
        print(trends[:200] + "..." if len(trends) > 200 else trends)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_gpt_functions()) 