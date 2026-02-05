# 设计文档

## 概述

卫星 GIS 平台是一个基于 Web 的综合遥感数据处理应用，旨在提供类似 Google Earth Engine 的功能，但基于 AWS Open Data 的私有化部署方案。系统采用现代化的前后端分离架构，前端使用 React 构建简约现代的用户界面，后端使用 FastAPI 提供高性能的数据处理服务。

系统核心功能包括：
- 多卫星数据源统一访问（Sentinel-1/2、Landsat 8、MODIS）
- 交互式 AOI 定义和地图可视化
- 植被指数计算（NDVI、SAVI、EVI、PVI、VGI）
- 时间序列合成（旬度、月度、季度）
- 真实地图服务集成（百度、高德、天地图、OSM）
- 数据下载和批处理

## 架构

### 整体架构

系统采用三层架构设计，集成 AWS Batch 进行大规模数据处理：

```
┌─────────────────────────────────────────────────────────┐
│                    前端层 (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  地图组件    │  │  数据查询    │  │  结果展示    │  │
│  │  (Leaflet)   │  │  界面        │  │  面板        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↕ REST API
┌─────────────────────────────────────────────────────────┐
│                  API 层 (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  数据查询    │  │  AOI 处理    │  │  任务管理    │  │
│  │  端点        │  │  端点        │  │  端点        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                          ↕                               │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  Batch 提交  │  │  数据库访问  │                    │
│  │  服务        │  │  (DynamoDB)  │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│              AWS 服务层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  AWS Batch   │  │  Amazon S3   │  │  DynamoDB    │  │
│  │  (计算)      │  │  (存储)      │  │  (状态)      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  CloudWatch  │  │  SNS/SQS     │                    │
│  │  (日志)      │  │  (通知)      │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│                  处理层 (Docker 容器)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  STAC 客户端 │  │  栅格处理器  │  │  指数计算器  │  │
│  │  (pystac)    │  │  (GDAL/rio)  │  │  (xarray)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  时间合成器  │  │  坐标转换器  │                    │
│  │  (Dask)      │  │  (pyproj)    │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│              外部数据源                                  │
│  AWS Open Data (S3) + STAC API                          │
└─────────────────────────────────────────────────────────┘
```

### AWS Batch 处理流程

```
用户提交任务
    ↓
FastAPI 接收请求
    ↓
创建任务记录（数据库）
    ↓
提交任务到 AWS Batch
    ↓
返回任务 ID 给用户
    ↓
AWS Batch 启动容器
    ↓
容器执行处理逻辑
    ├─ 从 S3 读取输入数据
    ├─ 执行栅格处理
    ├─ 计算植被指数
    └─ 保存结果到 S3
    ↓
更新任务状态（数据库）
    ↓
发送完成通知（可选）
    ↓
用户查询任务状态
    ↓
用户下载结果（S3 URL）
```

### 模块化设计

系统采用模块化设计，主要模块包括：

**前端模块：**
1. **地图模块** - 地图显示、交互、图层管理
2. **数据查询模块** - 卫星数据搜索和过滤界面
3. **AOI 管理模块** - 感兴趣区域定义和编辑
4. **处理配置模块** - 植被指数、时间合成参数设置
5. **结果展示模块** - 查询结果、处理进度、下载管理
6. **代码查看模块** - 算法源代码展示

**后端模块：**
1. **API 路由模块** - FastAPI 路由定义
2. **STAC 查询模块** - 卫星数据发现和元数据检索
3. **几何处理模块** - AOI 格式转换和验证
4. **栅格处理模块** - 影像裁剪、重投影、格式转换
5. **指数计算模块** - 植被指数算法实现
6. **时间合成模块** - 多时相数据聚合
7. **任务队列模块** - 异步任务管理
8. **坐标转换模块** - 不同坐标系转换（WGS84/GCJ02/BD09）
9. **AWS Batch 集成模块** - 任务提交和状态管理
10. **数据库访问模块** - 任务状态持久化
11. **S3 存储模块** - 结果文件上传和下载

## 组件和接口

### 前端组件

#### 1. MapComponent
地图显示和交互的核心组件。

**属性：**
- `mapProvider`: 地图服务提供商（baidu/amap/tianditu/osm/mapbox）
- `center`: 地图中心坐标 [lat, lon]
- `zoom`: 缩放级别
- `layers`: 图层配置数组
- `onAOIChange`: AOI 变化回调函数

**方法：**
- `drawPolygon()`: 启动多边形绘制模式
- `loadAOI(geojson)`: 加载 GeoJSON AOI
- `clearAOI()`: 清除当前 AOI
- `switchMapProvider(provider)`: 切换地图服务
- `addLayer(layer)`: 添加图层
- `removeLayer(layerId)`: 移除图层

#### 2. DataQueryPanel
数据查询和过滤界面组件。

**属性：**
- `satellites`: 可用卫星列表
- `onQuery`: 查询提交回调函数

**方法：**
- `setSatellite(type)`: 设置卫星类型
- `setDateRange(start, end)`: 设置时间范围
- `setCloudCover(max)`: 设置云量阈值
- `submitQuery()`: 提交查询请求

#### 3. ProcessingConfigPanel
处理参数配置组件。

**属性：**
- `availableIndices`: 可用植被指数列表
- `onProcess`: 处理提交回调函数

**方法：**
- `selectIndices(indices)`: 选择要计算的指数
- `setCompositeMode(mode)`: 设置合成模式（10day/monthly/seasonal）
- `submitProcessing()`: 提交处理任务

#### 4. ResultsPanel
结果展示和下载管理组件。

**属性：**
- `results`: 查询结果数组
- `tasks`: 处理任务状态数组

**方法：**
- `displayResults(results)`: 显示查询结果
- `downloadImage(imageId)`: 下载单个影像
- `batchDownload(imageIds)`: 批量下载
- `showProgress(taskId)`: 显示任务进度

### 后端 API 接口

#### 1. 数据查询接口

**POST /api/query**

查询卫星数据。

请求体：
```json
{
  "satellite": "sentinel-2",
  "product_level": "L2A",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  },
  "aoi": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], ...]]
  },
  "cloud_cover_max": 20
}
```

响应：
```json
{
  "results": [
    {
      "id": "S2A_MSIL2A_...",
      "datetime": "2024-06-15T10:30:00Z",
      "satellite": "sentinel-2",
      "product_level": "L2A",
      "cloud_cover": 15.2,
      "thumbnail_url": "https://...",
      "assets": {...}
    }
  ],
  "count": 42
}
```

#### 2. AOI 处理接口

**POST /api/aoi/upload**

上传 Shapefile 或 GeoJSON。

请求：multipart/form-data
- `file`: Shapefile (.zip) 或 GeoJSON (.json)

