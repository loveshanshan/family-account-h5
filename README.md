# 后端

# 测试环境启动服务
uvicorn main:app --reload


# 前端
 
# 测试环境启动服务
npm run dev


# 服务器部署
# 前端：
1, npm run build  (生成生产环境文件)
2, scp -r ./frontend/dist/* root@8.138.207.21:/opt/family-account/frontend/.   （将版本提供到生产环境）
# 后端：

