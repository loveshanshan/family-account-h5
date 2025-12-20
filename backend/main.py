from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import models

# 1. 配置
SECRET_KEY = "family_secret_key_change_me" # 生产环境建议更换
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 登录有效期7天

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI()

# 2. 跨域配置 (允许前端访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 部署时可限制为你的域名
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 数据库初始化
models.init_db()

def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 工具函数 ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- API 接口 ---

# 注册 (仅供初始创建账号)
@app.post("/api/register")
def register(phone: str, password: str, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.phone == phone).first()
    if db_user:
        raise HTTPException(status_code=400, detail="手机号已注册")
    hashed_pwd = pwd_context.hash(password)
    new_user = models.User(phone=phone, password_hash=hashed_pwd)
    db.add(new_user)
    db.commit()
    return {"msg": "注册成功"}

# 登录
@app.post("/api/login")
def login(phone: str, password: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.phone == phone).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")
    
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

# 获取账单记录 (简单演示，不带分页)
@app.get("/api/records")
def get_records(db: Session = Depends(get_db)):
    # 实际开发中这里应该根据 Token 获取当前用户 ID
    return db.query(models.Record).order_by(models.Record.date.desc()).all()

# 新增账单
@app.post("/api/records")
def create_record(amount: float, category: str, type: str, note: str = "", db: Session = Depends(get_db)):
    new_record = models.Record(amount=amount, category=category, type=type, note=note)
    db.add(new_record)
    db.commit()
    return {"msg": "保存成功"}