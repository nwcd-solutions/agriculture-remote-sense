"""
卫星数据查询 API 端点
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

from app.models import (
    SatelliteQuery,
    SatelliteQueryResponse,
    SatelliteImageResult,
    SatelliteImageAsset
)
from app.services.stac_service import STACQueryService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/query",
    tags=["query"]
)

# 创建 STAC 查询服务实例
stac_service = STACQueryService()


def _item_to_result(item: Any, satellite: str) -> SatelliteImageResult:
    """
    将 STAC Item 转换为 SatelliteImageResult
    
    Args:
        item: STAC Item 对象
        satellite: 卫星类型
        
    Returns:
        SatelliteImageResult 对象
    """
    # 提取云量信息
    cloud_cover = None
    if hasattr(item, 'properties'):
        cloud_cover = item.properties.get('eo:cloud_cover')
    
    # 提取缩略图 URL
    thumbnail_url = None
    if hasattr(item, 'assets') and 'thumbnail' in item.assets:
        thumbnail_url = item.assets['thumbnail'].href
    
    # 转换资产信息
    assets = {}
    if hasattr(item, 'assets'):
        for key, asset in item.assets.items():
            # 安全地获取属性，如果不存在则返回 None
            media_type = getattr(asset, 'media_type', None) if hasattr(asset, 'media_type') else None
            title = getattr(asset, 'title', None) if hasattr(asset, 'title') else None
            roles = getattr(asset, 'roles', None) if hasattr(asset, 'roles') else None
            
            assets[key] = SatelliteImageAsset(
                href=asset.href,
                type=media_type,
                title=title,
                roles=roles
            )
    
    # 提取产品级别
    product_level = None
    if hasattr(item, 'properties'):
        # Sentinel-2: s2:product_type or processing:level
        product_level = (
            item.properties.get('s2:product_type') or
            item.properties.get('processing:level') or
            item.properties.get('landsat:collection_category')
        )
    
    return SatelliteImageResult(
        id=item.id,
        datetime=item.datetime,
        satellite=satellite,
        product_level=product_level,
        cloud_cover=cloud_cover,
        thumbnail_url=thumbnail_url,
        assets=assets,
        geometry=item.geometry if hasattr(item, 'geometry') else None,
        bbox=item.bbox if hasattr(item, 'bbox') else None
    )


@router.post("", response_model=SatelliteQueryResponse)
async def query_satellite_data(query: SatelliteQuery) -> SatelliteQueryResponse:
    """
    查询卫星数据
    
    根据卫星类型、时间范围、AOI 和其他过滤条件查询卫星影像数据。
    
    Args:
        query: 卫星数据查询请求
        
    Returns:
        查询结果，包含影像列表和元数据
        
    Raises:
        HTTPException: 查询失败时抛出
    """
    try:
        logger.info(f"Received query for {query.satellite}")
        
        # 将 Pydantic 模型转换为字典
        aoi_dict = query.aoi.model_dump()
        date_range_dict = {
            'start': query.date_range.start,
            'end': query.date_range.end
        }
        
        # 根据卫星类型调用相应的查询方法
        items = []
        
        if query.satellite == "sentinel-2":
            product_level = query.product_level or "L2A"
            items = stac_service.search_sentinel2(
                aoi=aoi_dict,
                date_range=date_range_dict,
                cloud_cover_max=query.cloud_cover_max,
                product_level=product_level
            )
            
        elif query.satellite == "sentinel-1":
            product_type = query.product_level or "GRD"
            items = stac_service.search_sentinel1(
                aoi=aoi_dict,
                date_range=date_range_dict,
                product_type=product_type,
                polarization=query.polarization
            )
            
        elif query.satellite == "landsat-8":
            product_level = query.product_level or "L2"
            items = stac_service.search_landsat8(
                aoi=aoi_dict,
                date_range=date_range_dict,
                cloud_cover_max=query.cloud_cover_max,
                product_level=product_level
            )
            
        elif query.satellite == "modis":
            product = query.product_level or "MCD43A4"
            items = stac_service.search_modis(
                aoi=aoi_dict,
                date_range=date_range_dict,
                product=product
            )
        
        # 转换结果
        results = [_item_to_result(item, query.satellite) for item in items]
        
        logger.info(f"Query completed: found {len(results)} items")
        
        return SatelliteQueryResponse(
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        logger.error(f"Error querying satellite data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query satellite data: {str(e)}"
        )
