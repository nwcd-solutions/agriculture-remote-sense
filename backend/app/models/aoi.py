"""
AOI (Area of Interest) 数据模型
"""
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class DateRange(BaseModel):
    """时间范围模型"""
    start: datetime
    end: datetime
    
    @field_validator('end')
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """验证结束日期必须晚于开始日期"""
        if 'start' in info.data and v < info.data['start']:
            raise ValueError('end must be after start')
        return v


class GeoJSON(BaseModel):
    """GeoJSON 几何对象模型"""
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: List[List[List[float]]]
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: List[List[List[float]]]) -> List[List[List[float]]]:
        """验证坐标格式和闭合性"""
        if not v:
            raise ValueError('coordinates cannot be empty')
        
        # 验证 Polygon 的坐标结构
        for ring in v:
            if not ring:
                raise ValueError('coordinate ring cannot be empty')
            # 检查环中的点数（至少4个点：3个顶点 + 1个闭合点）
            if len(ring) < 4:
                raise ValueError('polygon must have at least 4 points (3 vertices + closing point)')
            
            # 验证坐标格式 [lon, lat]
            for coord in ring:
                if len(coord) < 2:
                    raise ValueError('coordinate must have at least [lon, lat]')
                lon, lat = coord[0], coord[1]
                if not (-180 <= lon <= 180):
                    raise ValueError(f'longitude {lon} out of range [-180, 180]')
                if not (-90 <= lat <= 90):
                    raise ValueError(f'latitude {lat} out of range [-90, 90]')
            
            # 验证多边形闭合性（首尾坐标相同）
            if ring[0] != ring[-1]:
                raise ValueError('polygon must be closed (first and last coordinates must be the same)')
        
        return v


class AOIValidateRequest(BaseModel):
    """AOI 验证请求模型"""
    aoi: GeoJSON


class AOIValidateResponse(BaseModel):
    """AOI 验证响应模型"""
    valid: bool
    area_km2: float
    centroid: List[float]
    bounds: Optional[List[float]] = None


class AOIUploadResponse(BaseModel):
    """AOI 上传响应模型"""
    aoi: GeoJSON
    area_km2: float
    bounds: List[float]
