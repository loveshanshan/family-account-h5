import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 应用配置
    APP_NAME = "家庭账本系统"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # 数据库配置
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:password@localhost/family_account")
    
    # JWT配置
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60 * 60  # 24小时
    
    # Redis配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # 系统管理员配置
    ADMIN_PHONE = os.getenv("ADMIN_PHONE", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "336699")
    
    # CORS配置
    CORS_ORIGINS = [
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "http://8.138.207.21:3001",
        "http://8.138.207.21/account"
    ]
    
    # 分页配置
    PAGE_SIZE = 20
    
    # 文件上传配置
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

config = Config()