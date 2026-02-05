"""
数据模型包
"""
from .aoi import (
    DateRange,
    GeoJSON,
    AOIValidateRequest,
    AOIValidateResponse,
    AOIUploadResponse
)
from .satellite import (
    SatelliteQuery,
    SatelliteImageAsset,
    SatelliteImageResult,
    SatelliteQueryResponse
)
from .processing import (
    VegetationIndex,
    ProcessingResult,
    ProcessingTask,
    IndicesProcessingRequest,
    IndicesProcessingResponse
)

__all__ = [
    "DateRange",
    "GeoJSON",
    "AOIValidateRequest",
    "AOIValidateResponse",
    "AOIUploadResponse",
    "SatelliteQuery",
    "SatelliteImageAsset",
    "SatelliteImageResult",
    "SatelliteQueryResponse",
    "VegetationIndex",
    "ProcessingResult",
    "ProcessingTask",
    "IndicesProcessingRequest",
    "IndicesProcessingResponse",
]
