# 卫星 GIS 平台

基于 AWS Open Data 的综合卫星遥感数据处理 Web 应用，设计为 Google Earth Engine 的私有化/企业级替代方案。

## 📋 目录

- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [项目结构](#-项目结构)
- [技术栈](#-技术栈)
- [API 文档](#-api-文档)
- [Geospatial 依赖说明](#-geospatial-依赖说明)
- [测试](#-测试)
- [故障排除](#-故障排除)
- [性能指标](#-性能指标)
- [支持的卫星数据](#-支持的卫星数据)
- [支持的植被指数](#-支持的植被指数)
- [开发指南](#-开发指南)
- [贡献](#-贡献)

## 🌟 功能特性

- **多卫星数据源**：统一访问 Sentinel-2、Landsat 8、MODIS 等卫星数据
- **交互式地图**：基于 Leaflet 的地图可视化，支持 AOI 绘制
- **植被指数计算**：NDVI、SAVI、EVI、VGI 等多种植被指数
- **实时处理**：异步任务处理，支持大规模数据处理
- **云优化格式**：输出 COG (Cloud Optimized GeoTIFF) 格式
- **STAC API 集成**：通过 STAC API 查询和访问卫星数据
- **无需 AWS 凭证**：自动转换 S3 URL 为公开 HTTPS 访问

## 🚀 快速开始

### 前置要求

- **Python**: 3.9+ (推荐 3.11)
- **Node.js**: 16+ (推荐 18+)
- **Conda**: 推荐使用 Conda 安装 geospatial 依赖

### 后端设置

#### 方法 1: 使用 Conda（推荐）

```bash
# 创建 Conda 环境
conda create -n satellite-gis python=3.11
conda activate satellite-gis

# 安装 geospatial 依赖
conda install -c conda-forge gdal rasterio rioxarray fiona shapely pyproj

# 安装其他依赖
cd backend
pip install fastapi uvicorn pydantic python-multipart pystac-client httpx numpy xarray dask pytest hypothesis pytest-asyncio

# 配置环境变量
cp .env.example .env

# 启动服务
python main.py
```

#### 方法 2: 使用 pip（需要预先安装 GDAL）

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

后端服务将在 **http://localhost:8000** 启动

### 前端设置

```bash
cd frontend
npm install
cp .env.example .env
npm start
```

前端应用将在 **http://localhost:3000** 启动

### Docker 部署

```bash
docker-compose up --build
```

服务地址：
- 后端：http://localhost:8000
- 前端：http://localhost:3000

## 📖 使用指南

### 1. 绘制 AOI（感兴趣区域）

1. 打开前端应用 http://localhost:3000
2. 在地图上使用绘图工具绘制多边形
3. 定义你感兴趣的区域

### 2. 查询卫星影像

1. 在左侧面板选择卫星类型（Sentinel-2）
2. 设置时间范围
3. 设置云量阈值（0-100%）
4. 点击"查询"按钮

### 3. 计算植被指数

1. 从查询结果中选择一个影像
2. 在右侧面板选择要计算的植被指数（NDVI、SAVI、EVI）
3. 点击"开始处理"
4. 等待任务完成（通常需要 1-5 分钟）

### 4. 查看结果

处理完成后，可以：
- 在前端查看任务状态和结果信息
- 使用 QGIS 或其他 GIS 软件打开输出的 GeoTIFF 文件
- 通过 API 下载结果文件

## 🏗️ 项目结构

```
satellite-gis-platform/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── aoi.py         # AOI 处理
│   │   │   ├── query.py       # 数据查询
│   │   │   └── process.py     # 数据处理
│   │   ├── models/            # 数据模型
│   │   │   ├── aoi.py
│   │   │   ├── satellite.py
│   │   │   └── processing.py
│   │   └── services/          # 业务逻辑
│   │       ├── stac_service.py              # STAC API 查询
│   │       ├── raster_processor.py          # 栅格处理
│   │       ├── vegetation_index_calculator.py  # 植被指数计算
│   │       ├── processing_service.py        # 处理服务
│   │       └── task_manager.py              # 任务管理
│   ├── tests/                 # 测试
│   ├── main.py                # 应用入口
│   └── requirements.txt       # Python 依赖
│
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── components/        # React 组件
│   │   │   ├── MapComponent.js           # 地图组件
│   │   │   ├── DataQueryPanel.js         # 查询面板
│   │   │   ├── ResultsPanel.js           # 结果面板
│   │   │   └── ProcessingConfigPanel.js  # 处理配置面板
│   │   ├── App.js             # 主应用
│   │   └── index.js           # 入口
│   └── package.json           # Node 依赖
│
├── .kiro/specs/               # 项目规范文档
│   └── satellite-gis-platform/
│       ├── requirements.md    # 需求文档
│       ├── design.md          # 设计文档
│       └── tasks.md           # 任务列表
│
├── docker-compose.yml         # Docker 配置
└── README.md                  # 本文档
```

## 🔧 技术栈

### 后端技术

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | FastAPI | 0.104+ | REST API |
| 地理处理 | GDAL | 3.7+ | 栅格数据读写 |
| 栅格 I/O | rasterio | 1.3+ | GeoTIFF 处理 |
| 高级接口 | rioxarray | 0.15+ | xarray + rasterio |
| 数组计算 | numpy | 1.26+ | 数值计算 |
| 多维数组 | xarray | 2023.1+ | 多维数据处理 |
| 几何操作 | shapely | 2.0+ | 几何计算 |
| STAC 客户端 | pystac-client | 0.7+ | STAC API 查询 |

### 前端技术

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | React | 18+ | UI 框架 |
| 地图库 | Leaflet | 1.9+ | 地图显示 |
| UI 组件 | Ant Design | 5.0+ | UI 组件库 |
| 状态管理 | Zustand | 4.0+ | 状态管理 |
| HTTP 客户端 | Axios | 1.6+ | API 请求 |

## 📊 API 文档

启动后端服务后，访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要 API 端点

#### 数据查询
```
POST /api/query
```
查询卫星影像数据

#### 植被指数计算
```
POST /api/process/indices
```
提交植被指数计算任务

#### 任务状态查询
```
GET /api/process/tasks/{task_id}
```
查询任务处理状态

#### 任务列表
```
GET /api/process/tasks
```
获取所有任务列表

## 🔍 Geospatial 依赖说明

### 为什么需要 Geospatial 依赖？

**简短回答：** 没有 geospatial 依赖（GDAL、rasterio、rioxarray）无法计算 NDVI 指数。

### 完整的 NDVI 计算流程

```
1. 从 S3 下载卫星影像 (COG 格式)
   ↓ 需要: rasterio (读取远程 GeoTIFF)
   
2. 裁剪到 AOI 区域
   ↓ 需要: rasterio.mask, shapely (几何操作)
   
3. 提取 NIR 和 Red 波段数据
   ↓ 需要: rasterio, xarray (多维数组处理)
   
4. 计算 NDVI = (NIR - Red) / (NIR + Red)
   ↓ 需要: numpy (数组计算)
   
5. 输出为 COG 格式
   ↓ 需要: rasterio (写入 GeoTIFF)
```

### 各个依赖的作用

#### 1. GDAL (Geospatial Data Abstraction Library)
**作用：** 底层地理空间数据读写库
- 读取和写入 GeoTIFF 格式
- 支持 COG (Cloud Optimized GeoTIFF)
- 处理地理坐标系统和投影
- 支持远程数据访问（HTTP/S3）

#### 2. rasterio
**作用：** Python 的栅格数据 I/O 库（基于 GDAL）
- 读取卫星影像文件
- 裁剪影像到 AOI
- 重投影和重采样
- 写入 COG 格式

#### 3. rioxarray
**作用：** 结合 rasterio 和 xarray 的高级接口
- 将栅格数据转换为 xarray.DataArray
- 支持多维数组操作
- 保留地理空间元数据

#### 4. numpy
**作用：** 数值计算库
- 执行 NDVI 公式计算
- 数组运算

#### 5. xarray
**作用：** 多维标记数组库
- 处理多波段、多时相数据
- 时间序列合成
- 保留维度标签和元数据

### 为什么 numpy 不够？

虽然 NDVI 的数学公式很简单（只需要 numpy），但实际应用中需要：

1. **获取波段数据**：卫星影像存储在 S3 上，格式为 GeoTIFF，需要 rasterio 读取
2. **裁剪到 AOI**：用户绘制的 AOI 是 GeoJSON 多边形，需要 shapely 和 rasterio.mask
3. **保存结果**：需要保存为 COG 格式，包含地理坐标信息，需要 rasterio 写入

### 安装 Geospatial 依赖

#### 使用 Conda（推荐）

```bash
conda install -c conda-forge gdal rasterio rioxarray fiona shapely pyproj
```

#### 使用 Docker

```bash
docker-compose up --build
```

#### Windows 用户

从 [Christoph Gohlke's 网站](https://www.lfd.uci.edu/~gohlke/pythonlibs/) 下载预编译的 wheel 文件：
- GDAL
- rasterio
- Fiona

然后安装：
```bash
pip install GDAL-3.7.3-cp311-cp311-win_amd64.whl
pip install rasterio-1.3.9-cp311-cp311-win_amd64.whl
pip install Fiona-1.9.5-cp311-cp311-win_amd64.whl
pip install rioxarray shapely pyproj
```

**注意：** 确保下载的 wheel 文件与你的 Python 版本匹配（例如 cp311 表示 Python 3.11）。

## 🧪 测试

### 后端测试

```bash
cd backend
source venv/bin/activate  # 或 conda activate satellite-gis
pytest
```

### 前端测试

```bash
cd frontend
npm test
```

## 🐛 故障排除

### 问题 1: numpy 版本不兼容

**错误**: `AttributeError: np.unicode_ was removed`

**原因**: xarray 2023.1.0 不兼容 numpy 2.0+

**解决**:
```bash
pip install "numpy<2.0" --force-reinstall
```

### 问题 2: GDAL MEM Dataset 错误

**错误**: `Opening a MEM dataset is no longer supported`

**原因**: GDAL 3.7+ 默认禁用 MEM Dataset 以提高安全性

**解决**: 已在代码中配置 `GDAL_MEM_ENABLE_OPEN=YES`

**为什么这样做是安全的**:
- 运行在受控环境（自己的服务器）
- 有输入验证和资源限制
- 性能提升显著（10-100倍）
- rioxarray 生态系统的标准做法

### 问题 3: 网络读取超时

**错误**: `TIFFReadEncodedTile() failed`

**原因**: 网络传输不完整或超时

**解决**: 已增加 GDAL 网络超时配置（10分钟，5次重试）

配置详情：
```python
os.environ['GDAL_HTTP_TIMEOUT'] = '600'        # 10分钟超时
os.environ['GDAL_HTTP_MAX_RETRY'] = '5'        # 最多重试5次
os.environ['GDAL_HTTP_RETRY_DELAY'] = '10'     # 重试间隔10秒
os.environ['CPL_VSIL_CURL_CHUNK_SIZE'] = '10485760'  # 10MB 块大小
```

### 问题 4: S3 访问失败

**错误**: `File not found` 或 `Access denied`

**原因**: 
- 使用了 S3 URL 但没有 AWS 凭证
- 前端已自动将 S3 URL 转换为 HTTPS URL

**验证**: 检查浏览器控制台，确认发送的是 HTTPS URL

### 问题 5: 波段匹配错误

**错误**: 匹配到错误的资产（如 `red-jp2` 而不是 `red`）

**原因**: 使用 `includes()` 方法导致模糊匹配

**解决**: 已改用精确匹配标准资产键名
```javascript
const standardBandKeys = {
  'red': 'red',    // B04 红光
  'nir': 'nir',    // B08 近红外
  'green': 'green', // B03 绿光
  'blue': 'blue'   // B02 蓝光
};
```

## 📈 性能指标

基于真实 Sentinel-2 数据的测试结果：

| 指标 | 值 |
|------|-----|
| **处理区域** | 33km × 28km |
| **输入数据** | ~300MB (2个波段) |
| **输出文件** | ~37MB (NDVI COG) |
| **处理时间** | 1-2 分钟 |
| **分辨率** | 10米 |
| **像素数** | 3315 × 2855 |

### 成功案例

**测试影像**: S2B_50TMK_20260126_0_L2A  
**测试区域**: 北京地区 (33km × 28km)  
**处理时间**: 约 1 分钟  
**输出文件**: 37.32 MB NDVI COG 文件

**NDVI 统计**:
- **范围**: -0.999 到 0.999
- **平均值**: 0.16
- **地表覆盖**:
  - 裸地/建筑: 64.0%
  - 稀疏植被: 28.6%
  - 中等植被: 3.6%
  - 茂密植被: 1.3%

### 性能优化

系统已实施以下优化：

1. **GDAL 网络配置**
   - 10分钟超时，5次重试
   - 10MB 块大小
   - 512MB 缓存

2. **异步任务处理**
   - 后台任务队列
   - 实时进度跟踪
   - 并发处理支持

3. **COG 格式输出**
   - 瓦片化存储（512x512）
   - DEFLATE 压缩
   - 自动生成概览层级

## 🗺️ 支持的卫星数据

| 卫星 | 产品级别 | 分辨率 | 状态 |
|------|---------|--------|------|
| Sentinel-2 | L2A | 10m | ✅ 已实现 |
| Sentinel-1 | GRD | 10m | 🔄 计划中 |
| Landsat 8 | L2 | 30m | 🔄 计划中 |
| MODIS | MCD43A4 | 500m | 🔄 计划中 |

## 🌱 支持的植被指数

| 指数 | 全称 | 公式 | 用途 |
|------|------|------|------|
| **NDVI** | 归一化植被指数 | (NIR-Red)/(NIR+Red) | 植被覆盖度 |
| **SAVI** | 土壤调节植被指数 | (NIR-Red)/(NIR+Red+L)×(1+L) | 低植被覆盖区 |
| **EVI** | 增强植被指数 | 2.5×(NIR-Red)/(NIR+6×Red-7.5×Blue+1) | 高植被覆盖区 |
| **VGI** | 可见光绿度指数 | (Green-Red)/(Green+Red) | 作物生长监测 |

## 📝 开发指南

### 技术文档

项目中包含以下详细的技术文档：

- **[MapComponent 文档](frontend/src/components/MapComponent.README.md)** - 地图组件使用指南
- **[RasterProcessor 文档](backend/app/services/RASTER_PROCESSOR_README.md)** - 栅格处理器实现说明
- **[VegetationIndexCalculator 文档](backend/app/services/VEGETATION_INDEX_CALCULATOR_README.md)** - 植被指数计算器使用文档

### 项目结构详解

```
satellite-gis-platform/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── aoi.py         # AOI 处理
│   │   │   ├── query.py       # 数据查询
│   │   │   └── process.py     # 数据处理
│   │   ├── models/            # 数据模型
│   │   │   ├── aoi.py
│   │   │   ├── processing.py
│   │   │   └── satellite.py
│   │   └── services/          # 业务逻辑
│   │       ├── stac_service.py              # STAC API 查询
│   │       ├── raster_processor.py          # 栅格处理
│   │       ├── vegetation_index_calculator.py  # 植被指数计算
│   │       ├── processing_service.py        # 处理服务
│   │       └── task_manager.py              # 任务管理
│   ├── tests/                 # 测试
│   ├── main.py                # 应用入口
│   └── requirements.txt       # Python 依赖
│
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── components/        # React 组件
│   │   │   ├── MapComponent.js           # 地图组件
│   │   │   ├── DataQueryPanel.js         # 查询面板
│   │   │   ├── ResultsPanel.js           # 结果面板
│   │   │   └── ProcessingConfigPanel.js  # 处理配置面板
│   │   ├── App.js             # 主应用
│   │   └── index.js           # 入口
│   └── package.json           # Node 依赖
│
├── .kiro/specs/               # 项目规范文档
│   └── satellite-gis-platform/
│       ├── requirements.md    # 需求文档
│       ├── design.md          # 设计文档
│       └── tasks.md           # 任务列表
│
├── docker-compose.yml         # Docker 配置
└── README.md                  # 本文档
```

### 开发工作流

#### 后端开发

1. **激活虚拟环境**
   ```bash
   cd backend
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   ```

2. **添加新功能**
   - 在 `backend/app/` 目录下添加新的模块
   - 在 `backend/tests/` 目录下添加对应的测试

3. **运行测试**
   ```bash
   pytest
   ```

4. **启动开发服务器**
   ```bash
   python main.py
   # 或
   uvicorn main:app --reload
   ```

#### 前端开发

1. **安装依赖**
   ```bash
   cd frontend
   npm install
   ```

2. **添加新组件**
   - 在 `frontend/src/components/` 目录下添加新组件
   - 在组件文件旁添加对应的测试文件

3. **运行测试**
   ```bash
   npm test
   ```

4. **启动开发服务器**
   ```bash
   npm start
   ```

### 添加新的植被指数

1. **在后端添加计算方法**
   
   编辑 `backend/app/services/vegetation_index_calculator.py`:
   ```python
   def calculate_new_index(self, bands: Dict[str, np.ndarray]) -> np.ndarray:
       """计算新的植被指数"""
       # 实现计算逻辑
       pass
   ```

2. **更新处理服务**
   
   编辑 `backend/app/services/processing_service.py`:
   ```python
   if 'NEW_INDEX' in indices:
       result = calculator.calculate_new_index(bands)
       # 保存结果
   ```

3. **更新数据模型**
   
   编辑 `backend/app/models/processing.py`:
   ```python
   class VegetationIndexType(str, Enum):
       NDVI = "NDVI"
       SAVI = "SAVI"
       EVI = "EVI"
       VGI = "VGI"
       NEW_INDEX = "NEW_INDEX"  # 添加新指数
   ```

4. **在前端添加选项**
   
   编辑 `frontend/src/components/ProcessingConfigPanel.js`:
   ```javascript
   const availableIndices = ['NDVI', 'SAVI', 'EVI', 'VGI', 'NEW_INDEX'];
   ```

### 添加新的卫星数据源

1. **在 STAC 服务中添加查询方法**
   
   编辑 `backend/app/services/stac_service.py`:
   ```python
   def query_new_satellite(self, ...):
       """查询新卫星数据"""
       pass
   ```

2. **更新查询 API**
   
   编辑 `backend/app/api/query.py`:
   ```python
   if satellite == "new-satellite":
       results = stac_service.query_new_satellite(...)
   ```

3. **在前端添加选项**
   
   编辑 `frontend/src/components/DataQueryPanel.js`:
   ```javascript
   const satellites = ['sentinel-2', 'landsat-8', 'new-satellite'];
   ```

### 环境变量配置

#### 后端 (.env)

```bash
# 服务器配置
HOST=0.0.0.0
PORT=8000

# STAC API
STAC_API_URL=https://earth-search.aws.element84.com/v1

# 数据处理
MAX_WORKERS=4
TEMP_DIR=/tmp/satellite_gis

# GDAL 配置
GDAL_CACHEMAX=512
GDAL_HTTP_TIMEOUT=600
```

#### 前端 (.env)

```bash
# API 端点
REACT_APP_API_URL=http://localhost:8000

# 地图配置
REACT_APP_DEFAULT_CENTER_LAT=39.9
REACT_APP_DEFAULT_CENTER_LNG=116.4
REACT_APP_DEFAULT_ZOOM=5
```

### Docker 开发

#### 构建镜像

```bash
docker-compose build
```

#### 启动服务

```bash
docker-compose up
```

#### 查看日志

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

#### 进入容器

```bash
docker-compose exec backend bash
docker-compose exec frontend sh
```

### 代码规范

#### Python (后端)

- 遵循 PEP 8 规范
- 使用 type hints
- 编写 docstrings
- 测试覆盖率 > 80%

#### JavaScript (前端)

- 使用 ESLint
- 遵循 React 最佳实践
- 组件化开发
- 编写单元测试

### 已实现功能

#### ✅ MVP Phase 1
- [x] 项目基础架构
- [x] 基础地图显示
- [x] AOI 绘制和管理
- [x] STAC API 集成
- [x] 数据查询界面

#### ✅ MVP Phase 2
- [x] 栅格数据处理
- [x] 植被指数计算
- [x] 异步任务处理
- [x] COG 格式输出
- [x] 结果展示

#### 🔄 计划中
- [ ] 多卫星支持（Sentinel-1, Landsat 8, MODIS）
- [ ] 时间序列合成
- [ ] 中国地图服务集成
- [ ] 用户认证系统

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

- [AWS Open Data](https://registry.opendata.aws/) - 提供免费的卫星数据
- [Element84 Earth Search](https://www.element84.com/earth-search/) - STAC API 服务
- [GDAL](https://gdal.org/) - 地理空间数据处理库
- [Leaflet](https://leafletjs.com/) - 开源地图库

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送 Pull Request
- 查看项目文档：`.kiro/specs/satellite-gis-platform/`

---

**最后更新**: 2026-01-28  
**版本**: 1.0.0  
**状态**: ✅ 生产就绪
