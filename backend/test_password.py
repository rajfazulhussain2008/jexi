from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from auth import verify_password
from models.user import User

# Load env
load_dotenv(dotenv_path="e:/jarvis/jexi/backend/.env")

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

user = db.query(User).filter(User.username == "rajfazulhussain2008").first()
if user:
    print(f"User: {user.username}")
    password_to_check = "password123"
    is_correct = verify_password(password_to_check, user.hashed_password)
    print(f"Verify 'password123': {is_correct}")
else:
    print("User 'rajfazulhussain2008' not found.")

db.close()
