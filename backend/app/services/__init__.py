"""
业务逻辑服务包
"""

# 核心服务 - Lambda需要（直接导出，不在模块级导入）
# 这些会在需要时通过延迟导入加载

# 延迟导入函数
def get_batch_manager():
    """延迟导入Batch管理器"""
    from .batch_job_manager import BatchJobManager
    return BatchJobManager

def get_s3_service():
    """延迟导入S3服务"""
    from .s3_storage_service import S3StorageService
    return S3StorageService

def get_task_repository():
    """延迟导入任务仓库"""
    from .task_repository import (
        TaskRepository,
        TaskRepositoryError,
        TaskNotFoundError,
        DatabaseConnectionError
    )
    return TaskRepository, TaskRepositoryError, TaskNotFoundError, DatabaseConnectionError

def get_stac_service():
    """延迟导入STAC服务"""
    from .stac_service import STACQueryService
    return STACQueryService

def get_task_manager():
    """延迟导入任务管理器"""
    from .task_manager import TaskManager, task_manager
    return TaskManager, task_manager

def get_aoi_service():
    """延迟导入AOI服务"""
    from .aoi_service import AOIService
    return AOIService

def get_raster_processor():
    """延迟导入栅格处理器"""
    from .raster_processor import RasterProcessor
    return RasterProcessor

def get_vegetation_calculator():
    """延迟导入植被指数计算器"""
    from .vegetation_index_calculator import VegetationIndexCalculator
    return VegetationIndexCalculator

def get_processing_service():
    """延迟导入处理服务"""
    from .processing_service import ProcessingService
    return ProcessingService

def get_cleanup_service():
    """延迟导入清理服务"""
    from .cleanup_service import CleanupService, CleanupResult
    return CleanupService, CleanupResult

def get_temporal_compositor():
    """延迟导入时间合成处理器"""
    from .temporal_compositor import TemporalCompositor
    return TemporalCompositor

__all__ = [
    "get_batch_manager",
    "get_s3_service",
    "get_task_repository",
    "get_stac_service",
    "get_task_manager",
    "get_aoi_service",
    "get_raster_processor",
    "get_vegetation_calculator",
    "get_processing_service",
    "get_cleanup_service",
    "get_temporal_compositor",
]
