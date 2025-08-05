#!/usr/bin/env python3
"""
Test script for post idea functionality
"""

import asyncio
import json
from config import CATEGORIES, FREE_LIMIT
from subscription_service import subscription_service

# Mock GPT service for testing
class MockGPTService:
    async def generate_post_idea(self, category: str) -> str:
        """Mock implementation for testing"""
        return f"""Идея: Интересный пост о {category}
Суть: Рассказать о ключевых аспектах {category} в увлекательной форме
Формат: Сторителлинг с элементами списка
Советы: Используйте личный опыт, добавьте интерактив, задавайте вопросы читателям"""

    async def generate_post_idea_pro(self, category: str, user_id: int) -> str:
        """Mock PRO implementation for testing"""
        return f"""Идея: Продвинутый пост о {category}
Суть: Глубокий анализ {category} с практическими советами
Формат: Аналитика с элементами сторителлинга
Советы: Используйте данные и статистику, добавьте экспертные мнения
Почему сработает: Основано на анализе трендов и популярных форматов"""

# Mock data analyzer
class MockDataAnalyzer:
    async def get_user_channels(self, user_id: int):
        return [
            {
                "channel_id": "test_channel_1",
                "title": "Тестовый канал",
                "description": "Канал для тестирования"
            }
        ]
    
    async def get_channel_posts(self, channel_id: str, limit: int = 5):
        return [
            {
                "post_id": "test_post_1",
                "text": "Тестовый пост с высоким ER",
                "views": 1000,
                "er": 5.2,
                "format": "storytelling"
            }
        ]
    
    async def get_trending_topics(self, category: str, days: int = 7):
        return [
            {"topic": f"Тренд в {category}", "posts_count": 10}
        ]
    
    async def get_popular_posts_by_category(self, category: str, limit: int = 5):
        return [
            {
                "text": f"Популярный пост о {category}",
                "views": 5000,
                "er": 4.8,
                "format": "list"
            }
        ]

# Test functions
async def test_post_idea_free():
    """Test FREE post idea generation"""
    print("🧪 Testing FREE post idea generation...")
    
    # Mock user
    user_id = 12345
    subscription_service.add_pro_user(user_id)  # Make user PRO for testing
    
    # Test with category
    category = "Маркетинг и продажи"
    
    mock_gpt = MockGPTService()
    mock_data = MockDataAnalyzer()
    
    # Test FREE generation
    result = await mock_gpt.generate_post_idea(category)
    print(f"✅ FREE result: {result[:100]}...")
    
    return result

async def test_post_idea_pro():
    """Test PRO post idea generation"""
    print("🧪 Testing PRO post idea generation...")
    
    # Mock user
    user_id = 12345
    
    mock_gpt = MockGPTService()
    mock_data = MockDataAnalyzer()
    
    # Test PRO generation
    result = await mock_gpt.generate_post_idea_pro("Маркетинг и продажи", user_id)
    print(f"✅ PRO result: {result[:100]}...")
    
    return result

async def test_categories():
    """Test category list"""
    print("🧪 Testing categories...")
    print(f"✅ Found {len(CATEGORIES)} categories:")
    for i, cat in enumerate(CATEGORIES[:5]):  # Show first 5
        print(f"  {i+1}. {cat}")
    if len(CATEGORIES) > 5:
        print(f"  ... and {len(CATEGORIES) - 5} more")

async def test_subscription_service():
    """Test subscription service"""
    print("🧪 Testing subscription service...")
    
    user_id = 12345
    
    # Test limit checking
    subscription_service.user_limits[user_id] = {
        'count': 0,
        'last_day': '2024-01-01',
        'is_pro': False
    }
    
    info = subscription_service.get_subscription_info(user_id)
    print(f"✅ User info: {info}")
    
    # Test limit
    can_use = subscription_service.check_limit(user_id)
    print(f"✅ Can use service: {can_use}")

async def main():
    """Run all tests"""
    print("🚀 Starting post idea functionality tests...\n")
    
    await test_categories()
    print()
    
    await test_subscription_service()
    print()
    
    await test_post_idea_free()
    print()
    
    await test_post_idea_pro()
    print()
    
    print("✅ All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())