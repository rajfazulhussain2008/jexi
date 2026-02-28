"""
notification_service.py — Global System Alarms
Parses database schedules silently and generates persistent notifications for UI
consumption across reminders, streaks, bounds, and thresholds.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session
from models.notification import Notification

from services.task_service import TaskService


class NotificationService:
    @staticmethod
    def get_all(db: Session, user_id: int, unread_only: bool = False) -> list:
        try:
            query = db.query(Notification).filter_by(user_id=user_id)
            if unread_only:
                query = query.filter_by(is_read=False)
            return query.order_by(Notification.created_at.desc()).all()
        except:
            return []

    @staticmethod
    def mark_read(db: Session, user_id: int, notification_id: int):
        try:
            n = db.query(Notification).filter_by(id=notification_id, user_id=user_id).first()
            if n:
                n.is_read = True
                db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def generate(db: Session, user_id: int) -> list:
        """Periodic background chron logic (simulated) creating missing alerts."""
        try:
            new_notifications = []
            
            # Example 1: Overdue Tasks
            overdue = TaskService.get_overdue(db, user_id)
            for t in overdue:
                # Basic deduping logic so we don't spam the exact same notification over and over
                existing = db.query(Notification).filter_by(user_id=user_id, type="reminder", reference_id=t.id, reference_type="task").first()
                if not existing:
                    n = Notification(
                        user_id=user_id, type="reminder",
                        title=f"Task Overdue: {t.title}",
                        message="Please complete or reschedule.",
                        reference_type="task", reference_id=t.id
                    )
                    db.add(n)
                    new_notifications.append(n)
            
            # Example 2: Other thresholds (Habits breaking streaks, Budget > 80% usage, etc.)
            # ...
            
            db.commit()
            return new_notifications
        except Exception:
            db.rollback()
            return []
