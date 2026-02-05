"""
业务逻辑服务包
"""
from .aoi_service import AOIService
from .stac_service import STACQueryService
from .task_manager import TaskManager, task_manager
from .batch_job_manager import BatchJobManager
from .s3_storage_service import S3StorageService
from .task_repository import (
    TaskRepository,
    TaskRepositoryError,
    TaskNotFoundError,
    DatabaseConnectionError
)

# 尝试导入需要geospatial依赖的模块
try:
    from .raster_processor import RasterProcessor
    from .vegetation_index_calculator import VegetationIndexCalculator
    from .processing_service import ProcessingService
    GEOSPATIAL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Geospatial dependencies not available: {e}")
    print("RasterProcessor, VegetationIndexCalculator, and ProcessingService will not be available.")
    RasterProcessor = None
    VegetationIndexCalculator = None
    ProcessingService = None
    GEOSPATIAL_AVAILABLE = False

__all__ = [
    "AOIService",
    "STACQueryService",
    "RasterProcessor",
    "VegetationIndexCalculator",
    "TaskManager",
    "task_manager",
    "ProcessingService",
    "BatchJobManager",
    "S3StorageService",
    "TaskRepository",
    "TaskRepositoryError",
    "TaskNotFoundError",
    "DatabaseConnectionError",
    "GEOSPATIAL_AVAILABLE",
]
