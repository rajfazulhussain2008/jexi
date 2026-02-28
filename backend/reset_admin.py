from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load env
load_dotenv(dotenv_path="e:/jarvis/jexi/backend/.env")

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

from models.user import User
from auth import hash_password

# Find 'raj' and update to 'rajfazulhussain2008' with a new password
user = db.query(User).filter(User.username == "raj").first()
if user:
    user.username = "rajfazulhussain2008"
    user.hashed_password = hash_password("password123")
    db.commit()
    print(f"Updated user ID {user.id} to username 'rajfazulhussain2008' with password 'password123'")
else:
    # Maybe it's already updated or doesn't exist?
    user = db.query(User).filter(User.username == "rajfazulhussain2008").first()
    if user:
        user.hashed_password = hash_password("password123")
        db.commit()
        print(f"Updated password for 'rajfazulhussain2008' to 'password123'")
    else:
        print("User 'raj' or 'rajfazulhussain2008' not found.")

db.close()
