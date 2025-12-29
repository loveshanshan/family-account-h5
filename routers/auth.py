from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from database import get_db
from schemas import UserLogin, Token, PasswordChange, PasswordReset, UserCreate
from utils.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user,
    get_password_hash,
    verify_password
)
from models import User
from config import config

router = APIRouter()

@router.post("/register")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    from sqlalchemy import select
    from models import UserRole
    
    # 检查手机号是否已存在
    stmt = select(User).where(User.phone == user_data.phone)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号已存在"
        )
    
    # 创建新用户
    new_user = User(
        phone=user_data.phone,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        role=UserRole.FAMILY_MEMBER,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return {
        "success": True,
        "message": "注册成功",
        "user": {
            "id": new_user.id,
            "phone": new_user.phone,
            "name": new_user.name,
            "role": new_user.role,
            "is_active": new_user.is_active
        }
    }

@router.post("/login", response_model=Token)
async def login(
    form_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    user = await authenticate_user(db, form_data.phone, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用"
        )
    
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"success": True, "message": "密码修改成功"}

@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """重置密码（系统管理员功能）"""
    from sqlalchemy import select
    
    stmt = select(User).where(User.phone == reset_data.phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user.hashed_password = get_password_hash("123456")  # 重置为默认密码
    await db.commit()
    
    return {"success": True, "message": "密码重置成功，新密码为 123456"}

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return {
        "success": True,
        "data": current_user
    }