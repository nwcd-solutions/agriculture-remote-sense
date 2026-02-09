# 卫星 GIS 平台

基于 AWS Open Data 的卫星遥感数据处理平台，提供类似 Google Earth Engine 的私有化解决方案。

## 📋 目录

- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [技术栈](#-技术栈)
- [API 文档](#-api-文档)
- [故障排除](#-故障排除)
- [开发指南](#-开发指南)

## 🌟 功能特性

- **多卫星数据源** - 支持 Sentinel-2、Landsat 8、MODIS（计划中）
- **交互式地图** - 基于 Leaflet，支持 AOI 绘制和可视化
- **植被指数计算** - NDVI、SAVI、EVI、VGI
- **异步任务处理** - 后台处理大规模数据，实时状态跟踪
- **COG 输出** - Cloud Optimized GeoTIFF 格式
- **STAC API 集成** - 标准化的卫星数据查询
- **无需 AWS 凭证** - 自动使用公开 HTTPS 访问

## 🚀 快速开始

### 前置要求

- Python 3.9+ (推荐 3.11)
- Node.js 16+ (推荐 18+)
- Conda (推荐用于安装 geospatial 依赖)

### 使用 Conda（推荐）

```bash
# 创建环境并安装依赖
conda create -n satellite-gis python=3.11
conda activate satellite-gis
conda install -c conda-forge gdal rasterio rioxarray fiona shapely pyproj

# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env
python main.py  # http://localhost:8000

# 前端（新终端）
cd frontend
npm install
cp .env.example .env
npm start  # http://localhost:3000
```

### 使用 Docker

```bash
docker-compose up --build
# 后端: http://localhost:8000
# 前端: http://localhost:3000
```

## 📖 使用指南

1. **绘制 AOI** - 在地图上使用绘图工具绘制感兴趣区域
2. **查询影像** - 选择卫星类型、时间范围、云量阈值，点击查询
3. **计算指数** - 选择影像和植被指数（NDVI/SAVI/EVI），开始处理
4. **查看结果** - 查看任务状态，下载 GeoTIFF 文件或在 QGIS 中打开

## 🔧 技术栈

**后端**: FastAPI, GDAL 3.7+, rasterio, rioxarray, numpy, xarray, shapely, pystac-client

**前端**: React 18, Leaflet, Ant Design, Zustand, Axios

## 📊 API 文档

启动后端后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

主要端点：
- `POST /api/query` - 查询卫星影像
- `POST /api/process/indices` - 提交植被指数计算任务
- `GET /api/process/tasks/{task_id}` - 查询任务状态
- `GET /api/process/tasks` - 获取任务列表

## 🐛 故障排除

### numpy 版本不兼容
```bash
# 错误: AttributeError: np.unicode_ was removed
pip install "numpy<2.0" --force-reinstall
```

### GDAL 配置问题
系统已自动配置以下环境变量：
- `GDAL_MEM_ENABLE_OPEN=YES` - 启用内存数据集
- `GDAL_HTTP_TIMEOUT=600` - 10分钟超时
- `GDAL_HTTP_MAX_RETRY=5` - 最多重试5次

### S3 访问失败
前端已自动将 S3 URL 转换为 HTTPS URL，无需 AWS 凭证。

### Windows 安装 GDAL
从 [Christoph Gohlke's 网站](https://www.lfd.uci.edu/~gohlke/pythonlibs/) 下载预编译的 wheel 文件并安装。

## 📝 开发指南

### 项目结构

```
backend/
├── app/
│   ├── api/          # API 路由 (aoi, query, process)
│   ├── models/       # 数据模型
│   └── services/     # 业务逻辑 (STAC, 栅格处理, 植被指数)
├── tests/            # 测试
└── main.py           # 入口

frontend/
├── src/
│   ├── components/   # React 组件 (地图, 查询, 结果面板)
│   └── App.js        # 主应用
└── package.json
```

### 添加新植被指数

1. 在 `backend/app/services/vegetation_index_calculator.py` 添加计算方法
2. 在 `backend/app/models/processing.py` 更新枚举类型
3. 在 `frontend/src/components/ProcessingConfigPanel.js` 添加选项

### 添加新卫星数据源

1. 在 `backend/app/services/stac_service.py` 添加查询方法
2. 在 `backend/app/api/query.py` 更新路由
3. 在 `frontend/src/components/DataQueryPanel.js` 添加选项

### 测试

```bash
# 后端
cd backend && pytest

# 前端
cd frontend && npm test
```

### 环境变量

**后端 (.env)**
```bash
HOST=0.0.0.0
PORT=8000
STAC_API_URL=https://earth-search.aws.element84.com/v1
```

**前端 (.env)**
```bash
REACT_APP_API_URL=http://localhost:8000
```

## 📄 许可证

MIT License

---

**版本**: 1.0.0 | **状态**: ✅ 生产就绪 | **更新**: 2026-02-09
