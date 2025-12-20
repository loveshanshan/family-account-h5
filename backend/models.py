from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# 数据库文件位置：当前目录下名为 account.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./account.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 用户表
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True)
    password_hash = Column(String)

# 账单记录表
class Record(Base):
    __tablename__ = "records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    category = Column(String) # 如：餐饮、交通、收入
    type = Column(String)     # 支出 / 收入
    note = Column(String)
    date = Column(DateTime, default=datetime.datetime.now)

# 创建所有表
def init_db():
    Base.metadata.create_all(bind=engine)