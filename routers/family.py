from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional

from database import get_db
from schemas import FamilyCreate, FamilyUpdate, FamilyMemberCreate, FamilyMemberWithUser, FamilyWithMembers, Family as FamilySchema
from utils.auth import get_current_active_user, get_admin_user
from models import Family, FamilyMember, User, AccountRecord, UserRole, RecordType

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

async def get_family_admin_user(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取家庭管理员权限用户"""
    # 系统管理员有所有权限
    if current_user.role == "system_admin":
        return current_user
    
    # 检查是否是家庭管理员
    stmt = select(FamilyMember).where(
        FamilyMember.user_id == current_user.id,
        FamilyMember.role == "family_admin",
        FamilyMember.is_active == True
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要家庭管理员权限"
        )
    
    return current_user

@router.post("/create", response_model=FamilySchema)
async def create_family(
    family: FamilyCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """创建家庭"""
    db_family = Family(
        name=family.name,
        description=family.description,
        created_by=current_user.id
    )
    
    db.add(db_family)
    await db.commit()
    await db.refresh(db_family)
    
    # 创建者自动成为家庭管理员
    family_member = FamilyMember(
        family_id=db_family.id,
        user_id=current_user.id,
        role="family_admin"
    )
    db.add(family_member)
    await db.commit()
    
    return db_family

@router.get("/my-family")
async def get_my_family(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我所在的家庭"""
    # 查找用户所在的家庭
    stmt = select(FamilyMember).where(
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=404,
            detail="您还没有加入任何家庭"
        )
    
    # 获取家庭信息
    family_stmt = select(Family).where(Family.id == membership.family_id)
    family_result = await db.execute(family_stmt)
    family = family_result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=404,
            detail="家庭不存在"
        )
    
    # 获取家庭成员
    member_stmt = select(FamilyMember).where(
        FamilyMember.family_id == family.id,
        FamilyMember.is_active == True
    )
    member_result = await db.execute(member_stmt)
    members = member_result.scalars().all()
    
    # 添加用户信息
    members_with_user = []
    for member in members:
        user_stmt = select(User).where(User.id == member.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        members_with_user.append(FamilyMemberWithUser(
            id=member.id,
            family_id=member.family_id,
            user_id=member.user_id,
            user_name=user.name if user else "未知用户",
            user_phone=user.phone if user else "",
            role=member.role,
            joined_at=member.joined_at,
            is_active=member.is_active
        ))
    
    return FamilyWithMembers(
        id=family.id,
        name=family.name,
        description=family.description,
        created_by=family.created_by,
        is_active=family.is_active,
        created_at=family.created_at,
        members=members_with_user
    )

@router.post("/add-member")
async def add_family_member(
    member_data: FamilyMemberCreate,
    current_user: User = Depends(get_family_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """添加家庭成员"""
    # 检查家庭是否存在
    family_stmt = select(Family).where(Family.id == member_data.family_id)
    family_result = await db.execute(family_stmt)
    family = family_result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=404,
            detail="家庭不存在"
        )
    
    # 检查用户是否存在
    user_stmt = select(User).where(User.id == member_data.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    # 检查是否已经是家庭成员
    existing_stmt = select(FamilyMember).where(
        and_(
            FamilyMember.family_id == member_data.family_id,
            FamilyMember.user_id == member_data.user_id,
            FamilyMember.is_active == True
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing_member = existing_result.scalar_one_or_none()
    
    if existing_member:
        raise HTTPException(
            status_code=400,
            detail="该用户已经是家庭成员"
        )
    
    # 创建家庭成员
    print(f"创建家庭成员: family_id={member_data.family_id}, user_id={member_data.user_id}, role={member_data.role}")
    print(f"角色类型: {type(member_data.role)}, 值: {member_data.role}")
    
    try:
        family_member = FamilyMember(
            family_id=member_data.family_id,
            user_id=member_data.user_id,
            role=member_data.role
        )
        db.add(family_member)
        await db.commit()
    except Exception as e:
        print(f"创建家庭成员失败: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"创建家庭成员失败: {str(e)}"
        )
    
    
    return {"success": True, "message": "家庭成员添加成功"}

@router.delete("/remove-member/{member_id}")
async def remove_family_member(
    member_id: int,
    current_user: User = Depends(get_family_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """移除家庭成员"""
    stmt = select(FamilyMember).where(FamilyMember.id == member_id)
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=404,
            detail="家庭成员不存在"
        )
    
    # 获取用户信息以检查角色
    user_stmt = select(User).where(User.id == member.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    # 不能移除系统管理员
    if user and user.role == "system_admin":
        raise HTTPException(
            status_code=400,
            detail="不能移除系统管理员"
        )
    
    # 标记为非活跃（软删除）
    member.is_active = False
    await db.commit()
    
    return {"success": True, "message": "家庭成员移除成功"}

@router.put("/update/{family_id}")
async def update_family(
    family_id: int,
    family_update: FamilyUpdate,
    current_user: User = Depends(get_family_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """更新家庭信息"""
    # 检查家庭是否存在
    stmt = select(Family).where(Family.id == family_id)
    result = await db.execute(stmt)
    family = result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=404,
            detail="家庭不存在"
        )
    
    # 更新字段
    if family_update.name is not None:
        family.name = family_update.name
    if family_update.description is not None:
        family.description = family_update.description
    
    await db.commit()
    await db.refresh(family)
    
    return family

@router.delete("/cleanup-members")
async def cleanup_test_members(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """清理测试家庭成员数据"""
    # 清理非活跃的家庭成员
    stmt = select(FamilyMember).where(FamilyMember.is_active == False)
    result = await db.execute(stmt)
    inactive_members = result.scalars().all()
    
    count = 0
    for member in inactive_members:
        # 检查是否为测试用户（手机号包含特定标识）
        if member.user and ('test' in member.user.phone.lower() or '测试' in member.user.name):
            await db.delete(member)
            count += 1
    
    await db.commit()
    
    return {"success": True, "message": f"已清理 {count} 个测试家庭成员"}

@router.post("/create-family", response_model=FamilySchema)
async def quick_create_family(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """快速创建家庭"""
    # 检查用户是否已经在家庭中
    existing_stmt = select(FamilyMember).where(
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    )
    existing_result = await db.execute(existing_stmt)
    existing_membership = existing_result.scalar_one_or_none()
    
    if existing_membership:
        raise HTTPException(
            status_code=400,
            detail="您已经在一个家庭中了"
        )
    
    # 创建新家庭
    db_family = Family(
        name=f"{current_user.name}的家庭",
        description=f"{current_user.name}创建的家庭",
        created_by=current_user.id
    )
    
    db.add(db_family)
    await db.commit()
    await db.refresh(db_family)
    
    # 创建者自动成为家庭管理员
    family_member = FamilyMember(
        family_id=db_family.id,
        user_id=current_user.id,
        role="family_admin"
    )
    db.add(family_member)
    await db.commit()
    
    return db_family

@router.get("/statistics")
async def get_family_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取家庭统计数据"""
    from schemas import Statistics, CategoryStats, TrendData, FamilyRanking
    from datetime import datetime, timedelta
    
    # 获取用户所在家庭
    member_stmt = select(FamilyMember).where(
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    )
    member_result = await db.execute(member_stmt)
    membership = member_result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=404,
            detail="您还没有加入任何家庭"
        )
    
    family_id = membership.family_id
    
    # 计算总收入、总支出
    income_stmt = select(func.sum(AccountRecord.amount)).where(
        and_(
            AccountRecord.family_id == family_id,
            AccountRecord.type == RecordType.INCOME
        )
    )
    expense_stmt = select(func.sum(AccountRecord.amount)).where(
        and_(
            AccountRecord.family_id == family_id,
            AccountRecord.type == RecordType.EXPENSE
        )
    )
    
    income_result = await db.execute(income_stmt)
    expense_result = await db.execute(expense_stmt)
    
    total_income = income_result.scalar() or 0
    total_expense = expense_result.scalar() or 0
    balance = total_income - total_expense
    
    # 按分类统计支出
    expense_category_stmt = select(
        AccountRecord.category,
        func.sum(AccountRecord.amount).label("total_amount")
    ).where(
        and_(
            AccountRecord.family_id == family_id,
            AccountRecord.type == RecordType.EXPENSE
        )
    ).group_by(AccountRecord.category)
    
    expense_category_result = await db.execute(expense_category_stmt)
    expense_category_rows = expense_category_result.all()
    
    expense_by_category = []
    for category, amount in expense_category_rows:
        percentage = (amount / total_expense * 100) if total_expense > 0 else 0
        expense_by_category.append(CategoryStats(
            category=category,
            amount=float(amount),
            percentage=float(percentage)
        ))
    
    # 按分类统计收入
    income_category_stmt = select(
        AccountRecord.category,
        func.sum(AccountRecord.amount).label("total_amount")
    ).where(
        and_(
            AccountRecord.family_id == family_id,
            AccountRecord.type == RecordType.INCOME
        )
    ).group_by(AccountRecord.category)
    
    income_category_result = await db.execute(income_category_stmt)
    income_category_rows = income_category_result.all()
    
    income_by_category = []
    for category, amount in income_category_rows:
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        income_by_category.append(CategoryStats(
            category=category,
            amount=float(amount),
            percentage=float(percentage)
        ))
    
    # 生成趋势数据（最近6个月）
    trend_data = []
    now = datetime.now()
    for i in range(5, -1, -1):  # 从6个月前到现在
        month_start = datetime(now.year, now.month - i if now.month - i > 0 else 12, 1)
        if now.month - i <= 0:
            month_start = datetime(now.year - 1, now.month - i + 12, 1)
        
        month_end = datetime(month_start.year, month_start.month, 1) + timedelta(days=32)
        month_end = datetime(month_end.year, month_end.month, 1) - timedelta(days=1)
        
        # 计算当月收入和支出
        month_income_stmt = select(func.sum(AccountRecord.amount)).where(
            and_(
                AccountRecord.family_id == family_id,
                AccountRecord.type == RecordType.INCOME,
                AccountRecord.date >= month_start.date(),
                AccountRecord.date <= month_end.date()
            )
        )
        
        month_expense_stmt = select(func.sum(AccountRecord.amount)).where(
            and_(
                AccountRecord.family_id == family_id,
                AccountRecord.type == RecordType.EXPENSE,
                AccountRecord.date >= month_start.date(),
                AccountRecord.date <= month_end.date()
            )
        )
        
        month_income_result = await db.execute(month_income_stmt)
        month_expense_result = await db.execute(month_expense_stmt)
        
        month_income = month_income_result.scalar() or 0
        month_expense = month_expense_result.scalar() or 0
        
        trend_data.append(TrendData(
            date=f"{month_start.year}年{month_start.month}月",
            income=float(month_income),
            expense=float(month_expense)
        ))
    
    # 生成家庭排行榜数据
    ranking_stmt = select(
        User.name,
        func.count(AccountRecord.id).label("record_count"),
        func.sum(AccountRecord.amount).label("total_amount")
    ).join(
        FamilyMember, AccountRecord.user_id == FamilyMember.user_id
    ).join(
        User, FamilyMember.user_id == User.id
    ).where(
        and_(
            FamilyMember.family_id == family_id,
            FamilyMember.is_active == True
        )
    ).group_by(
        User.id, User.name
    ).order_by(
        func.count(AccountRecord.id).desc()
    )
    
    ranking_result = await db.execute(ranking_stmt)
    ranking_rows = ranking_result.all()
    
    family_ranking = []
    for name, record_count, total_amount in ranking_rows:
        family_ranking.append(FamilyRanking(
            name=name,
            record_count=record_count,
            total_amount=float(total_amount or 0)
        ))
    
    # 返回统计数据
    statistics = Statistics(
        total_income=float(total_income),
        total_expense=float(total_expense),
        balance=float(balance),
        income_trend=0.0,  # 这里需要计算趋势
        expense_trend=0.0,
        balance_trend=0.0,
        expense_by_category=expense_by_category,
        income_by_category=income_by_category,
        trend_data=trend_data,
        family_ranking=family_ranking
    )
    
    return {"success": True, "data": statistics}