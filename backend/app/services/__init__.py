"""
业务逻辑服务包
"""

# 核心服务 - Lambda需要
from .batch_job_manager import BatchJobManager
from .s3_storage_service import S3StorageService
from .task_repository import (
    TaskRepository,
    TaskRepositoryError,
    TaskNotFoundError,
    DatabaseConnectionError
)

# 可选服务 - 仅在需要时导入
def get_stac_service():
    """延迟导入STAC服务"""
    from .stac_service import STACQueryService
    return STACQueryService

def get_task_manager():
    """延迟导入任务管理器"""
    from .task_manager import TaskManager, task_manager
    return TaskManager, task_manager

# 尝试导入需要geospatial依赖的模块
try:
    from .aoi_service import AOIService
    from .raster_processor import RasterProcessor
    from .vegetation_index_calculator import VegetationIndexCalculator
    from .processing_service import ProcessingService
    GEOSPATIAL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Geospatial dependencies not available: {e}")
    print("AOIService, RasterProcessor, VegetationIndexCalculator, and ProcessingService will not be available.")
    AOIService = None
    RasterProcessor = None
    VegetationIndexCalculator = None
    ProcessingService = None
    GEOSPATIAL_AVAILABLE = False

__all__ = [
    "AOIService",
    "get_stac_service",
    "RasterProcessor",
    "VegetationIndexCalculator",
    "get_task_manager",
    "ProcessingService",
    "BatchJobManager",
    "S3StorageService",
    "TaskRepository",
    "TaskRepositoryError",
    "TaskNotFoundError",
    "DatabaseConnectionError",
    "GEOSPATIAL_AVAILABLE",
]
