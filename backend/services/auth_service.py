from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os

# 🔐 Secret key (use ENV in production)
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 🔒 Hash password
def hash_password(password: str):
    return pwd_context.hash(password)


# 🔍 Verify password
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


# 🎫 Create JWT token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# 🔓 Decode token (SAFE)
def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise Exception("Invalid token")