import os
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

h = "$2b$12$KqOyA/eE3EBfjUDKyVZWge5tKD5T89g3/.gsmP0B6JJ5xA0AT8pAK"
try:
    print(pwd_context.verify("Jexi@2024", h))
except Exception as e:
    print("Error:", repr(e))
