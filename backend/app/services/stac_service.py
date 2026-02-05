"""
STAC API 查询服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pystac_client import Client
from pystac import Item
import logging

logger = logging.getLogger(__name__)


class STACQueryService:
    """STAC API 查询服务类"""
    
    def __init__(self, stac_url: str = "https://earth-search.aws.element84.com/v1"):
        """
        初始化 STAC 查询服务
        
        Args:
            stac_url: STAC API 端点 URL
        """
        self.stac_url = stac_url
        self.client = None
        
    def _get_client(self) -> Client:
        """获取或创建 STAC 客户端"""
        if self.client is None:
            self.client = Client.open(self.stac_url)
        return self.client
    
    def _geojson_to_bbox(self, geojson: Dict[str, Any]) -> List[float]:
        """
        将 GeoJSON 转换为 bbox
        
        Args:
            geojson: GeoJSON 几何对象
            
        Returns:
            bbox: [minx, miny, maxx, maxy]
        """
        coords = geojson["coordinates"][0]  # 获取外环坐标
        lons = [coord[0] for coord in coords]
        lats = [coord[1] for coord in coords]
        return [min(lons), min(lats), max(lons), max(lats)]
    
    def search_sentinel2(
        self,
        aoi: Dict[str, Any],
        date_range: Dict[str, datetime],
        cloud_cover_max: Optional[float] = None,
        product_level: str = "L2A"
    ) -> List[Item]:
        """
        查询 Sentinel-2 数据
        
        Args:
            aoi: GeoJSON 格式的感兴趣区域
            date_range: 时间范围，包含 'start' 和 'end' 键
            cloud_cover_max: 最大云量百分比（0-100）
            product_level: 产品级别，L1C 或 L2A
            
        Returns:
            STAC Item 列表
        """
        try:
            client = self._get_client()
            bbox = self._geojson_to_bbox(aoi)
            
            # 构建查询参数
            search_params = {
                "collections": [f"sentinel-2-{product_level.lower()}"],
                "bbox": bbox,
                "datetime": f"{date_range['start'].isoformat()}/{date_range['end'].isoformat()}",
                "max_items": 100,
            }
            
            # 添加云量过滤
            if cloud_cover_max is not None:
                search_params["query"] = {
                    "eo:cloud_cover": {
                        "lte": cloud_cover_max
                    }
                }
            
            logger.info(f"Searching Sentinel-2 {product_level} with params: {search_params}")
            
            # 执行搜索
            search = client.search(**search_params)
            items = list(search.items())
            
            logger.info(f"Found {len(items)} Sentinel-2 items")
            return items
            
        except Exception as e:
            logger.error(f"Error searching Sentinel-2 data: {str(e)}")
            raise
    
    def search_sentinel1(
        self,
        aoi: Dict[str, Any],
        date_range: Dict[str, datetime],
        product_type: str = "GRD",
        **kwargs
    ) -> List[Item]:
        """
        查询 Sentinel-1 数据
        
        Args:
            aoi: GeoJSON 格式的感兴趣区域
            date_range: 时间范围
            product_type: 产品类型，GRD 或 RTC
            **kwargs: 其他查询参数
            
        Returns:
            STAC Item 列表
        """
        try:
            client = self._get_client()
            bbox = self._geojson_to_bbox(aoi)
            
            # Sentinel-1 collection ID
            collection = "sentinel-1-grd" if product_type == "GRD" else "sentinel-1-rtc"
            
            search_params = {
                "collections": [collection],
                "bbox": bbox,
                "datetime": f"{date_range['start'].isoformat()}/{date_range['end'].isoformat()}",
                "max_items": 100,
            }
            
            logger.info(f"Searching Sentinel-1 {product_type} with params: {search_params}")
            
            search = client.search(**search_params)
            items = list(search.items())
            
            logger.info(f"Found {len(items)} Sentinel-1 items")
            return items
            
        except Exception as e:
            logger.error(f"Error searching Sentinel-1 data: {str(e)}")
            raise
    
    def search_landsat8(
        self,
        aoi: Dict[str, Any],
        date_range: Dict[str, datetime],
        cloud_cover_max: Optional[float] = None,
        product_level: str = "L2"
    ) -> List[Item]:
        """
        查询 Landsat 8 数据
        
        Args:
            aoi: GeoJSON 格式的感兴趣区域
            date_range: 时间范围
            cloud_cover_max: 最大云量百分比
            product_level: 产品级别，L1 或 L2
            
        Returns:
            STAC Item 列表
        """
        try:
            client = self._get_client()
            bbox = self._geojson_to_bbox(aoi)
            
            # Landsat collection ID
            collection = f"landsat-c2-{product_level.lower()}"
            
            search_params = {
                "collections": [collection],
                "bbox": bbox,
                "datetime": f"{date_range['start'].isoformat()}/{date_range['end'].isoformat()}",
                "max_items": 100,
            }
            
            # 添加云量过滤
            if cloud_cover_max is not None:
                search_params["query"] = {
                    "eo:cloud_cover": {
                        "lte": cloud_cover_max
                    }
                }
            
            logger.info(f"Searching Landsat 8 {product_level} with params: {search_params}")
            
            search = client.search(**search_params)
            items = list(search.items())
            
            logger.info(f"Found {len(items)} Landsat 8 items")
            return items
            
        except Exception as e:
            logger.error(f"Error searching Landsat 8 data: {str(e)}")
            raise
    
    def search_modis(
        self,
        aoi: Dict[str, Any],
        date_range: Dict[str, datetime],
        product: str = "MCD43A4"
    ) -> List[Item]:
        """
        查询 MODIS 数据
        
        Args:
            aoi: GeoJSON 格式的感兴趣区域
            date_range: 时间范围
            product: MODIS 产品名称
            
        Returns:
            STAC Item 列表
        """
        try:
            client = self._get_client()
            bbox = self._geojson_to_bbox(aoi)
            
            search_params = {
                "collections": [f"modis-{product.lower()}"],
                "bbox": bbox,
                "datetime": f"{date_range['start'].isoformat()}/{date_range['end'].isoformat()}",
                "max_items": 100,
            }
            
            logger.info(f"Searching MODIS {product} with params: {search_params}")
            
            search = client.search(**search_params)
            items = list(search.items())
            
            logger.info(f"Found {len(items)} MODIS items")
            return items
            
        except Exception as e:
            logger.error(f"Error searching MODIS data: {str(e)}")
            raise
