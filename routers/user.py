from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from database import get_db
from schemas import User as UserSchema, UserUpdate
from utils.auth import get_current_active_user
from models import User

router = APIRouter()

@router.get("/profile", response_model=UserSchema)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """获取用户资料"""
    return current_user

@router.put("/profile", response_model=UserSchema)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户资料"""
    # 检查手机号是否已被其他用户使用
    if user_update.phone and user_update.phone != current_user.phone:
        stmt = select(User).where(User.phone == user_update.phone)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="手机号已被使用"
            )
    
    # 更新用户信息
    if user_update.name:
        current_user.name = user_update.name
    if user_update.phone:
        current_user.phone = user_update.phone
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

@router.get("/by-phone/{phone}")
async def get_user_by_phone(
    phone: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """通过手机号查找用户"""
    stmt = select(User).where(User.phone == phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.name,
        "role": user.role,
        "is_active": user.is_active
    }

@router.get("/family-members")
async def get_family_members(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭成员列表"""
    from sqlalchemy.orm import selectinload
    from models import Family, FamilyMember
    
    # 查找用户所在的家庭
    stmt = select(FamilyMember).where(
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).options(selectinload(FamilyMember.family))
    result = await db.execute(stmt)
    memberships = result.scalars().all()
    
    members = []
    for membership in memberships:
        family = membership.family
        # 获取该家庭的所有成员
        member_stmt = select(FamilyMember).where(
            FamilyMember.family_id == family.id,
            FamilyMember.is_active == True
        ).options(selectinload(FamilyMember.user))
        member_result = await db.execute(member_stmt)
        family_members = member_result.scalars().all()
        
        for member in family_members:
            members.append({
                "id": member.id,
                "family_id": family.id,
                "family_name": family.name,
                "user_id": member.user.id,
                "user_name": member.user.name,
                "user_phone": member.user.phone,
                "role": member.role,
                "joined_at": member.joined_at,
                "is_active": member.is_active
            })
    
    return {
        "success": True,
        "data": members
    }