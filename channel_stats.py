import json
import os
from pyrogram import Client
from tqdm import tqdm

# Вставь свои значения ниже
api_id = 26333656  # твой API ID
api_hash = "2c550faf732f3920b062006d9b7dfd55"  # твой API HASH

# Имя сессии (файл user_session.session появится в папке после первого запуска)
app = Client("user_session", api_id=api_id, api_hash=api_hash)

channel_username = input("Введи username канала (без @): ")
limit_input = input("Сколько сообщений парсить? (Enter — все): ").strip()
limit = int(limit_input) if limit_input else None

# Создаём папку для изображений, если её нет
os.makedirs("images", exist_ok=True)

all_posts = []
print("Парсинг всех постов... Это может занять время!")

with app:
    # Получаем количество сообщений для прогресс-бара
    total_msgs = app.get_chat(channel_username).messages_count if not limit else limit
    messages = app.get_chat_history(channel_username, limit=limit) if limit else app.get_chat_history(channel_username)
    for message in tqdm(messages, total=total_msgs, desc="Посты обработано"):
        text = message.text or message.caption or "[без текста]"
        # Сбор реакций
        reactions = {}
        if message.reactions:
            for reaction in message.reactions.reactions:
                reactions[reaction.emoji] = reaction.count
        # Сбор темы (topic)
        topic_id = getattr(message, 'topic_id', None)
        topic_name = getattr(message, 'topic_name', None)
        # Ссылка на изображение (если есть)
        image_url = None
        if message.photo:
            try:
                image_url = app.download_media(message, file_name=f"images/{channel_username}_{message.id}.jpg")
            except Exception as e:
                print(f"Ошибка при скачивании изображения для поста {message.id}: {e}")
                image_url = None
        all_posts.append({
            "id": message.id,
            "views": message.views,
            "text": text,
            "reactions": reactions,
            "topic_id": topic_id,
            "topic_name": topic_name,
            "image_path": image_url
        })

print(f"Всего постов собрано: {len(all_posts)}")

# Сохраняем в файл
with open(f"{channel_username}_posts.json", "w", encoding="utf-8") as f:
    json.dump(all_posts, f, ensure_ascii=False, indent=2)
print(f"Данные сохранены в {channel_username}_posts.json")

# --- Интерактивная статистика ---
while True:
    print("\nЧто вывести?\n1. Топ-10 по просмотрам\n2. Топ-10 по реакциям\n3. Статистика по темам\n4. Выйти")
    choice = input("Выбери (1/2/3/4): ").strip()
    if choice == "1":
        top = sorted([p for p in all_posts if p["views"]], key=lambda x: x["views"], reverse=True)[:10]
        for post in top:
            print(f"ID: {post['id']}, Views: {post['views']}, Text: {post['text'][:50]}")
            if post["reactions"]:
                reactions_str = ", ".join(f"{emoji} {count}" for emoji, count in post["reactions"].items())
                print(f"Реакции: {reactions_str}")
            else:
                print("Реакции: нет")
            if post["image_path"]:
                print(f"Изображение: {post['image_path']}")
    elif choice == "2":
        reaction_stats = {}
        for post in all_posts:
            for emoji, count in post["reactions"].items():
                reaction_stats[emoji] = reaction_stats.get(emoji, 0) + count
        if reaction_stats:
            for emoji, count in sorted(reaction_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"{emoji}: {count}")
        else:
            print("Нет реакций в постах.")
    elif choice == "3":
        topics = {}
        for post in all_posts:
            topic = post["topic_name"] or str(post["topic_id"]) or "Без темы"
            topics.setdefault(topic, []).append(post)
        for topic, posts in topics.items():
            print(f"\nТема: {topic} — {len(posts)} постов")
            total_views = sum(p["views"] or 0 for p in posts)
            print(f"  Всего просмотров: {total_views}")
    elif choice == "4":
        break
    else:
        print("Некорректный выбор. Попробуй снова.") 