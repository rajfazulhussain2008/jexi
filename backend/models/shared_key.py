from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from database import Base


class SharedKey(Base):
    """
    SharedKey stores API keys provided by friends inside the web app.
    Keys are stored as encrypted blobs.
    """
    __tablename__ = "shared_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)  # groq, gemini, openrouter, etc.
    encrypted_key = Column(Text, nullable=False)
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Optional linking
    is_active = Column(Boolean, default=True)
    is_exhausted = Column(Boolean, default=False)
    last_used = Column(DateTime, nullable=True)
    exhausted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        return f"{self.provider}_shared_{self.id}"
