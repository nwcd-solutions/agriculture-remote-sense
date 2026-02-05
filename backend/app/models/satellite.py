"""
卫星数据查询相关数据模型
"""
from datetime import datetime
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from .aoi import GeoJSON, DateRange


class SatelliteQuery(BaseModel):
    """卫星数据查询请求模型"""
    satellite: Literal["sentinel-1", "sentinel-2", "landsat-8", "modis"]
    product_level: Optional[str] = None  # L1C, L2A, Collection2-L1, etc.
    date_range: DateRange
    aoi: GeoJSON
    cloud_cover_max: Optional[float] = Field(None, ge=0, le=100)
    polarization: Optional[List[str]] = None  # For Sentinel-1: VV, VH


class SatelliteImageAsset(BaseModel):
    """卫星影像资产信息"""
    href: str
    type: Optional[str] = None
    title: Optional[str] = None
    roles: Optional[List[str]] = None


class SatelliteImageResult(BaseModel):
    """卫星影像查询结果"""
    id: str
    datetime: datetime
    satellite: str
    product_level: Optional[str] = None
    cloud_cover: Optional[float] = None
    thumbnail_url: Optional[str] = None
    assets: Dict[str, SatelliteImageAsset]
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None


class SatelliteQueryResponse(BaseModel):
    """卫星数据查询响应模型"""
    results: List[SatelliteImageResult]
    count: int
