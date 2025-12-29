from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import config
from database import get_db
from models import User

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT认证
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 确保用户ID是字符串类型
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    print(f"DEBUG: Received Authorization header: {credentials.credentials[:20]}...")
    
    try:
        payload = jwt.decode(credentials.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            print("DEBUG: No 'sub' in JWT payload")
            raise credentials_exception
        # 转换为整数
        user_id = int(user_id_str)
        print(f"DEBUG: JWT decoded successfully, user_id: {user_id}")
    except (JWTError, ValueError) as e:
        print(f"DEBUG: JWT decode error: {e}")
        raise credentials_exception
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        print(f"DEBUG: User not found with id: {user_id}")
        raise credentials_exception
    
    if not user.is_active:
        print(f"DEBUG: User {user.phone} is not active")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    print(f"DEBUG: User authenticated: {user.phone}, role: {user.role}")
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取管理员用户"""
    if current_user.role not in ["system_admin", "family_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_system_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取系统管理员"""
    print(f"DEBUG: get_system_admin called with user: {current_user.phone}, role: {current_user.role}")
    if current_user.role != "system_admin":
        print(f"DEBUG: User role {current_user.role} is not system_admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System admin access required"
        )
    print(f"DEBUG: System admin access granted for {current_user.phone}")
    return current_user

async def authenticate_user(db: AsyncSession, phone: str, password: str) -> Optional[User]:
    """验证用户"""
    stmt = select(User).where(User.phone == phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    
    return user