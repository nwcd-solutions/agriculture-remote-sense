"""
处理任务相关数据模型
"""
from datetime import datetime
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from .aoi import GeoJSON


class VegetationIndex(BaseModel):
    """植被指数配置模型"""
    name: Literal["NDVI", "SAVI", "EVI", "VGI"]
    formula: str
    required_bands: List[str]
    parameters: Optional[Dict[str, Any]] = None  # For SAVI L, etc.


class ProcessingResult(BaseModel):
    """处理结果模型"""
    output_files: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class ProcessingTask(BaseModel):
    """处理任务模型"""
    task_id: str
    task_type: Literal["indices", "composite", "download"]
    status: Literal["queued", "running", "completed", "failed"]
    progress: int = Field(0, ge=0, le=100)  # 0-100
    batch_job_id: Optional[str] = None  # AWS Batch Job ID
    batch_job_status: Optional[str] = None  # SUBMITTED, PENDING, RUNNABLE, STARTING, RUNNING, SUCCEEDED, FAILED
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parameters: Dict[str, Any]
    result: Optional[ProcessingResult] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class IndicesProcessingRequest(BaseModel):
    """植被指数计算请求模型"""
    image_id: str
    indices: List[Literal["NDVI", "SAVI", "EVI", "VGI"]]
    aoi: GeoJSON
    output_format: Literal["COG"] = "COG"
    band_urls: Dict[str, str]  # 波段名称到 URL 的映射，如 {"red": "url", "nir": "url"}


class IndicesProcessingResponse(BaseModel):
    """植被指数计算响应模型"""
    task_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    batch_job_id: Optional[str] = None  # AWS Batch Job ID
    created_at: datetime
    estimated_time: Optional[int] = None  # 预计处理时间（秒）


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    tasks: List[ProcessingTask]
    total: int
    limit: int
    offset: Optional[str] = None
    next_offset: Optional[str] = None  # 下一页的偏移键

