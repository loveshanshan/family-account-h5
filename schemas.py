from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, RecordType

# 用户相关
class UserBase(BaseModel):
    phone: str
    name: str
    role: Optional[UserRole] = UserRole.FAMILY_MEMBER

class UserCreate(UserBase):
    password: str
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v.isdigit() or len(v) < 11:
            raise ValueError('手机号格式不正确')
        return v

class UserLogin(BaseModel):
    phone: str
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and (not v.isdigit() or len(v) < 11):
            raise ValueError('手机号格式不正确')
        return v

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class PasswordReset(BaseModel):
    phone: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# 账本记录相关
class AccountRecordBase(BaseModel):
    type: RecordType
    category: str
    amount: float
    note: Optional[str] = None
    date: Optional[datetime] = None

class AccountRecordCreate(AccountRecordBase):
    family_id: int

class AccountRecordUpdate(BaseModel):
    type: Optional[RecordType] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    note: Optional[str] = None

class AccountRecord(AccountRecordBase):
    id: int
    family_id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AccountRecordWithUser(AccountRecord):
    user_name: str

# 家庭相关
class FamilyBase(BaseModel):
    name: str
    description: Optional[str] = None

class FamilyCreate(FamilyBase):
    pass

class FamilyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Family(FamilyBase):
    id: int
    created_by: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class FamilyMemberBase(BaseModel):
    user_id: int
    role: UserRole

class FamilyMemberCreate(FamilyMemberBase):
    family_id: int

class FamilyMemberUpdate(BaseModel):
    role: Optional[UserRole] = None

class FamilyMember(FamilyMemberBase):
    id: int
    family_id: int
    joined_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class FamilyMemberWithUser(FamilyMember):
    user_name: str
    user_phone: str

class FamilyWithMembers(Family):
    members: List[FamilyMemberWithUser]

# 统计相关
class CategoryStats(BaseModel):
    category: str
    amount: float
    percentage: float

class TrendData(BaseModel):
    date: str
    income: float
    expense: float

class FamilyRanking(BaseModel):
    name: str
    record_count: int
    total_amount: float

class Statistics(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    income_trend: float
    expense_trend: float
    balance_trend: float
    expense_by_category: List[CategoryStats]
    income_by_category: List[CategoryStats]
    trend_data: List[TrendData]
    family_ranking: List[FamilyRanking]

# 系统管理相关
class SystemStats(BaseModel):
    total_users: int
    total_families: int
    total_records: int
    total_amount: float

class AdminUserCreate(BaseModel):
    name: str
    phone: str
    password: str
    role: UserRole

# 分类相关
class CategoryBase(BaseModel):
    name: str
    type: RecordType
    icon: Optional[str] = "📝"
    color: Optional[str] = "#1989fa"

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class Category(CategoryBase):
    id: int
    family_id: int
    is_active: bool
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# 通用响应
class Response(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User