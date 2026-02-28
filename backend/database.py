import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL
import logging

# Set up logging for Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Only use connect_args if we are using SQLite
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
else:
    # Production settings for PostgreSQL
    engine_args.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    })

try:
    engine = create_engine(
        DATABASE_URL,
        **engine_args,
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Failed to create engine: {e}")
    raise e

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create the data/ directory if it doesn't exist, then create all tables."""
    if DATABASE_URL.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)

    # Import all models so they register with Base.metadata
    from models.user import User
    from models.task import Task
    from models.goal import Goal
    from models.habit import Habit
    from models.habit_log import HabitLog
    from models.journal import JournalEntry
    from models.transaction import Transaction
    from models.budget import Budget
    from models.health_log import HealthLog
    from models.project import Project
    from models.dev_session import DevSession
    from models.snippet import Snippet
    from models.learning_course import LearningCourse
    from models.learning_note import LearningNote
    from models.memory_fact import MemoryFact
    from models.conversation import Conversation
    from models.notification import Notification
    from models.dsa_problem import DSAProblem
    from models.daily_score import DailyScore
    from models.api_usage import APIUsage
    from models.shared_key import SharedKey
    from models.friendship import Friendship
    from models.chat_message import ChatMessage
    from models.book import Book

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        # In Vercel, this might fail if the DB user doesn't have CREATE privileges
        # but we should still catch it to avoid a crash.
