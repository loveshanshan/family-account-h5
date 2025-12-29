from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from schemas import AccountRecordCreate, AccountRecordUpdate, AccountRecordWithUser
from utils.auth import get_current_active_user
from models import AccountRecord, Family, FamilyMember, User, UserRole

router = APIRouter()

async def get_user_family_id(current_user: User, db: AsyncSession) -> Optional[int]:
    """获取用户所在的家庭ID"""
    stmt = select(FamilyMember.family_id).where(
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    )
    result = await db.execute(stmt)
    family_id = result.scalar_one_or_none()
    return family_id

@router.post("/", response_model=AccountRecordWithUser)
async def create_record(
    record: AccountRecordCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """创建记账记录"""
    # 验证用户是否为该家庭成员
    user_family_id = await get_user_family_id(current_user, db)
    if user_family_id != record.family_id:
        raise HTTPException(
            status_code=403,
            detail="您不是该家庭的成员"
        )
    
    # 创建记录
    db_record = AccountRecord(
        family_id=record.family_id,
        user_id=current_user.id,
        type=record.type,
        category=record.category,
        amount=record.amount,
        note=record.note,
        date=record.date or datetime.utcnow()
    )
    
    db.add(db_record)
    await db.commit()
    await db.refresh(db_record)
    
    # 关联用户信息
    db_record.user_name = current_user.name
    
    # 返回格式化的数据，确保type字段为小写
    result = {
        "id": db_record.id,
        "family_id": db_record.family_id,
        "user_id": db_record.user_id,
        "user_name": current_user.name,
        "type": db_record.type.value if hasattr(db_record.type, 'value') else str(db_record.type).lower(),
        "category": db_record.category,
        "amount": db_record.amount,
        "note": db_record.note,
        "date": db_record.date,
        "created_at": db_record.created_at
    }
    return result

@router.get("/", response_model=List[AccountRecordWithUser])
async def get_records(
    family_id: Optional[int] = None,
    record_type: Optional[str] = None,
    category: Optional[List[str]] = Query(None),  # 支持多值查询
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取记账记录列表"""
    # 确定查询的家庭ID
    if family_id is None:
        family_id = await get_user_family_id(current_user, db)
    
    if family_id is None:
        raise HTTPException(
            status_code=400,
            detail="请指定家庭ID"
        )
    
    # 验证用户权限
    user_family_id = await get_user_family_id(current_user, db)
    if user_family_id != family_id and current_user.role not in ["system_admin", "family_admin"]:
        raise HTTPException(
            status_code=403,
            detail="您没有权限查看该家庭的记录"
        )
    
    # 构建查询条件
    conditions = [AccountRecord.family_id == family_id]
    
    if record_type:
        conditions.append(AccountRecord.type == record_type)
    if category:
        # 支持多个分类查询
        if isinstance(category, list):
            if category:  # 如果列表不为空
                conditions.append(AccountRecord.category.in_(category))
        else:  # 兼容单个分类的模糊查询
            conditions.append(AccountRecord.category.like(f"%{category}%"))
    if start_date:
        conditions.append(AccountRecord.date >= start_date)
    if end_date:
        conditions.append(AccountRecord.date <= end_date)
    
    # 查询记录
    stmt = select(AccountRecord).where(and_(*conditions))
    stmt = stmt.order_by(AccountRecord.date.desc())
    stmt = stmt.offset((page - 1) * size).limit(size)
    
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    # 添加用户名信息
    records_with_user = []
    for record in records:
        user_stmt = select(User.name).where(User.id == record.user_id)
        user_result = await db.execute(user_stmt)
        user_name = user_result.scalar_one_or_none() or "未知用户"
        
        record_dict = {
            "id": record.id,
            "family_id": record.family_id,
            "user_id": record.user_id,
            "user_name": user_name,
            "type": record.type.value if hasattr(record.type, 'value') else str(record.type).lower(),
            "category": record.category,
            "amount": record.amount,
            "note": record.note,
            "date": record.date,
            "created_at": record.created_at
        }
        records_with_user.append(record_dict)
    
    return records_with_user

@router.get("/{record_id}", response_model=AccountRecordWithUser)
async def get_record(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单条记账记录"""
    stmt = select(AccountRecord).where(AccountRecord.id == record_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail="记录不存在"
        )
    
    # 验证权限
    user_family_id = await get_user_family_id(current_user, db)
    if record.family_id != user_family_id and current_user.role not in ["system_admin", "family_admin"]:
        raise HTTPException(
            status_code=403,
            detail="您没有权限查看该记录"
        )
    
    # 获取用户名
    user_stmt = select(User.name).where(User.id == record.user_id)
    user_result = await db.execute(user_stmt)
    user_name = user_result.scalar_one_or_none() or "未知用户"
    
    # 返回格式化的数据，确保type字段为小写
    result = {
        "id": record.id,
        "family_id": record.family_id,
        "user_id": record.user_id,
        "user_name": user_name,
        "type": record.type.value if hasattr(record.type, 'value') else str(record.type).lower(),
        "category": record.category,
        "amount": record.amount,
        "note": record.note,
        "date": record.date,
        "created_at": record.created_at
    }
    return result

@router.put("/{record_id}")
async def update_record(
    record_id: int,
    record_update: AccountRecordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """更新记账记录"""
    stmt = select(AccountRecord).where(AccountRecord.id == record_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail="记录不存在"
        )
    
    # 验证权限（只有记录创建者、家庭管理员、系统管理员可以修改）
    user_family_id = await get_user_family_id(current_user, db)
    can_edit = (
        record.user_id == current_user.id or
        current_user.role in ["system_admin", "family_admin"]
    )
    
    if record.family_id != user_family_id and current_user.role not in ["system_admin", "family_admin"]:
        can_edit = False
    
    if not can_edit:
        raise HTTPException(
            status_code=403,
            detail="您没有权限修改该记录"
        )
    
    # 更新字段
    if record_update.type:
        record.type = record_update.type
    if record_update.category:
        record.category = record_update.category
    if record_update.amount:
        record.amount = record_update.amount
    if record_update.note is not None:
        record.note = record_update.note
    
    await db.commit()
    
    return {"success": True, "message": "记录更新成功"}

@router.delete("/{record_id}")
async def delete_record(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """删除记账记录"""
    stmt = select(AccountRecord).where(AccountRecord.id == record_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail="记录不存在"
        )
    
    # 验证权限（只有记录创建者、家庭管理员、系统管理员可以删除）
    user_family_id = await get_user_family_id(current_user, db)
    can_delete = (
        record.user_id == current_user.id or
        current_user.role in ["system_admin", "family_admin"]
    )
    
    if record.family_id != user_family_id and current_user.role not in ["system_admin", "family_admin"]:
        can_delete = False
    
    if not can_delete:
        raise HTTPException(
            status_code=403,
            detail="您没有权限删除该记录"
        )
    
    await db.delete(record)
    await db.commit()
    
    return {"success": True, "message": "记录删除成功"}