响应：
```json
{
  "aoi": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], ...]]
  },
  "area_km2": 125.6,
  "bounds": [minx, miny, maxx, maxy]
}
```

**POST /api/aoi/validate**

验证 AOI 几何。

请求体：
```json
{
  "aoi": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], ...]]
  }
}
```

响应：
```json
{
  "valid": true,
  "area_km2": 125.6,
  "centroid": [lon, lat]
}
```

#### 3. 植被指数计算接口

**POST /api/process/indices**

计算植被指数（提交到 AWS Batch）。

请求体：
```json
{
  "image_id": "S2A_MSIL2A_...",
  "indices": ["NDVI", "EVI", "SAVI"],
  "aoi": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], ...]]
  },
  "band_urls": {
    "red": "https://...",
    "nir": "https://...",
    "blue": "https://..."
  },
  "output_format": "COG"
}
```

响应：
```json
{
  "task_id": "task_123456",
  "status": "queued",
  "batch_job_id": "abc-def-123",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### 4. 时间合成接口

**POST /api/process/composite**

创建时间合成。

请求体：
```json
{
  "satellite": "sentinel-2",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  },
  "aoi": {
    "type": "Polygon",
    "coordinates": [[[lon, lat], ...]]
  },
  "composite_mode": "monthly",
  "apply_cloud_mask": true,
  "indices": ["NDVI"]
}
```

响应：
```json
{
  "task_id": "task_789012",
  "status": "queued",
  "composite_periods": [
    "2024-01", "2024-02", ...
  ]
}
```

#### 5. 任务状态接口

**GET /api/process/tasks/{task_id}**

查询任务状态。

响应：
```json
{
  "task_id": "task_123456",
  "status": "completed",
  "progress": 100,
  "batch_job_id": "abc-def-123",
  "batch_job_status": "SUCCEEDED",
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:31:00Z",
  "completed_at": "2024-01-15T10:35:00Z",
  "result": {
    "output_files": [
      {
        "name": "NDVI.tif",
        "s3_url": "s3://bucket/results/task_123456/NDVI.tif",
        "download_url": "https://bucket.s3.amazonaws.com/results/task_123456/NDVI.tif",
        "size_mb": 45.2
      }
    ]
  },
  "error": null
}
```

**GET /api/process/tasks**

列出所有任务。

查询参数：
- `status`: 过滤状态（queued, running, completed, failed）
- `limit`: 返回数量限制（默认 20）
- `offset`: 分页偏移量

响应：
```json
{
  "tasks": [...],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

#### 6. 坐标转换接口

**POST /api/coordinates/transform**

转换坐标系。

请求体：
```json
{
  "coordinates": [[lon, lat], ...],
  "from_crs": "WGS84",
  "to_crs": "GCJ02"
}
```

响应：
```json
{
  "coordinates": [[lon, lat], ...],
  "crs": "GCJ02"
}
```

### 核心处理类

#### STACQueryService
STAC API 查询服务。

```python
class STACQueryService:
    def __init__(self, stac_url: str)
    def search_sentinel1(self, aoi: dict, date_range: dict, **kwargs) -> List[Item]
    def search_sentinel2(self, aoi: dict, date_range: dict, cloud_cover_max: float) -> List[Item]
    def search_landsat8(self, aoi: dict, date_range: dict, cloud_cover_max: float) -> List[Item]
    def search_modis(self, aoi: dict, date_range: dict, product: str) -> List[Item]
```

#### RasterProcessor
栅格数据处理器。

```python
class RasterProcessor:
    def clip_to_aoi(self, image_url: str, aoi: dict) -> xarray.DataArray
    def reproject(self, data: xarray.DataArray, target_crs: str) -> xarray.DataArray
    def to_cog(self, data: xarray.DataArray, output_path: str) -> str
    def apply_cloud_mask(self, data: xarray.DataArray, qa_band: xarray.DataArray) -> xarray.DataArray
```

#### VegetationIndexCalculator
植被指数计算器。

```python
class VegetationIndexCalculator:
    def calculate_ndvi(self, nir: np.ndarray, red: np.ndarray) -> np.ndarray
    def calculate_savi(self, nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray
    def calculate_evi(self, nir: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray
    def calculate_pvi(self, nir: np.ndarray, red: np.ndarray, a: float, b: float) -> np.ndarray
    def calculate_vgi(self, green: np.ndarray, red: np.ndarray) -> np.ndarray
```

#### TemporalCompositor
时间合成处理器。

```python
class TemporalCompositor:
    def composite_10day(self, images: List[xarray.DataArray], date_range: dict) -> List[xarray.DataArray]
    def composite_monthly(self, images: List[xarray.DataArray], date_range: dict) -> List[xarray.DataArray]
    def composite_seasonal(self, images: List[xarray.DataArray], date_range: dict) -> List[xarray.DataArray]
    def _aggregate_mean(self, images: List[xarray.DataArray]) -> xarray.DataArray
```

#### BatchJobManager
AWS Batch 任务管理器。

```python
class BatchJobManager:
    def __init__(self, job_queue: str, job_definition: str, s3_bucket: str)
    def submit_job(self, task_id: str, parameters: dict) -> str  # 返回 batch_job_id
    def get_job_status(self, batch_job_id: str) -> dict
    def cancel_job(self, batch_job_id: str) -> bool
    def list_jobs(self, status: str = None) -> List[dict]
```

#### TaskRepository
任务数据库访问层（DynamoDB）。

```python
class TaskRepository:
    def __init__(self, table_name: str, region: str = "us-west-2")
    def create_task(self, task: ProcessingTask) -> str  # 返回 task_id
    def get_task(self, task_id: str) -> ProcessingTask
    def update_task_status(self, task_id: str, status: str, **kwargs) -> bool
    def list_tasks(self, status: str = None, limit: int = 20, last_key: dict = None) -> Tuple[List[ProcessingTask], dict]
    def query_by_batch_job_id(self, batch_job_id: str) -> ProcessingTask
    def delete_task(self, task_id: str) -> bool
```

#### S3StorageService
S3 存储服务。

```python
class S3StorageService:
    def __init__(self, bucket_name: str, region: str = "us-west-2")
    def upload_file(self, local_path: str, s3_key: str) -> str  # 返回 S3 URL
    def download_file(self, s3_key: str, local_path: str) -> str
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str
    def delete_file(self, s3_key: str) -> bool
    def list_files(self, prefix: str) -> List[str]
```

## 数据模型

### SatelliteQuery
卫星数据查询请求模型。

```python
class SatelliteQuery(BaseModel):
    satellite: Literal["sentinel-1", "sentinel-2", "landsat-8", "modis"]
    product_level: Optional[str]  # L1C, L2A, Collection2-L1, etc.
    date_range: DateRange
    aoi: GeoJSON
    cloud_cover_max: Optional[float] = None
    polarization: Optional[List[str]] = None  # For Sentinel-1: VV, VH
```

### DateRange
时间范围模型。

```python
class DateRange(BaseModel):
    start: datetime
    end: datetime
    
    @validator('end')
    def end_after_start(cls, v, values):
        if 'start' in values and v < values['start']:
            raise ValueError('end must be after start')
        return v
```

### GeoJSON
几何对象模型。

```python
class GeoJSON(BaseModel):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: List[List[List[float]]]
    
    @validator('coordinates')
    def validate_coordinates(cls, v):
        # 验证坐标格式和闭合性
        return v
```

### ProcessingTask
处理任务模型。

```python
class ProcessingTask(BaseModel):
    task_id: str
    task_type: Literal["indices", "composite", "download"]
    status: Literal["queued", "running", "completed", "failed"]
    progress: int  # 0-100
    batch_job_id: Optional[str] = None  # AWS Batch Job ID
    batch_job_status: Optional[str] = None  # SUBMITTED, PENDING, RUNNABLE, STARTING, RUNNING, SUCCEEDED, FAILED
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parameters: dict
    result: Optional[ProcessingResult] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
```

### ProcessingResult
处理结果模型。

```python
class ProcessingResult(BaseModel):
    output_files: List[OutputFile]
    metadata: dict
    processing_time_seconds: Optional[float] = None
    
class OutputFile(BaseModel):
    name: str
    s3_key: str
    s3_url: str
    download_url: str  # Presigned URL
    size_mb: float
    index: Optional[str] = None  # NDVI, SAVI, etc.
```

### BatchJobConfig
AWS Batch 任务配置模型。

```python
class BatchJobConfig(BaseModel):
    job_queue: str
    job_definition: str
    job_name: str
    container_overrides: Optional[dict] = None
    retry_strategy: Optional[dict] = {"attempts": 3}
    timeout: Optional[dict] = {"attemptDurationSeconds": 3600}  # 1 hour
```

### VegetationIndex
植被指数配置模型。

```python
class VegetationIndex(BaseModel):
    name: Literal["NDVI", "SAVI", "EVI", "PVI", "VGI"]
    formula: str
    required_bands: List[str]
    parameters: Optional[dict] = None  # For SAVI L, PVI a/b, etc.
```

### MapProvider
地图服务提供商配置模型。

```python
class MapProvider(BaseModel):
    name: Literal["baidu", "amap", "tianditu", "osm", "mapbox"]
    api_key: Optional[str] = None
    coordinate_system: Literal["WGS84", "GCJ02", "BD09"]
    tile_url: str
    attribution: str
    max_zoom: int
    min_zoom: int
```

## 正确性属性

*属性是系统在所有有效执行中应保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 数据查询属性

**属性 1: 卫星类型过滤一致性**
*对于任何*卫星类型查询参数，返回的所有结果应该只包含该卫星类型的数据
**验证：需求 3.1**

**属性 2: 云量过滤有效性**
*对于任何*云量阈值参数，返回的所有 Sentinel-2 或 Landsat 8 影像的云量应该小于或等于该阈值
**验证：需求 3.4, 3.5**

**属性 3: 时间范围过滤正确性**
*对于任何*有效的时间范围（开始日期和结束日期），返回的所有影像的获取时间应该在该时间范围内
**验证：需求 3.3**

**属性 4: 空间交集验证**
*对于任何*AOI 和查询结果，所有返回的影像应该与 AOI 有空间交集
**验证：需求 3.8**

**属性 5: 查询结果元数据完整性**
*对于任何*查询结果，每个影像应该包含获取时间、传感器类型和产品级别字段
**验证：需求 3.7**

### AOI 处理属性

**属性 6: AOI 格式标准化**
*对于任何*有效的 AOI 输入（Shapefile、GeoJSON 或绘制的多边形），系统转换后的输出应该是标准的 GeoJSON 格式
**验证：需求 2.4**

**属性 7: GeoJSON 解析往返一致性**
*对于任何*有效的 GeoJSON AOI，解析后再序列化应该产生等价的几何对象
**验证：需求 2.3**

**属性 8: Shapefile 解析有效性**
*对于任何*包含必需组件（.shp、.shx、.dbf、.prj）的有效 Shapefile，系统应该能够成功解析并转换为 GeoJSON
**验证：需求 2.2**

### 栅格处理属性

**属性 9: AOI 裁剪边界正确性**
*对于任何*影像和 AOI，裁剪后的结果的空间范围应该完全包含在 AOI 边界内
**验证：需求 4.1**

**属性 10: 空间元数据保留**
*对于任何*处理后的栅格数据，其空间分辨率和投影信息应该与原始数据一致
**验证：需求 4.4**

**属性 11: COG 格式输出一致性**
*对于任何*下载或处理的栅格数据，输出格式应该是云优化 GeoTIFF（COG）
**验证：需求 4.3, 5.9**

### 植被指数计算属性

**属性 12: NDVI 计算公式正确性**
*对于任何*有效的 NIR 和 Red 波段数据，NDVI 计算结果应该等于 (NIR - Red) / (NIR + Red)
**验证：需求 5.2**

**属性 13: SAVI 计算公式正确性**
*对于任何*有效的 NIR 和 Red 波段数据，SAVI 计算结果应该等于 (1 + 0.5) * (NIR - Red) / (NIR + Red + 0.5)
**验证：需求 5.3**

**属性 14: EVI 计算公式正确性**
*对于任何*有效的 NIR、Red 和 Blue 波段数据，EVI 计算结果应该等于 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
**验证：需求 5.4**

**属性 15: VGI 计算公式正确性**
*对于任何*有效的 Green 和 Red 波段数据，VGI 计算结果应该等于 Green / Red
**验证：需求 5.6**

**属性 16: 波段可用性约束**
*对于任何*数据集，可用的植被指数选项应该只包含该数据集具有所需波段的指数
**验证：需求 5.7**

**属性 17: 批量指数计算完整性**
*对于任何*指定的指数列表，系统应该为每个指数生成一个输出文件
**验证：需求 5.8**

### 时间合成属性

**属性 18: 时间合成均值计算**
*对于任何*影像集合，时间合成结果的每个像素值应该等于该像素在时间维度上的均值
**验证：需求 7.2**

**属性 19: 合成前 AOI 裁剪**
*对于任何*时间合成操作，所有输入影像应该先裁剪到 AOI 范围
**验证：需求 7.4**

**属性 20: 合成周期输出数量**
*对于任何*时间范围和合成周期（10天/月度/季度），输出的合成影像数量应该等于该时间范围内的周期数量
**验证：需求 7.5**

**属性 21: 光学数据云掩膜应用**
*对于任何*光学卫星数据（Sentinel-2、Landsat 8）的时间合成，应该在合成前应用云和质量掩膜
**验证：需求 7.3**

### 坐标转换属性

**属性 22: 坐标系转换往返一致性**
*对于任何*坐标点，从坐标系 A 转换到坐标系 B，再转换回坐标系 A，应该得到原始坐标（在精度误差范围内）
**验证：需求 8.1.8**

**属性 23: 地图服务切换状态保持**
*对于任何*地图服务切换操作，地图的中心点、缩放级别和显示的图层应该在切换后保持一致
**验证：需求 8.1.6**

### 地图交互属性

**属性 24: 图层可见性控制**
*对于任何*图层的显示/隐藏操作，该图层的可见性状态应该与操作一致
**验证：需求 8.2.2**

**属性 25: 几何测量准确性**
*对于任何*在地图上绘制的几何对象，测量的距离和面积应该与基于坐标计算的理论值一致（在精度误差范围内）
**验证：需求 8.2.3**

**属性 26: 地图定位精度**
*对于任何*有效的坐标，地图定位后的中心点应该等于指定的坐标
**验证：需求 8.2.8**

### 网络状态处理属性

**属性 27: 在线地图服务优先级**
*当*网络连接可用时，系统应该使用在线地图服务而不是离线降级方案
**验证：需求 8.7**

**属性 28: 离线降级可用性**
*当*网络不可用时，系统应该提供基础的地图功能作为降级方案
**验证：需求 8.8**


## 错误处理

### 错误分类

系统错误分为以下几类：

1. **输入验证错误** - 用户输入不符合要求
2. **数据访问错误** - STAC API 或 S3 访问失败
3. **处理错误** - 栅格处理或计算失败
4. **资源错误** - 内存不足或磁盘空间不足
5. **网络错误** - 地图服务或外部 API 不可用

### 错误处理策略

#### 前端错误处理

**输入验证：**
- AOI 几何验证：检查多边形闭合性、自相交、坐标范围
- 日期范围验证：确保结束日期晚于开始日期
- 参数范围验证：云量百分比 0-100，缩放级别在有效范围内
- 文件格式验证：检查上传文件的扩展名和 MIME 类型

**用户友好的错误消息：**
```javascript
// 示例错误消息
{
  "error": "invalid_aoi",
  "message": "绘制的多边形存在自相交，请重新绘制",
  "details": {
    "intersection_point": [lon, lat]
  }
}
```

**错误恢复：**
- 自动重试：网络请求失败时自动重试 3 次，使用指数退避
- 降级处理：地图服务不可用时切换到备用服务
- 状态保存：处理失败时保存用户的查询参数和 AOI

#### 后端错误处理

**异常捕获和转换：**
```python
# 统一的错误响应格式
class APIError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code

# 错误处理中间件
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message
        }
    )
```

**数据访问错误处理：**
- STAC API 超时：设置 30 秒超时，超时后返回友好错误
- S3 访问失败：检查凭证和权限，提供具体的错误信息
- 数据不存在：返回 404 错误，建议用户调整查询参数

**处理错误处理：**
- 内存不足：使用 Dask 分块处理大型数据集
- 计算错误：捕获除零错误、无效值，记录详细日志
- 格式转换失败：验证输入数据格式，提供转换失败的具体原因

**资源管理：**
- 临时文件清理：使用上下文管理器确保临时文件被删除
- 连接池管理：限制并发连接数，避免资源耗尽
- 任务超时：长时间运行的任务设置超时限制

### 日志记录

**日志级别：**
- DEBUG：详细的调试信息（开发环境）
- INFO：关键操作记录（查询、处理任务）
- WARNING：潜在问题（重试、降级）
- ERROR：错误事件（处理失败、API 错误）
- CRITICAL：系统级错误（服务不可用）

**日志内容：**
```python
# 结构化日志示例
logger.info(
    "STAC query completed",
    extra={
        "satellite": "sentinel-2",
        "date_range": "2024-01-01 to 2024-12-31",
        "result_count": 42,
        "query_time_ms": 1250
    }
)
```

## 测试策略

### 双重测试方法

系统采用单元测试和基于属性的测试相结合的方法，以确保全面的正确性验证。

**单元测试：**
- 验证特定示例和边界情况
- 测试组件之间的集成点
- 快速反馈，易于调试

**基于属性的测试（PBT）：**
- 验证应该在所有输入上成立的通用属性
- 自动生成测试用例，发现边界情况
- 提供更强的正确性保证

两种测试方法是互补的：单元测试捕获具体的错误，属性测试验证通用的正确性。

### 单元测试

**测试框架：** pytest（Python）、Jest（JavaScript/React）

**测试覆盖范围：**

1. **API 端点测试**
   - 测试每个 REST API 端点的正常响应
   - 测试无效输入的错误处理
   - 测试认证和授权（如果适用）

2. **数据处理测试**
   - 测试 STAC 查询的特定场景
   - 测试 AOI 格式转换的已知示例
   - 测试植被指数计算的参考值

3. **前端组件测试**
   - 测试组件渲染
   - 测试用户交互（点击、输入）
   - 测试状态管理

**示例单元测试：**
```python
def test_ndvi_calculation_known_values():
    """测试 NDVI 计算的已知参考值"""
    nir = np.array([0.5, 0.6, 0.7])
    red = np.array([0.2, 0.3, 0.4])
    expected = np.array([0.4286, 0.3333, 0.2308])
    
    calculator = VegetationIndexCalculator()
    result = calculator.calculate_ndvi(nir, red)
    
    np.testing.assert_array_almost_equal(result, expected, decimal=4)

def test_aoi_upload_invalid_file():
    """测试上传无效文件的错误处理"""
    response = client.post(
        "/api/aoi/upload",
        files={"file": ("test.txt", b"invalid content", "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_file_format"
```

### 基于属性的测试

**测试框架：** Hypothesis（Python）、fast-check（JavaScript）

**配置要求：**
- 每个属性测试至少运行 100 次迭代
- 使用随机种子以确保可重现性
- 记录失败的测试用例以便调试

**测试标注：**
每个属性测试必须使用注释明确引用设计文档中的正确性属性：

```python
# **Feature: satellite-gis-platform, Property 1: 卫星类型过滤一致性**
@given(
    satellite_type=st.sampled_from(["sentinel-1", "sentinel-2", "landsat-8", "modis"]),
    aoi=st_valid_geojson(),
    date_range=st_date_range()
)
@settings(max_examples=100)
def test_satellite_type_filter_consistency(satellite_type, aoi, date_range):
    """属性测试：查询结果应该只包含指定的卫星类型"""
    query = SatelliteQuery(
        satellite=satellite_type,
        aoi=aoi,
        date_range=date_range
    )
    results = stac_service.search(query)
    
    # 验证所有结果的卫星类型与查询一致
    for item in results:
        assert item.satellite == satellite_type
```

**生成器策略：**

智能生成器应该约束输入空间以生成有效的测试数据：

```python
# 有效的 GeoJSON 多边形生成器
@st.composite
def st_valid_geojson(draw):
    # 生成有效的经纬度坐标
    lon = draw(st.floats(min_value=-180, max_value=180))
    lat = draw(st.floats(min_value=-90, max_value=90))
    
    # 生成简单的矩形多边形
    width = draw(st.floats(min_value=0.1, max_value=10))
    height = draw(st.floats(min_value=0.1, max_value=10))
    
    coords = [
        [lon, lat],
        [lon + width, lat],
        [lon + width, lat + height],
        [lon, lat + height],
        [lon, lat]  # 闭合多边形
    ]
    
    return {
        "type": "Polygon",
        "coordinates": [coords]
    }

# 有效的日期范围生成器
@st.composite
def st_date_range(draw):
    start = draw(st.datetimes(
        min_value=datetime(2015, 1, 1),
        max_value=datetime(2024, 12, 31)
    ))
    duration = draw(st.timedeltas(
        min_value=timedelta(days=1),
        max_value=timedelta(days=365)
    ))
    end = start + duration
    
    return {"start": start, "end": end}
```

**属性测试覆盖：**

每个正确性属性都应该有对应的属性测试：

- 属性 1-5：数据查询属性
- 属性 6-8：AOI 处理属性
- 属性 9-11：栅格处理属性
- 属性 12-17：植被指数计算属性
- 属性 18-21：时间合成属性
- 属性 22-23：坐标转换属性
- 属性 24-26：地图交互属性
- 属性 27-28：网络状态处理属性

### 集成测试

**端到端测试场景：**

1. **完整的数据查询和下载流程**
   - 用户绘制 AOI
   - 查询 Sentinel-2 数据
   - 下载裁剪后的影像

2. **植被指数计算流程**
   - 查询数据
   - 选择多个植被指数
   - 计算并下载结果

3. **时间合成流程**
   - 定义时间范围和 AOI
   - 选择合成周期
   - 生成月度合成影像

**测试环境：**
- 使用 Docker 容器化测试环境
- 模拟 STAC API 响应（使用 mock 服务器）
- 使用小型测试数据集以加快测试速度

### 性能测试

**负载测试：**
- 模拟多个并发用户查询
- 测试大型 AOI 的处理性能
- 测试批量下载的吞吐量

**基准测试：**
- 植被指数计算时间（不同影像大小）
- 时间合成处理时间（不同影像数量）
- API 响应时间（不同查询复杂度）

**性能目标：**
- API 响应时间 < 2 秒（95th percentile）
- 单个影像处理时间 < 30 秒（100 MB 影像）
- 时间合成处理时间 < 5 分钟（10 个影像）

## 技术栈

### 后端

- **Web 框架：** FastAPI 0.104+
- **STAC 客户端：** pystac-client 0.7+
- **栅格处理：** 
  - GDAL 3.7+
  - rasterio 1.3+
  - rioxarray 0.15+
- **数组计算：** 
  - numpy 1.24+
  - xarray 2023.1+
- **并行处理：** Dask 2023.1+
- **坐标转换：** pyproj 3.5+
- **几何处理：** shapely 2.0+, fiona 1.9+
- **HTTP 客户端：** httpx 0.25+
- **测试框架：** pytest 7.4+, hypothesis 6.92+
- **AWS SDK：** boto3 1.34+
- **数据库：** DynamoDB (使用 boto3)
- **ORM（可选）：** PynamoDB 5.5+ (DynamoDB ORM)

### 前端

- **框架：** React 18+
- **地图库：** Leaflet 1.9+ 或 MapLibre GL JS 3.0+
- **地图服务集成：**
  - react-leaflet（Leaflet 封装）
  - leaflet.chinatmsproviders（中国地图服务）
- **UI 组件：** Ant Design 5.0+ 或 Material-UI 5.0+
- **状态管理：** Zustand 4.0+ 或 Redux Toolkit 2.0+
- **HTTP 客户端：** axios 1.6+
- **文件上传：** react-dropzone 14.0+
- **图表可视化：** recharts 2.10+ 或 Apache ECharts 5.4+
- **代码高亮：** Prism.js 1.29+ 或 highlight.js 11.9+
- **测试框架：** Jest 29+, React Testing Library 14+, fast-check 3.15+

### 开发工具

- **代码格式化：** Black（Python）、Prettier（JavaScript）
- **代码检查：** Ruff（Python）、ESLint（JavaScript）
- **类型检查：** mypy（Python）、TypeScript 5.0+
- **容器化：** Docker 24+, Docker Compose 2.0+
- **API 文档：** FastAPI 自动生成的 OpenAPI/Swagger 文档

## 部署架构

### AWS CDK 基础设施即代码

系统使用 AWS CDK (Cloud Development Kit) 定义和部署所有基础设施，实现可重复、版本化的基础设施管理。

**CDK 项目结构：**

```
infrastructure/
├── bin/
│   └── satellite-gis.ts          # CDK 应用入口
├── lib/
│   ├── stacks/
│   │   ├── network-stack.ts      # VPC、子网、安全组
│   │   ├── database-stack.ts     # DynamoDB 表
│   │   ├── storage-stack.ts      # S3 存储桶
│   │   ├── batch-stack.ts        # AWS Batch 计算环境
│   │   ├── api-stack.ts          # ECS/Fargate API 服务
│   │   ├── frontend-stack.ts     # S3 + CloudFront
│   │   └── monitoring-stack.ts   # CloudWatch 仪表板和告警
│   ├── constructs/
│   │   ├── batch-job-definition.ts
│   │   └── api-service.ts
│   └── config/
│       ├── dev.ts                # 开发环境配置
│       ├── staging.ts            # 预发布环境配置
│       └── prod.ts               # 生产环境配置
├── cdk.json                      # CDK 配置
├── package.json                  # Node.js 依赖
└── tsconfig.json                 # TypeScript 配置
```

### AWS 云部署架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户层                                │
│  Web 浏览器 → AWS Amplify (CDN + 托管) → React 应用     │
└─────────────────────────────────────────────────────────┘
                          ↓ REST API
┌─────────────────────────────────────────────────────────┐
│                    API 层                                │
│  ALB → ECS/Fargate (FastAPI) → DynamoDB                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    计算层                                │
│  AWS Batch → EC2/Spot Instances (Docker 容器)           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    存储层                                │
│  S3 (结果存储) + CloudWatch (日志) + SNS (通知)         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    监控层                                │
│  CloudWatch Dashboard + Alarms + SNS Notifications      │
└─────────────────────────────────────────────────────────┘
```

**前端部署说明**：
- 使用 AWS Amplify 替代传统的 S3 + CloudFront 方案
- Amplify 提供自动构建、部署和全球 CDN 分发
- 支持分支预览和环境变量管理
- 简化的部署流程，无需手动配置 CloudFront

### CDK Stack 定义示例

#### 1. Network Stack

```typescript
// lib/stacks/network-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly batchSecurityGroup: ec2.SecurityGroup;
  public readonly apiSecurityGroup: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 创建 VPC
    this.vpc = new ec2.Vpc(this, 'SatelliteGisVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
      ],
    });

    // Batch 安全组
    this.batchSecurityGroup = new ec2.SecurityGroup(this, 'BatchSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for Batch compute environment',
      allowAllOutbound: true,
    });

    // API 安全组
    this.apiSecurityGroup = new ec2.SecurityGroup(this, 'ApiSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for API service',
      allowAllOutbound: true,
    });
  }
}
```

#### 2. Storage Stack

```typescript
// lib/stacks/storage-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export class StorageStack extends cdk.Stack {
  public readonly resultsBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 创建结果存储桶
    this.resultsBucket = new s3.Bucket(this, 'ResultsBucket', {
      bucketName: `satellite-gis-results-${this.account}`,
      versioned: false,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          id: 'DeleteOldResults',
          enabled: true,
          expiration: cdk.Duration.days(30),
          prefix: 'tasks/',
        },
        {
          id: 'DeleteTempFiles',
          enabled: true,
          expiration: cdk.Duration.days(1),
          prefix: 'temp/',
        },
      ],
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT],
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
        },
      ],
    });

    // 输出桶名称
    new cdk.CfnOutput(this, 'ResultsBucketName', {
      value: this.resultsBucket.bucketName,
      exportName: 'SatelliteGisResultsBucket',
    });
  }
}
```

#### 3. Database Stack

```typescript
// lib/stacks/database-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class DatabaseStack extends cdk.Stack {
  public readonly tasksTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 创建 DynamoDB 表
    this.tasksTable = new dynamodb.Table(this, 'ProcessingTasksTable', {
      tableName: 'ProcessingTasks',
      partitionKey: {
        name: 'task_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // 开发环境，生产环境改为 RETAIN
      pointInTimeRecovery: true,
      timeToLiveAttribute: 'ttl',
    });

    // 创建 GSI：按状态查询
    this.tasksTable.addGlobalSecondaryIndex({
      indexName: 'StatusIndex',
      partitionKey: {
        name: 'status',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // 创建 GSI：按 Batch Job ID 查询
    this.tasksTable.addGlobalSecondaryIndex({
      indexName: 'BatchJobIndex',
      partitionKey: {
        name: 'batch_job_id',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // 输出表名称
    new cdk.CfnOutput(this, 'TasksTableName', {
      value: this.tasksTable.tableName,
      exportName: 'SatelliteGisTasksTable',
    });

    new cdk.CfnOutput(this, 'TasksTableArn', {
      value: this.tasksTable.tableArn,
      exportName: 'SatelliteGisTasksTableArn',
    });
  }
}
```

#### 4. Frontend Stack (AWS Amplify)

```typescript
// lib/stacks/frontend-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as amplify from 'aws-cdk-lib/aws-amplify';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config/types';

export interface FrontendStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
  apiUrl: string;
}

export class FrontendStack extends cdk.Stack {
  public readonly amplifyApp: amplify.CfnApp;
  public readonly amplifyBranch: amplify.CfnBranch;
  public readonly websiteUrl: string;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    const { config, apiUrl } = props;

    // 创建 IAM 角色
    const amplifyRole = new iam.Role(this, 'AmplifyRole', {
      assumedBy: new iam.ServicePrincipal('amplify.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess-Amplify'),
      ],
    });

    // 创建 Amplify App
    this.amplifyApp = new amplify.CfnApp(this, 'AmplifyApp', {
      name: `satellite-gis-${config.environment}`,
      platform: 'WEB',
      iamServiceRole: amplifyRole.roleArn,
      
      // 构建配置
      buildSpec: `
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci
    build:
      commands:
        - echo "REACT_APP_API_URL=${apiUrl}" >> .env.production
        - echo "REACT_APP_ENVIRONMENT=${config.environment}" >> .env.production
        - npm run build
  artifacts:
    baseDirectory: frontend/build
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
`,
      
      // 环境变量
      environmentVariables: [
        { name: 'REACT_APP_API_URL', value: apiUrl },
        { name: 'REACT_APP_ENVIRONMENT', value: config.environment },
      ],
      
      // SPA 路由规则
      customRules: [
        {
          source: '</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|ttf|map|json)$)([^.]+$)/>',
          target: '/index.html',
          status: '200',
        },
      ],
    });

    // 创建分支
    this.amplifyBranch = new amplify.CfnBranch(this, 'AmplifyBranch', {
      appId: this.amplifyApp.attrAppId,
      branchName: config.frontend.branchName || config.environment,
      enableAutoBuild: true,
      stage: config.environment === 'prod' ? 'PRODUCTION' : 'DEVELOPMENT',
    });

    this.websiteUrl = `https://${config.frontend.branchName || config.environment}.${this.amplifyApp.attrDefaultDomain}`;

    // 输出
    new cdk.CfnOutput(this, 'AmplifyAppId', {
      value: this.amplifyApp.attrAppId,
      exportName: `SatelliteGis-AmplifyAppId-${config.environment}`,
    });

    new cdk.CfnOutput(this, 'WebsiteUrl', {
      value: this.websiteUrl,
      exportName: `SatelliteGis-WebsiteUrl-${config.environment}`,
    });
  }
}
```

**Amplify 优势**：
- 自动构建和部署
- 分支预览功能
- 环境变量管理
- 全球 CDN 分发
- 自动缓存失效
- 简化的配置

**部署方式**：
1. 通过 AWS Console 连接 GitHub/GitLab/Bitbucket 仓库
2. 或使用 Amplify CLI 手动部署

#### 5. Batch Stack

```typescript
// lib/stacks/batch-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as batch from 'aws-cdk-lib/aws-batch';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import { Construct } from 'constructs';

export interface BatchStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  securityGroup: ec2.SecurityGroup;
  resultsBucket: s3.Bucket;
  tasksTable: dynamodb.Table;
}

export class BatchStack extends cdk.Stack {
  public readonly jobQueue: batch.JobQueue;
  public readonly jobDefinition: batch.EcsJobDefinition;

  constructor(scope: Construct, id: string, props: BatchStackProps) {
    super(scope, id, props);

    // 创建 ECR 仓库
    const repository = new ecr.Repository(this, 'BatchRepository', {
      repositoryName: 'satellite-gis-batch',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // 创建 Batch 执行角色
    const jobRole = new iam.Role(this, 'BatchJobRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess'),
      ],
    });

    // 授予 S3 访问权限
    props.resultsBucket.grantReadWrite(jobRole);

    // 授予 DynamoDB 访问权限
    props.tasksTable.grantReadWriteData(jobRole);

    // 创建计算环境（使用 Spot 实例）
    const computeEnvironment = new batch.ManagedEc2EcsComputeEnvironment(
      this,
      'ComputeEnvironment',
      {
        vpc: props.vpc,
        vpcSubnets: {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        securityGroups: [props.securityGroup],
        instanceTypes: [
          ec2.InstanceType.of(ec2.InstanceClass.C5, ec2.InstanceSize.XLARGE),
          ec2.InstanceType.of(ec2.InstanceClass.C5, ec2.InstanceSize.XLARGE2),
        ],
        spot: true,
        spotBidPercentage: 70,
        minvCpus: 0,
        maxvCpus: 256,
      }
    );

    // 创建任务队列
    this.jobQueue = new batch.JobQueue(this, 'JobQueue', {
      jobQueueName: 'satellite-gis-queue',
      priority: 1,
      computeEnvironments: [
        {
          computeEnvironment,
          order: 1,
        },
      ],
    });

    // 创建任务定义
    this.jobDefinition = new batch.EcsJobDefinition(this, 'JobDefinition', {
      jobDefinitionName: 'satellite-gis-processor',
      container: new batch.EcsEc2ContainerDefinition(this, 'Container', {
        image: ecs.ContainerImage.fromEcrRepository(repository, 'latest'),
        cpu: 4,
        memory: cdk.Size.mebibytes(8192),
        jobRole,
        environment: {
          S3_BUCKET: props.resultsBucket.bucketName,
          AWS_REGION: this.region,
          DYNAMODB_TABLE: props.tasksTable.tableName,
        },
      }),
      retryAttempts: 3,
      timeout: cdk.Duration.hours(1),
    });

    // 输出
    new cdk.CfnOutput(this, 'JobQueueArn', {
      value: this.jobQueue.jobQueueArn,
      exportName: 'SatelliteGisBatchJobQueue',
    });

    new cdk.CfnOutput(this, 'JobDefinitionArn', {
      value: this.jobDefinition.jobDefinitionArn,
      exportName: 'SatelliteGisBatchJobDefinition',
    });

    new cdk.CfnOutput(this, 'RepositoryUri', {
      value: repository.repositoryUri,
      exportName: 'SatelliteGisBatchRepository',
    });
  }
}
```

#### 5. 主应用入口

```typescript
// bin/satellite-gis.ts
#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/stacks/network-stack';
import { StorageStack } from '../lib/stacks/storage-stack';
import { DatabaseStack } from '../lib/stacks/database-stack';
import { BatchStack } from '../lib/stacks/batch-stack';
import { ApiStack } from '../lib/stacks/api-stack';
import { FrontendStack } from '../lib/stacks/frontend-stack';
import { MonitoringStack } from '../lib/stacks/monitoring-stack';

const app = new cdk.App();

// 获取环境配置
const env = app.node.tryGetContext('env') || 'dev';
const config = require(`../lib/config/${env}`).default;

// 网络层
const networkStack = new NetworkStack(app, `SatelliteGis-Network-${env}`, {
  env: config.env,
  tags: config.tags,
});

// 存储层
const storageStack = new StorageStack(app, `SatelliteGis-Storage-${env}`, {
  env: config.env,
  tags: config.tags,
});

// 数据库层
const databaseStack = new DatabaseStack(app, `SatelliteGis-Database-${env}`, {
  env: config.env,
  tags: config.tags,
});

// Batch 计算层
const batchStack = new BatchStack(app, `SatelliteGis-Batch-${env}`, {
  env: config.env,
  tags: config.tags,
  vpc: networkStack.vpc,
  securityGroup: networkStack.batchSecurityGroup,
  resultsBucket: storageStack.resultsBucket,
  tasksTable: databaseStack.tasksTable,
});

// API 服务层
const apiStack = new ApiStack(app, `SatelliteGis-Api-${env}`, {
  env: config.env,
  tags: config.tags,
  vpc: networkStack.vpc,
  securityGroup: networkStack.apiSecurityGroup,
  tasksTable: databaseStack.tasksTable,
  resultsBucket: storageStack.resultsBucket,
  batchJobQueue: batchStack.jobQueue,
  batchJobDefinition: batchStack.jobDefinition,
});

// 前端层
const frontendStack = new FrontendStack(app, `SatelliteGis-Frontend-${env}`, {
  env: config.env,
  tags: config.tags,
  apiUrl: apiStack.apiUrl,
});

// 监控层
const monitoringStack = new MonitoringStack(app, `SatelliteGis-Monitoring-${env}`, {
  env: config.env,
  tags: config.tags,
  apiService: apiStack.service,
  batchJobQueue: batchStack.jobQueue,
  database: databaseStack.database,
});

app.synth();
```

### CDK 部署命令

```bash
# 安装依赖
cd infrastructure
npm install

# 引导 CDK（首次部署）
cdk bootstrap aws://ACCOUNT-ID/REGION

# 查看将要部署的资源
cdk diff --context env=dev

# 部署到开发环境
cdk deploy --all --context env=dev

# 部署到生产环境
cdk deploy --all --context env=prod

# 销毁资源
cdk destroy --all --context env=dev
```

### 环境配置示例

```typescript
// lib/config/dev.ts
export default {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-west-2',
  },
  tags: {
    Environment: 'dev',
    Project: 'satellite-gis',
  },
  database: {
    instanceType: 't3.micro',
    allocatedStorage: 20,
  },
  batch: {
    maxvCpus: 64,
    spotBidPercentage: 70,
  },
  api: {
    desiredCount: 1,
    cpu: 512,
    memory: 1024,
  },
};

