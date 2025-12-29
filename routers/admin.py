from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List

from database import get_db
from schemas import SystemStats, AdminUserCreate, User as UserSchema
from utils.auth import get_system_admin
from models import User, Family, FamilyMember, AccountRecord

router = APIRouter()

@router.get("/system-stats", response_model=SystemStats)
async def get_system_statistics(
    current_user: User = Depends(get_system_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取系统统计数据"""
    print(f"DEBUG: /system-stats 被调用")
    """获取系统统计数据"""
    
    # 统计总用户数
    user_count_stmt = select(func.count(User.id))
    user_result = await db.execute(user_count_stmt)
    total_users = user_result.scalar() or 0
    
    # 统计总家庭数
    family_count_stmt = select(func.count(Family.id))
    family_result = await db.execute(family_count_stmt)
    total_families = family_result.scalar() or 0
    
    # 统计总记录数
    record_count_stmt = select(func.count(AccountRecord.id))
    record_result = await db.execute(record_count_stmt)
    total_records = record_result.scalar() or 0
    
    # 统计总金额
    amount_stmt = select(func.sum(AccountRecord.amount))
    amount_result = await db.execute(amount_stmt)
    total_amount = amount_result.scalar() or 0
    
    return SystemStats(
        total_users=total_users,
        total_families=total_families,
        total_records=total_records,
        total_amount=float(total_amount)
    )

@router.get("/family-admins", response_model=List[UserSchema])
async def get_family_admins(
    current_user: User = Depends(get_system_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭管理员列表"""
    stmt = select(User).where(User.role == "family_admin")
    result = await db.execute(stmt)
    admins = result.scalars().all()
    
    return list(admins)

@router.post("/add-admin", response_model=UserSchema)
async def add_family_admin(
    admin_data: AdminUserCreate,
    current_user: User = Depends(get_system_admin),
    db: AsyncSession = Depends(get_db)
):
    """添加家庭管理员"""
    from utils.auth import get_password_hash
    
    # 检查手机号是否已存在
    existing_stmt = select(User).where(User.phone == admin_data.phone)
    existing_result = await db.execute(existing_stmt)
    existing_user = existing_result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="手机号已存在"
        )
    
    # 创建管理员用户
    new_admin = User(
        phone=admin_data.phone,
        name=admin_data.name,
        hashed_password=get_password_hash(admin_data.password),
        role=admin_data.role,
        is_active=True
    )
    
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    
    return new_admin

@router.delete("/remove-admin/{admin_id}")
async def remove_family_admin(
    admin_id: int,
    current_user: User = Depends(get_system_admin),
    db: AsyncSession = Depends(get_db)
):
    """移除家庭管理员"""
    stmt = select(User).where(User.id == admin_id)
    result = await db.execute(stmt)
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(
            status_code=404,
            detail="管理员不存在"
        )
    
    if admin.role != "family_admin":
        raise HTTPException(
            status_code=400,
            detail="该用户不是家庭管理员"
        )
    
    # 先删除相关的账本记录
    record_stmt = select(AccountRecord).where(AccountRecord.user_id == admin_id)
    record_result = await db.execute(record_stmt)
    records = record_result.scalars().all()
    
    for record in records:
        await db.delete(record)
    
    # 删除相关的家庭成员关系
    member_stmt = select(FamilyMember).where(FamilyMember.user_id == admin_id)
    member_result = await db.execute(member_stmt)
    members = member_result.scalars().all()
    
    for member in members:
        await db.delete(member)
    
    # 删除用户
    await db.delete(admin)
    await db.commit()
    
    return {"success": True, "message": "家庭管理员移除成功"}

@router.get("/all-families")
async def get_all_families(
    current_user: User = Depends(get_system_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取所有家庭列表"""
    family_stmt = select(Family)
    family_result = await db.execute(family_stmt)
    families = family_result.scalars().all()
    
    families_data = []
    for family in families:
        # 获取家庭成员数量
        member_count_stmt = select(func.count(FamilyMember.id)).where(
            and_(
                FamilyMember.family_id == family.id,
                FamilyMember.is_active == True
            )
        )
        member_result = await db.execute(member_count_stmt)
        member_count = member_result.scalar() or 0
        
        # 获取家庭总金额
        amount_stmt = select(func.sum(AccountRecord.amount)).where(
            AccountRecord.family_id == family.id
        )
        amount_result = await db.execute(amount_stmt)
        total_amount = amount_result.scalar() or 0
        
        # 获取创建者姓名
        creator_stmt = select(User.name).where(User.id == family.created_by)
        creator_result = await db.execute(creator_stmt)
        admin_name = creator_result.scalar_one_or_none() or "未知"
        
        families_data.append({
            "id": family.id,
            "name": family.name,
            "admin_name": admin_name,
            "member_count": member_count,
            "total_amount": float(total_amount),
            "is_active": family.is_active,
            "created_at": family.created_at
        })
    
    return {"success": True, "data": families_data}

@router.post("/reset-user-password")
async def reset_user_password(
    phone: str,
    current_user: User = Depends(get_system_admin),
    db: AsyncSession = Depends(get_db)
):
    """重置用户密码"""
    from utils.auth import get_password_hash
    
    stmt = select(User).where(User.phone == phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    # 重置密码为默认密码
    user.hashed_password = get_password_hash("123456")
    await db.commit()
    
    return {"success": True, "message": "密码重置成功，新密码为 123456"}

@router.get("/export-data")
async def export_system_data(
    current_user: User = Depends(get_system_admin),
    db: AsyncSession = Depends(get_db)
):
    """导出系统数据"""
    # 这里可以实现数据导出功能
    # 导出用户、家庭、记录等数据为CSV或Excel格式
    
    return {
        "success": True,
        "message": "数据导出功能待实现",
        "data": {
            "export_url": "/api/admin/download/export.zip"
        }
    }