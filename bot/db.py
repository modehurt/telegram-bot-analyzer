import os
import enum
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Text, ForeignKey, Boolean, Enum, Float

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://tguser:tgpass@localhost:5432/tgstat")
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# --- Старые модели для обратной совместимости ---
class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(BigInteger, unique=True, index=True)
    title = Column(String)
    category = Column(String)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.group_id"))
    user_id = Column(BigInteger)
    text = Column(Text)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    group = relationship("Group", backref="messages")

# --- Новые модели по ТЗ ---
class AccountStatus(enum.Enum):
    Active = "Active"
    Banned = "Banned"
    Error = "Error"

class Account(Base):
    __tablename__ = "accounts"
    account_id = Column(String, primary_key=True)  # uuid
    phone_number = Column(String, nullable=False)
    session_file_path = Column(String, nullable=False)
    status = Column(Enum(AccountStatus), nullable=False)
    is_logged_in = Column(Boolean, default=False)
    total_channels = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Channel(Base):
    __tablename__ = "channels"
    channel_id = Column(String, primary_key=True)  # uuid
    username = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_bot_admin = Column(Boolean, default=False)

class ChannelSnapshot(Base):
    __tablename__ = "channel_snapshots"
    channel_snapshot_id = Column(String, primary_key=True)  # uuid
    channel_id = Column(String, ForeignKey("channels.channel_id"))
    snapshot_date = Column(DateTime, nullable=False)
    subscribers_count = Column(Integer)
    reach_rate = Column(Float)
    avg_reactions = Column(Float)
    avg_reposts = Column(Float)
    avg_post_comments = Column(Float)
    new_followers = Column(Integer)
    lost_followers = Column(Integer)
    silent_users_percent = Column(Float)
    active_users_percent = Column(Float)
    posts_count = Column(Integer)
    total_views = Column(Integer)
    engagement_rate = Column(Float)
    source_info = Column(Text)
    notification_percent = Column(Float)
    avg_positive_reactions = Column(Float)
    avg_negative_reactions = Column(Float)

class Topic(Base):
    __tablename__ = "topics"
    topic_id = Column(String, primary_key=True)  # uuid
    topic_name = Column(String, nullable=False)

class ChannelTopic(Base):
    __tablename__ = "channel_topic"
    id = Column(String, primary_key=True)  # uuid
    channel_id = Column(String, ForeignKey("channels.channel_id"))
    topic_id = Column(String, ForeignKey("topics.topic_id"))

class AccountChannel(Base):
    __tablename__ = "account_channels"
    id = Column(String, primary_key=True)  # uuid
    account_id = Column(String, ForeignKey("accounts.account_id"))
    channel_id = Column(String, ForeignKey("channels.channel_id"))
    subscribed_at = Column(DateTime)

class Post(Base):
    __tablename__ = "posts"
    post_id = Column(String, primary_key=True)  # uuid
    channel_id = Column(String, ForeignKey("channels.channel_id"))
    posted_at = Column(DateTime, nullable=False)  # <-- было datetime, стало posted_at
    title = Column(String)
    body = Column(Text)
    is_ad = Column(Boolean, default=False)
    media_type = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    has_poll = Column(Boolean, default=False)
    format = Column(String)
    cta = Column(String)
    topic = Column(String)
    tags = Column(Text)

class PostSnapshot(Base):
    __tablename__ = "posts_snapshot"
    id = Column(String, primary_key=True)  # uuid
    post_id = Column(String, ForeignKey("posts.post_id"))
    views_count = Column(Integer)
    views_info = Column(Text)
    reactions = Column(Text)
    comments = Column(Integer)
    forwards = Column(Integer)
    forwards_private = Column(Integer)
    er = Column(Float)
    snapshot_date = Column(DateTime)
    is_final = Column(Boolean, default=False)

class PostTopic(Base):
    __tablename__ = "post_topic"
    id = Column(String, primary_key=True)  # uuid
    channel_id = Column(String, ForeignKey("channels.channel_id"))
    topic_id = Column(String, ForeignKey("topics.topic_id"))

class Creative(Base):
    __tablename__ = "creatives"
    creative_id = Column(String, primary_key=True)  # uuid
    ad_topic = Column(String)
    channel_topic = Column(String)
    tags = Column(Text)
    ad_title = Column(String)
    ad_text = Column(Text)
    link = Column(String)
    cta = Column(String)
    media_id = Column(String, ForeignKey("media.media_id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Media(Base):
    __tablename__ = "media"
    media_id = Column(String, primary_key=True)  # uuid
    post_id = Column(String, ForeignKey("posts.post_id"))
    media_type = Column(String)
    file_id = Column(String)
    external_url = Column(String)
    thumb_url = Column(String)
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)  # uuid
    telegram_id = Column(BigInteger, nullable=False)
    username = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Subscription(Base):
    __tablename__ = "subscriptions"
    subscription_id = Column(String, primary_key=True)  # uuid
    user_id = Column(String, ForeignKey("users.user_id"))
    plan_name = Column(String)
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    status = Column(String)

class SearchLog(Base):
    __tablename__ = "search_logs"
    log_id = Column(String, primary_key=True)  # uuid
    user_id = Column(String, ForeignKey("users.user_id"))
    query = Column(Text)
    filters = Column(Text)
    type = Column(String)
    data = Column(Text)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 