// lib/config/prod.ts
export default {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-west-2',
  },
  tags: {
    Environment: 'prod',
    Project: 'satellite-gis',
  },
  database: {
    instanceType: 't3.small',
    allocatedStorage: 100,
  },
  batch: {
    maxvCpus: 256,
    spotBidPercentage: 70,
  },
  api: {
    desiredCount: 2,
    cpu: 1024,
    memory: 2048,
  },
};
```

### AWS Batch 配置

**计算环境：**
```yaml
ComputeEnvironment:
  Type: MANAGED
  State: ENABLED
  ComputeResources:
    Type: SPOT  # 使用 Spot 实例节省成本
    MinvCpus: 0
    MaxvCpus: 256
    DesiredvCpus: 0
    InstanceTypes:
      - c5.xlarge   # 4 vCPU, 8 GB RAM
      - c5.2xlarge  # 8 vCPU, 16 GB RAM
      - c5.4xlarge  # 16 vCPU, 32 GB RAM
    BidPercentage: 70  # Spot 实例出价百分比
    Subnets:
      - subnet-xxx
    SecurityGroupIds:
      - sg-xxx
    InstanceRole: arn:aws:iam::ACCOUNT:instance-profile/ecsInstanceRole
```

**任务队列：**
```yaml
JobQueue:
  Name: satellite-gis-queue
  State: ENABLED
  Priority: 1
  ComputeEnvironmentOrder:
    - Order: 1
      ComputeEnvironment: satellite-gis-compute
