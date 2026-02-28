import os
import passlib
import bcrypt

print("passlib:", passlib.__version__)
print("bcrypt:", bcrypt.__version__)

from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

print("verifying...")
plain = "Jexi@2024"
hashed = "$2b$12$KqOyA/eE3EBfjUDKyVZWge5tKD5T89g3/.gsmP0B6JJ5xA0AT8pAK"
res = pwd_context.verify(plain, hashed)
print("Res:", res)
