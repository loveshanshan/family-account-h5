from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from config import config
from database import engine, Base, AsyncSessionLocal, async_engine
from routers import auth, user, account, family, admin, category
from models import User

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("家庭账本系统启动中...")
    
    # 异步创建数据库表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 初始化系统管理员
    await init_admin()
    
    print("系统启动完成")
    yield
    
    # 关闭时执行
    print("系统关闭中...")

app = FastAPI(
    title=config.APP_NAME,
    version=config.VERSION,
    description="家庭账本H5应用后端API",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(user.router, prefix="/api/user", tags=["用户"])
app.include_router(account.router, prefix="/api/account", tags=["账本"])
app.include_router(family.router, prefix="/api/family", tags=["家庭"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理员"])
app.include_router(category.router, prefix="/api/category", tags=["分类"])

# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "code": 500
        }
    )

# 健康检查
@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "message": "家庭账本系统运行正常",
        "version": config.VERSION
    }

async def init_admin():
    """初始化系统管理员"""
    from database import get_db
    from utils.auth import get_password_hash
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        # 检查是否已存在系统管理员
        stmt = select(User).where(User.phone == config.ADMIN_PHONE)
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()
        
        if not admin:
            # 创建系统管理员
            admin = User(
                phone=config.ADMIN_PHONE,
                name="系统管理员",
                hashed_password=get_password_hash(config.ADMIN_PASSWORD),
                role="system_admin",
                is_active=True
            )
            db.add(admin)
            await db.commit()
            print(f"系统管理员初始化成功 - 账号: {config.ADMIN_PHONE}, 密码: {config.ADMIN_PASSWORD}")
        else:
            print("系统管理员已存在")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3001,
        reload=config.DEBUG
    )