```

**任务定义：**
```yaml
JobDefinition:
  Name: satellite-gis-processor
  Type: container
  ContainerProperties:
    Image: ACCOUNT.dkr.ecr.REGION.amazonaws.com/satellite-gis:latest
    Vcpus: 4
    Memory: 8192
    JobRoleArn: arn:aws:iam::ACCOUNT:role/BatchJobRole
    Environment:
      - Name: S3_BUCKET
        Value: satellite-gis-results
      - Name: AWS_REGION
        Value: us-west-2
    MountPoints:
      - SourceVolume: temp
        ContainerPath: /tmp
        ReadOnly: false
    Volumes:
      - Name: temp
        Host:
          SourcePath: /tmp
  RetryStrategy:
    Attempts: 3
  Timeout:
    AttemptDurationSeconds: 3600  # 1 hour
```

### 数据库架构

**DynamoDB 表设计：**

**表名：** ProcessingTasks

**主键：**
- Partition Key: `task_id` (String)
- Sort Key: `created_at` (String, ISO 8601 格式)

**属性：**
```json
{
  "task_id": "uuid-v4",
  "created_at": "2024-01-15T10:30:00Z",
  "task_type": "indices",
  "status": "completed",
  "progress": 100,
  "batch_job_id": "abc-def-123",
  "batch_job_status": "SUCCEEDED",
  "updated_at": "2024-01-15T10:35:00Z",
  "started_at": "2024-01-15T10:31:00Z",
  "completed_at": "2024-01-15T10:35:00Z",
  "parameters": {
    "image_id": "S2A_MSIL2A_...",
    "indices": ["NDVI", "SAVI"],
    "aoi": {...}
  },
  "result": {
    "output_files": [...]
  },
  "error": null,
  "retry_count": 0,
  "max_retries": 3,
  "ttl": 1738368000
}
```

**全局二级索引（GSI）：**

1. **StatusIndex**
   - Partition Key: `status` (String)
   - Sort Key: `created_at` (String)
   - 用途：按状态查询任务列表

2. **BatchJobIndex**
   - Partition Key: `batch_job_id` (String)
   - 用途：通过 Batch Job ID 查询任务

**TTL 配置：**
- 属性：`ttl`
- 自动删除 30 天前的任务记录

**计费模式：**
- 按需计费（PAY_PER_REQUEST）
- 适合不可预测的工作负载

**备份：**
- 启用时间点恢复（Point-in-Time Recovery）
- 自动备份最近 35 天的数据

### S3 存储结构

```
s3://satellite-gis-results/
├── tasks/
│   ├── {task_id}/
│   │   ├── NDVI.tif
│   │   ├── SAVI.tif
│   │   ├── EVI.tif
│   │   └── metadata.json
│   └── ...
├── temp/
│   └── {task_id}/
│       └── intermediate_files/
└── logs/
    └── {task_id}/
        └── processing.log
