# Import all models so they register with SQLAlchemy Base.metadata
# This ensures Base.metadata.create_all() creates all tables

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

__all__ = [
    "User",
    "Task",
    "Goal",
    "Habit",
    "HabitLog",
    "JournalEntry",
    "Transaction",
    "Budget",
    "HealthLog",
    "Project",
    "DevSession",
    "Snippet",
    "LearningCourse",
    "LearningNote",
    "MemoryFact",
    "Conversation",
    "Notification",
    "DSAProblem",
    "DailyScore",
    "APIUsage",
    "SharedKey",
    "Friendship",
    "ChatMessage",
]
