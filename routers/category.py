from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional

from database import get_db
from schemas import CategoryCreate, CategoryUpdate, Category as CategorySchema
from utils.auth import get_current_active_user, get_admin_user
from models import Category, User, FamilyMember, RecordType

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

@router.post("/create", response_model=CategorySchema)
async def create_category(
    category: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """创建分类"""
    # 获取用户所在家庭
    family_id = await get_user_family_id(current_user, db)
    if not family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您还没有加入任何家庭"
        )
    
    # 检查分类名称是否已存在
    existing_stmt = select(Category).where(
        and_(
            Category.family_id == family_id,
            Category.name == category.name,
            Category.type == category.type,
            Category.is_active == True
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing_category = existing_result.scalar_one_or_none()
    
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{category.type}分类 '{category.name}' 已存在"
        )
    
    # 创建新分类
    db_category = Category(
        family_id=family_id,
        name=category.name,
        type=category.type,
        icon=category.icon,
        color=category.color,
        created_by=current_user.id
    )
    
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    
    return db_category

@router.get("/list")
async def get_categories(
    record_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取分类列表"""
    # 获取用户所在家庭
    family_id = await get_user_family_id(current_user, db)
    if not family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您还没有加入任何家庭"
        )
    
    # 构建查询条件
    conditions = [
        Category.family_id == family_id,
        Category.is_active == True
    ]
    
    if record_type and record_type in ["income", "expense"]:
        conditions.append(Category.type == record_type)
    
    stmt = select(Category).where(and_(*conditions)).order_by(Category.name)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    
    # 按类型分组
    income_categories = []
    expense_categories = []
    
    for category in categories:
        if category.type == RecordType.INCOME:
            income_categories.append(category)
        else:
            expense_categories.append(category)
    
    return {
        "success": True,
        "data": {
            "income": income_categories,
            "expense": expense_categories,
            "all": categories
        }
    }

@router.put("/update/{category_id}")
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """更新分类"""
    # 检查分类是否存在
    stmt = select(Category).where(Category.id == category_id)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    # 更新字段
    if category_update.name is not None:
        category.name = category_update.name
    if category_update.icon is not None:
        category.icon = category_update.icon
    if category_update.color is not None:
        category.color = category_update.color
    
    await db.commit()
    await db.refresh(category)
    
    return category

@router.delete("/delete/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """删除分类（软删除）"""
    # 检查分类是否存在
    stmt = select(Category).where(Category.id == category_id)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    # 软删除：标记为非活跃
    category.is_active = False
    await db.commit()
    
    return {"success": True, "message": "分类删除成功"}

@router.post("/init-default")
async def init_default_categories(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """初始化默认分类"""
    # 获取用户所在家庭
    family_id = await get_user_family_id(current_user, db)
    if not family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您还没有加入任何家庭"
        )
    
    # 默认分类
    default_categories = [
        # 收入分类
        {"name": "工资", "type": RecordType.INCOME, "icon": "💰", "color": "#52c41a"},
        {"name": "奖金", "type": RecordType.INCOME, "icon": "🎁", "color": "#52c41a"},
        {"name": "投资收益", "type": RecordType.INCOME, "icon": "📈", "color": "#52c41a"},
        {"name": "兼职收入", "type": RecordType.INCOME, "icon": "💼", "color": "#52c41a"},
        {"name": "其他收入", "type": RecordType.INCOME, "icon": "💵", "color": "#52c41a"},
        
        # 支出分类
        {"name": "餐饮", "type": RecordType.EXPENSE, "icon": "🍔", "color": "#ff4d4f"},
        {"name": "交通", "type": RecordType.EXPENSE, "icon": "🚗", "color": "#ff4d4f"},
        {"name": "购物", "type": RecordType.EXPENSE, "icon": "🛒", "color": "#ff4d4f"},
        {"name": "娱乐", "type": RecordType.EXPENSE, "icon": "🎮", "color": "#ff4d4f"},
        {"name": "医疗", "type": RecordType.EXPENSE, "icon": "🏥", "color": "#ff4d4f"},
        {"name": "教育", "type": RecordType.EXPENSE, "icon": "📚", "color": "#ff4d4f"},
        {"name": "居住", "type": RecordType.EXPENSE, "icon": "🏠", "color": "#ff4d4f"},
        {"name": "其他支出", "type": RecordType.EXPENSE, "icon": "💸", "color": "#ff4d4f"},
    ]
    
    created_count = 0
    
    for cat_data in default_categories:
        # 检查是否已存在
        existing_stmt = select(Category).where(
            and_(
                Category.family_id == family_id,
                Category.name == cat_data["name"],
                Category.type == cat_data["type"],
                Category.is_active == True
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing_category = existing_result.scalar_one_or_none()
        
        if not existing_category:
            # 创建新分类
            db_category = Category(
                family_id=family_id,
                name=cat_data["name"],
                type=cat_data["type"],
                icon=cat_data["icon"],
                color=cat_data["color"],
                created_by=current_user.id
            )
            db.add(db_category)
            created_count += 1
    
    await db.commit()
    
    return {
        "success": True, 
        "message": f"已初始化 {created_count} 个默认分类"
    }