```

### 容器化部署

#### Batch 处理容器

```dockerfile
# Dockerfile.batch
FROM osgeo/gdal:ubuntu-full-3.7.3

WORKDIR /app

# 安装 Python 依赖
RUN pip install --no-cache-dir \
    rasterio==1.3.9 \
    rioxarray==0.15.0 \
    numpy==1.26.4 \
    xarray==2023.1.0 \
    pystac-client==0.7.5 \
    boto3==1.34.0 \
    psycopg2-binary==2.9.9

# 复制应用代码
COPY backend/app/ /app/app/
COPY batch_processor.py /app/

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV GDAL_CACHEMAX=512
ENV GDAL_HTTP_TIMEOUT=600

# 入口脚本
CMD ["python", "batch_processor.py"]
```

#### API 服务容器

```dockerfile
# Dockerfile.api
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/ /app/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose (本地开发)

```yaml
# docker-compose.yml
version: '3.8'

services:
  dynamodb-local:
    image: amazon/dynamodb-local
    ports:
      - "8000:8000"
    command: "-jar DynamoDBLocal.jar -sharedDb -inMemory"
  
  backend:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      DYNAMODB_TABLE: ProcessingTasks
      DYNAMODB_ENDPOINT: http://dynamodb-local:8000
      AWS_REGION: us-west-2
      AWS_ACCESS_KEY_ID: dummy
      AWS_SECRET_ACCESS_KEY: dummy
      S3_BUCKET: satellite-gis-results
      BATCH_JOB_QUEUE: satellite-gis-queue
      BATCH_JOB_DEFINITION: satellite-gis-processor
    depends_on:
      - dynamodb-local
    volumes:
      - ./backend:/app
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000
    depends_on:
      - backend
  
  localstack:
    image: localstack/localstack
    ports:
      - "4566:4566"
    environment:
      SERVICES: s3,batch,ecs
      DEBUG: 1
    volumes:
      - localstack_data:/tmp/localstack

volumes:
  localstack_data:
```

