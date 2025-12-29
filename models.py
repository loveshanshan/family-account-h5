from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base

class UserRole(str, enum.Enum):
    SYSTEM_ADMIN = "system_admin"
    FAMILY_ADMIN = "family_admin"
    FAMILY_MEMBER = "family_member"

class RecordType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.FAMILY_MEMBER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    family_memberships = relationship("FamilyMember", back_populates="user")
    records = relationship("AccountRecord", back_populates="user")

class Family(Base):
    __tablename__ = "families"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    creator = relationship("User")
    members = relationship("FamilyMember", back_populates="family")
    records = relationship("AccountRecord", back_populates="family")

class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.FAMILY_MEMBER)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # 关联关系
    family = relationship("Family", back_populates="members")
    user = relationship("User", back_populates="family_memberships")

class AccountRecord(Base):
    __tablename__ = "account_records"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(RecordType), nullable=False)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    note = Column(Text, nullable=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    family = relationship("Family", back_populates="records")
    user = relationship("User", back_populates="records")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    name = Column(String(50), nullable=False)
    type = Column(Enum(RecordType), nullable=False)  # income 或 expense
    icon = Column(String(20), nullable=True, default="📝")  # 表情符号图标
    color = Column(String(7), nullable=True, default="#1989fa")  # 颜色代码
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    family = relationship("Family")
    creator = relationship("User")