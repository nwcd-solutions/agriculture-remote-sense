"""
卫星 GIS 平台 - FastAPI 后端主应用
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from app.api import aoi  # Disabled for Lambda (not used by frontend)
from app.api import query, process

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用实例
app = FastAPI(
    title="卫星 GIS 平台 API",
    description="基于 AWS Open Data 的综合卫星遥感数据处理 Web 应用",
    version="0.1.0"
)

# 从环境变量读取 CORS 配置
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
# 支持逗号分隔的多个源
if cors_origins == "*":
    origins_list = ["*"]
else:
    origins_list = [origin.strip() for origin in cors_origins.split(",")]

logger.info(f"CORS Origins configured: {origins_list}")

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_credentials=True if origins_list != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
# app.include_router(aoi.router)  # Disabled for Lambda
app.include_router(query.router)
app.include_router(process.router)

@app.get("/")
async def root():
    """根端点 - 健康检查"""
    return {
        "status": "ok",
        "message": "卫星 GIS 平台 API 正在运行",
        "version": "0.1.0"
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "satellite-gis-platform"
    }

if __name__ == "__main__":
    import uvicorn
    # 从环境变量读取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