### 扩展性考虑

**水平扩展：**
- 使用负载均衡器分发请求到多个后端实例
- 使用 Redis 或 Memcached 进行会话共享
- 使用消息队列（RabbitMQ、Redis）处理异步任务

**存储优化：**
- 使用对象存储（S3、MinIO）存储处理结果
- 实现结果缓存以减少重复计算
- 定期清理过期的临时文件

**性能优化：**
- 使用 CDN 加速前端资源和地图瓦片
- 实现 API 响应缓存（Redis）
- 使用数据库索引优化查询（如果使用数据库）

## 安全考虑

### 输入验证

- 验证所有用户输入（AOI、日期范围、参数）
- 限制文件上传大小（最大 50 MB）
- 防止路径遍历攻击（文件下载）

### API 安全

- 实现速率限制（每分钟最多 60 个请求）
- 使用 CORS 限制跨域访问
- 实现 API 密钥认证（如果需要）

### 数据安全

- 不存储敏感的用户数据
- 定期清理临时文件和处理结果
- 使用 HTTPS 加密传输

## 未来扩展

### 短期扩展（3-6 个月）

1. **用户账户系统**
   - 用户注册和登录
   - 保存查询历史和 AOI
   - 个性化设置

2. **更多卫星数据源**
   - Planet Labs 数据
   - 国产卫星数据（高分系列）
   - 商业卫星数据集成

3. **高级分析功能**
   - 变化检测
   - 分类和分割
   - 时间序列分析

### 长期扩展（6-12 个月）

1. **机器学习集成**
   - 预训练模型库
   - 自定义模型训练
   - GPU 加速处理

2. **协作功能**
   - 多用户协作
   - 项目共享
   - 评论和标注

3. **移动应用**
   - iOS 和 Android 应用
   - 离线数据访问
   - 现场数据采集
