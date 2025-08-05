import asyncio
import json
import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, func, desc, and_
from bot.db import SessionLocal, Post, PostSnapshot, Channel, ChannelSnapshot, Topic, ChannelTopic
from gpt_service import gpt_service

class DataAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 час
    
    async def get_popular_posts_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        """Получает популярные посты по категории"""
        async with SessionLocal() as session:
            # Получаем каналы по категории
            channels_query = await session.execute("""
                SELECT c.channel_id, c.title, c.username
                FROM channels c
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
            """, {"category": f"%{category}%"})
            
            channel_ids = [row.channel_id for row in channels_query]
            
            if not channel_ids:
                return []
            
            # Получаем посты с высоким ER
            posts_query = await session.execute("""
                SELECT p.post_id, p.title, p.body, p.format, p.cta, p.is_ad,
                       ps.views_count, ps.er, ps.reactions,
                       c.title as channel_title, c.username as channel_username
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                WHERE p.channel_id = ANY(:channel_ids)
                AND ps.er > 2.0  -- Минимальный ER
                AND ps.views_count > 1000  -- Минимальные просмотры
                ORDER BY ps.er DESC, ps.views_count DESC
                LIMIT :limit
            """, {"channel_ids": channel_ids, "limit": limit})
            
            posts = []
            for row in posts_query:
                post_data = {
                    "post_id": row.post_id,
                    "title": row.title,
                    "body": row.body,
                    "format": row.format,
                    "cta": row.cta,
                    "is_ad": row.is_ad,
                    "views": row.views_count,
                    "er": row.er,
                    "reactions": json.loads(row.reactions) if row.reactions else {},
                    "channel_title": row.channel_title,
                    "channel_username": row.channel_username
                }
                posts.append(post_data)
            
            return posts
    
    async def get_trending_topics(self, category: str, days: int = 7) -> List[Dict]:
        """Получает трендовые темы за последние дни"""
        async with SessionLocal() as session:
            # Получаем посты за последние дни
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            posts_query = await session.execute("""
                SELECT p.topic, p.format, p.is_ad,
                       ps.views_count, ps.er, ps.reactions,
                       COUNT(*) OVER (PARTITION BY p.topic) as topic_count
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
                AND p.posted_at >= :start_date
                AND ps.er > 1.0
            """, {"category": f"%{category}%", "start_date": start_date})
            
            # Группируем по темам
            topics = {}
            for row in posts_query:
                topic = row.topic or "Общие"
                if topic not in topics:
                    topics[topic] = {
                        "topic": topic,
                        "posts_count": 0,
                        "total_views": 0,
                        "avg_er": 0,
                        "formats": {},
                        "ad_percentage": 0
                    }
                
                topics[topic]["posts_count"] += 1
                topics[topic]["total_views"] += row.views_count or 0
                topics[topic]["avg_er"] += row.er or 0
                
                # Считаем форматы
                format_type = row.format or "other"
                if format_type not in topics[topic]["formats"]:
                    topics[topic]["formats"][format_type] = 0
                topics[topic]["formats"][format_type] += 1
                
                # Считаем рекламные посты
                if row.is_ad:
                    topics[topic]["ad_percentage"] += 1
            
            # Вычисляем средние значения
            for topic_data in topics.values():
                if topic_data["posts_count"] > 0:
                    topic_data["avg_er"] /= topic_data["posts_count"]
                    topic_data["ad_percentage"] = (topic_data["ad_percentage"] / topic_data["posts_count"]) * 100
            
            # Сортируем по количеству постов и ER
            trending_topics = sorted(
                topics.values(),
                key=lambda x: (x["posts_count"], x["avg_er"]),
                reverse=True
            )
            
            return trending_topics[:10]
    
    async def get_trending_channels(self, category: str, days: int = 3) -> List[Dict]:
        """Получает трендовые каналы за последние дни"""
        async with SessionLocal() as session:
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            channels_query = await session.execute("""
                SELECT c.channel_id, c.title, c.username, c.description,
                       cs.subscribers_count, cs.engagement_rate,
                       COUNT(p.post_id) as posts_count,
                       AVG(ps.er) as avg_er,
                       SUM(ps.views_count) as total_views
                FROM channels c
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                LEFT JOIN posts p ON c.channel_id = p.channel_id
                LEFT JOIN posts_snapshot ps ON p.post_id = ps.post_id
                WHERE t.topic_name ILIKE :category
                AND p.posted_at >= :start_date
                GROUP BY c.channel_id, c.title, c.username, c.description,
                         cs.subscribers_count, cs.engagement_rate
                HAVING COUNT(p.post_id) > 0
                ORDER BY cs.engagement_rate DESC, total_views DESC
                LIMIT 10
            """, {"category": f"%{category}%", "start_date": start_date})
            
            channels = []
            for row in channels_query:
                channel_data = {
                    "channel_id": row.channel_id,
                    "title": row.title,
                    "username": row.username,
                    "description": row.description,
                    "subscribers": row.subscribers_count,
                    "engagement_rate": row.engagement_rate,
                    "posts_count": row.posts_count,
                    "avg_er": row.avg_er,
                    "total_views": row.total_views
                }
                channels.append(channel_data)
            
            return channels
    
    async def get_best_posting_times(self, category: str) -> Dict:
        """Анализирует лучшее время для публикаций"""
        async with SessionLocal() as session:
            # Получаем посты с данными о времени
            posts_query = await session.execute("""
                SELECT 
                    EXTRACT(HOUR FROM p.posted_at) as hour,
                    EXTRACT(DOW FROM p.posted_at) as day_of_week,
                    ps.er, ps.views_count
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
                AND ps.er > 0
                AND ps.views_count > 100
            """, {"category": f"%{category}%"})
            
            # Анализируем время
            hour_stats = {}
            day_stats = {}
            
            for row in posts_query:
                hour = int(row.hour)
                day = int(row.day_of_week)
                er = row.er or 0
                views = row.views_count or 0
                
                # Статистика по часам
                if hour not in hour_stats:
                    hour_stats[hour] = {"total_er": 0, "total_views": 0, "count": 0}
                hour_stats[hour]["total_er"] += er
                hour_stats[hour]["total_views"] += views
                hour_stats[hour]["count"] += 1
                
                # Статистика по дням
                if day not in day_stats:
                    day_stats[day] = {"total_er": 0, "total_views": 0, "count": 0}
                day_stats[day]["total_er"] += er
                day_stats[day]["total_views"] += views
                day_stats[day]["count"] += 1
            
            # Вычисляем средние значения
            for hour in hour_stats:
                if hour_stats[hour]["count"] > 0:
                    hour_stats[hour]["avg_er"] = hour_stats[hour]["total_er"] / hour_stats[hour]["count"]
                    hour_stats[hour]["avg_views"] = hour_stats[hour]["total_views"] / hour_stats[hour]["count"]
            
            for day in day_stats:
                if day_stats[day]["count"] > 0:
                    day_stats[day]["avg_er"] = day_stats[day]["total_er"] / day_stats[day]["count"]
                    day_stats[day]["avg_views"] = day_stats[day]["total_views"] / day_stats[day]["count"]
            
            # Находим лучшие часы и дни
            best_hours = sorted(hour_stats.items(), key=lambda x: x[1]["avg_er"], reverse=True)[:3]
            best_days = sorted(day_stats.items(), key=lambda x: x[1]["avg_er"], reverse=True)[:3]
            
            day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            
            return {
                "best_hours": [{"hour": hour, "avg_er": data["avg_er"], "avg_views": data["avg_views"]} 
                              for hour, data in best_hours],
                "best_days": [{"day": day_names[day], "avg_er": data["avg_er"], "avg_views": data["avg_views"]} 
                             for day, data in best_days]
            }
    
    async def analyze_content_trends(self, category: str) -> Dict:
        """Анализирует тренды контента"""
        async with SessionLocal() as session:
            # Получаем статистику по форматам
            formats_query = await session.execute("""
                SELECT p.format, COUNT(*) as count, AVG(ps.er) as avg_er
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
                AND p.format IS NOT NULL
                GROUP BY p.format
                ORDER BY count DESC
            """, {"category": f"%{category}%"})
            
            formats = []
            for row in formats_query:
                format_data = {
                    "format": row.format,
                    "count": row.count,
                    "avg_er": row.avg_er
                }
                formats.append(format_data)
            
            # Анализируем тренды CTA
            cta_query = await session.execute("""
                SELECT p.cta, COUNT(*) as count, AVG(ps.er) as avg_er
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
                AND p.cta IS NOT NULL
                GROUP BY p.cta
                ORDER BY count DESC
                LIMIT 10
            """, {"category": f"%{category}%"})
            
            cta_trends = []
            for row in cta_query:
                cta_data = {
                    "cta": row.cta,
                    "count": row.count,
                    "avg_er": row.avg_er
                }
                cta_trends.append(cta_data)
            
            return {
                "formats": formats,
                "cta_trends": cta_trends
            }
    
    async def get_falling_trends(self, category: str) -> List[Dict]:
        """Определяет падающие тренды"""
        async with SessionLocal() as session:
            # Сравниваем статистику за последние 7 и 30 дней
            week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            month_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
            
            # Статистика за неделю
            week_stats = await session.execute("""
                SELECT p.format, p.cta, COUNT(*) as count, AVG(ps.er) as avg_er
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
                AND p.posted_at >= :week_ago
                GROUP BY p.format, p.cta
            """, {"category": f"%{category}%", "week_ago": week_ago})
            
            # Статистика за месяц
            month_stats = await session.execute("""
                SELECT p.format, p.cta, COUNT(*) as count, AVG(ps.er) as avg_er
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                JOIN channels c ON p.channel_id = c.channel_id
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
                AND p.posted_at >= :month_ago
                GROUP BY p.format, p.cta
            """, {"category": f"%{category}%", "month_ago": month_ago})
            
            # Создаем словари для сравнения
            week_data = {}
            month_data = {}
            
            for row in week_stats:
                key = f"{row.format}_{row.cta}"
                week_data[key] = {"count": row.count, "avg_er": row.avg_er}
            
            for row in month_stats:
                key = f"{row.format}_{row.cta}"
                month_data[key] = {"count": row.count, "avg_er": row.avg_er}
            
            # Анализируем падение
            falling_trends = []
            for key in month_data:
                if key in week_data:
                    week_count = week_data[key]["count"]
                    month_count = month_data[key]["count"]
                    week_er = week_data[key]["avg_er"]
                    month_er = month_data[key]["avg_er"]
                    
                    # Если активность упала более чем на 50%
                    if week_count < month_count * 0.5 or week_er < month_er * 0.7:
                        format_type, cta = key.split("_", 1)
                        falling_trends.append({
                            "format": format_type,
                            "cta": cta,
                            "week_count": week_count,
                            "month_count": month_count,
                            "week_er": week_er,
                            "month_er": month_er,
                            "decline_percent": ((month_count - week_count) / month_count * 100) if month_count > 0 else 0
                        })
            
            return sorted(falling_trends, key=lambda x: x["decline_percent"], reverse=True)
    
    async def get_channel_analysis(self, channel_id: str) -> Dict:
        """Полный анализ канала"""
        async with SessionLocal() as session:
            # Основная статистика канала
            channel_query = await session.execute("""
                SELECT c.title, c.username, c.description,
                       cs.subscribers_count, cs.engagement_rate,
                       cs.avg_reactions, cs.avg_reposts,
                       COUNT(p.post_id) as total_posts
                FROM channels c
                LEFT JOIN channel_snapshots cs ON c.channel_id = cs.channel_id
                LEFT JOIN posts p ON c.channel_id = p.channel_id
                WHERE c.channel_id = :channel_id
                GROUP BY c.title, c.username, c.description,
                         cs.subscribers_count, cs.engagement_rate,
                         cs.avg_reactions, cs.avg_reposts
            """, {"channel_id": channel_id})
            
            channel_data = None
            for row in channel_query:
                channel_data = {
                    "title": row.title,
                    "username": row.username,
                    "description": row.description,
                    "subscribers": row.subscribers_count,
                    "engagement_rate": row.engagement_rate,
                    "avg_reactions": row.avg_reactions,
                    "avg_reposts": row.avg_reposts,
                    "total_posts": row.total_posts
                }
                break
            
            if not channel_data:
                return {}
            
            # Статистика по форматам
            formats_query = await session.execute("""
                SELECT p.format, COUNT(*) as count, AVG(ps.er) as avg_er
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                WHERE p.channel_id = :channel_id
                AND p.format IS NOT NULL
                GROUP BY p.format
                ORDER BY count DESC
            """, {"channel_id": channel_id})
            
            formats = []
            for row in formats_query:
                formats.append({
                    "format": row.format,
                    "count": row.count,
                    "avg_er": row.avg_er
                })
            
            # Лучшие посты
            top_posts_query = await session.execute("""
                SELECT p.title, p.body, p.format, p.cta,
                       ps.views_count, ps.er, ps.reactions
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                WHERE p.channel_id = :channel_id
                ORDER BY ps.er DESC, ps.views_count DESC
                LIMIT 5
            """, {"channel_id": channel_id})
            
            top_posts = []
            for row in top_posts_query:
                top_posts.append({
                    "title": row.title,
                    "body": row.body,
                    "format": row.format,
                    "cta": row.cta,
                    "views": row.views_count,
                    "er": row.er,
                    "reactions": json.loads(row.reactions) if row.reactions else {}
                })
            
            return {
                "channel": channel_data,
                "formats": formats,
                "top_posts": top_posts
            }
    
    async def get_audience_analysis(self, channel_id: str) -> Dict:
        """Анализ аудитории канала"""
        async with SessionLocal() as session:
            # Получаем снапшоты канала
            snapshots_query = await session.execute("""
                SELECT snapshot_date, subscribers_count, new_followers, lost_followers,
                       active_users_percent, silent_users_percent, engagement_rate
                FROM channel_snapshots
                WHERE channel_id = :channel_id
                ORDER BY snapshot_date DESC
                LIMIT 30
            """, {"channel_id": channel_id})
            
            snapshots = []
            for row in snapshots_query:
                snapshots.append({
                    "date": row.snapshot_date.isoformat(),
                    "subscribers": row.subscribers_count,
                    "new_followers": row.new_followers,
                    "lost_followers": row.lost_followers,
                    "active_users_percent": row.active_users_percent,
                    "silent_users_percent": row.silent_users_percent,
                    "engagement_rate": row.engagement_rate
                })
            
            if not snapshots:
                return {}
            
            # Анализируем тренды
            latest = snapshots[0]
            oldest = snapshots[-1] if len(snapshots) > 1 else latest
            
            growth_rate = 0
            if oldest["subscribers"] and oldest["subscribers"] > 0:
                growth_rate = ((latest["subscribers"] - oldest["subscribers"]) / oldest["subscribers"]) * 100
            
            return {
                "current_subscribers": latest["subscribers"],
                "growth_rate": growth_rate,
                "active_users_percent": latest["active_users_percent"],
                "silent_users_percent": latest["silent_users_percent"],
                "engagement_rate": latest["engagement_rate"],
                "snapshots": snapshots
            }
    
    async def get_successful_creatives_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        """Получает успешные рекламные креативы по категории"""
        async with SessionLocal() as session:
            # Получаем каналы по категории
            channels_query = await session.execute("""
                SELECT c.channel_id, c.title, c.username
                FROM channels c
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
            """, {"category": f"%{category}%"})
            
            channel_ids = [row.channel_id for row in channels_query]
            
            if not channel_ids:
                return []
            
            # Получаем рекламные креативы с высоким ER
            creatives_query = await session.execute("""
                SELECT cr.creative_id, cr.ad_title, cr.ad_text, cr.cta, cr.ad_topic,
                       cr.channel_topic, cr.tags, cr.created_at
                FROM creatives cr
                JOIN channels c ON cr.channel_id = c.channel_id
                WHERE cr.channel_id = ANY(:channel_ids)
                ORDER BY cr.created_at DESC
                LIMIT :limit
            """, {"channel_ids": channel_ids, "limit": limit})
            
            creatives = []
            for row in creatives_query:
                creative_data = {
                    "creative_id": row.creative_id,
                    "ad_title": row.ad_title,
                    "ad_text": row.ad_text,
                    "cta": row.cta,
                    "ad_topic": row.ad_topic,
                    "channel_topic": row.channel_topic,
                    "tags": row.tags,
                    "created_at": row.created_at
                }
                creatives.append(creative_data)
            
            return creatives
    
    async def get_engagement_analysis(self, category: str) -> Dict:
        """Получает анализ вовлеченности по категории"""
        async with SessionLocal() as session:
            # Получаем каналы по категории
            channels_query = await session.execute("""
                SELECT c.channel_id, c.title, c.username
                FROM channels c
                JOIN channel_topic ct ON c.channel_id = ct.channel_id
                JOIN topics t ON ct.topic_id = t.topic_id
                WHERE t.topic_name ILIKE :category
            """, {"category": f"%{category}%"})
            
            channel_ids = [row.channel_id for row in channels_query]
            
            if not channel_ids:
                return {
                    "avg_er": 0,
                    "best_formats": [],
                    "engagement_trends": [],
                    "recommendations": []
                }
            
            # Получаем статистику вовлеченности
            engagement_query = await session.execute("""
                SELECT 
                    AVG(ps.er) as avg_er,
                    p.format,
                    COUNT(*) as posts_count,
                    AVG(ps.views_count) as avg_views
                FROM posts p
                JOIN posts_snapshot ps ON p.post_id = ps.post_id
                WHERE p.channel_id = ANY(:channel_ids)
                AND ps.er > 0
                GROUP BY p.format
                ORDER BY avg_er DESC
                LIMIT 5
            """, {"channel_ids": channel_ids})
            
            formats = []
            total_er = 0
            total_posts = 0
            
            for row in engagement_query:
                if row.format:
                    formats.append({
                        "format": row.format,
                        "avg_er": float(row.avg_er or 0),
                        "posts_count": row.posts_count,
                        "avg_views": float(row.avg_views or 0)
                    })
                    total_er += float(row.avg_er or 0) * row.posts_count
                    total_posts += row.posts_count
            
            avg_er = total_er / total_posts if total_posts > 0 else 0
            best_formats = [f["format"] for f in formats[:3]]
            
            return {
                "avg_er": avg_er,
                "best_formats": best_formats,
                "format_analysis": formats,
                "total_posts": total_posts
            }

# Глобальный экземпляр анализатора данных
data_analyzer = DataAnalyzer() 