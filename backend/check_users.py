from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load env from the same directory or adjust path
load_dotenv(dotenv_path="e:/jarvis/jexi/backend/.env")

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

from models.user import User

users = db.query(User).all()
print(f"Total users: {len(users)}")
for u in users:
    print(f"ID: {u.id}, Username: {u.username}, Admin: {u.is_admin}")

db.close()
