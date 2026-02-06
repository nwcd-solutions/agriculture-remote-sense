"""
STAC API 查询服务

支持多卫星数据源查询：
- Sentinel-1: GRD, RTC 产品 (VV/VH 极化)
- Sentinel-2: L1C, L2A 处理级别
- Landsat 8: Collection 2 Level-1, Level-2
- MODIS: Terra/Aqua 反射率及植被产品
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pystac_client import Client
from pystac import Item
import logging

logger = logging.getLogger(__name__)

# Sentinel-1 collection 映射
SENTINEL1_COLLECTIONS = {
    "GRD": "sentinel-1-grd",
    "RTC": "sentinel-1-rtc",
}

# Sentinel-2 collection 映射
SENTINEL2_COLLECTIONS = {
    "L1C": "sentinel-2-l1c",
    "L2A": "sentinel-2-l2a",
}

# Landsat 8 Collection 2 映射
LANDSAT8_COLLECTIONS = {
    "L1": "landsat-c2-l1",
    "L2": "landsat-c2-l2",
}

# MODIS 产品映射 (Terra 和 Aqua)
MODIS_COLLECTIONS = {
    # Terra 反射率
    "MOD09A1": "modis-mod09a1",
    # Aqua 反射率
    "MYD09A1": "modis-myd09a1",
    # Combined 反射率 (BRDF)
    "MCD43A4": "modis-mcd43a4",
    # Terra 植被指数
    "MOD13A1": "modis-mod13a1",
    # Aqua 植被指数
    "MYD13A1": "modis-myd13a1",
    # Terra 地表温度
    "MOD11A1": "modis-mod11a1",
    # Aqua 地表温度
    "MYD11A1": "modis-myd11a1",
}


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
            
            collection = SENTINEL2_COLLECTIONS.get(
                product_level.upper(), f"sentinel-2-{product_level.lower()}"
            )
            
            search_params = {
                "collections": [collection],
                "bbox": bbox,
                "datetime": f"{date_range['start'].isoformat()}/{date_range['end'].isoformat()}",
                "max_items": 100,
            }
            
            if cloud_cover_max is not None:
                search_params["query"] = {
                    "eo:cloud_cover": {"lte": cloud_cover_max}
                }
            
            logger.info(f"Searching Sentinel-2 {product_level} with params: {search_params}")
            
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
        polarization: Optional[List[str]] = None,
        **kwargs
    ) -> List[Item]:
        """
        查询 Sentinel-1 数据，支持 GRD 和 RTC 产品，VV/VH 极化
        
        Args:
            aoi: GeoJSON 格式的感兴趣区域
            date_range: 时间范围
            product_type: 产品类型，GRD 或 RTC
            polarization: 极化方式列表，如 ["VV", "VH"]
            **kwargs: 其他查询参数
            
        Returns:
            STAC Item 列表
        """
        try:
            client = self._get_client()
            bbox = self._geojson_to_bbox(aoi)
            
            collection = SENTINEL1_COLLECTIONS.get(
                product_type.upper(), "sentinel-1-grd"
            )
            
            search_params = {
                "collections": [collection],
                "bbox": bbox,
                "datetime": f"{date_range['start'].isoformat()}/{date_range['end'].isoformat()}",
                "max_items": 100,
            }
            
            # 添加极化过滤 (通过 sar:polarizations 属性)
            if polarization:
                search_params["query"] = {
                    "sar:polarizations": {"eq": polarization}
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
        查询 Landsat 8 Collection 2 数据，支持 Level-1 和 Level-2
        
        Args:
            aoi: GeoJSON 格式的感兴趣区域
            date_range: 时间范围
            cloud_cover_max: 最大云量百分比 (CLOUD_COVER 字段)
            product_level: 产品级别，L1 或 L2
            
        Returns:
            STAC Item 列表
        """
        try:
            client = self._get_client()
            bbox = self._geojson_to_bbox(aoi)
            
            collection = LANDSAT8_COLLECTIONS.get(
                product_level.upper(), f"landsat-c2-{product_level.lower()}"
            )
            
            search_params = {
                "collections": [collection],
                "bbox": bbox,
                "datetime": f"{date_range['start'].isoformat()}/{date_range['end'].isoformat()}",
                "max_items": 100,
            }
            
            if cloud_cover_max is not None:
                search_params["query"] = {
                    "eo:cloud_cover": {"lte": cloud_cover_max}
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
        查询 MODIS 数据，支持 Terra 和 Aqua 产品
        
        支持的产品:
        - MOD09A1: Terra 反射率 (8天合成)
        - MYD09A1: Aqua 反射率 (8天合成)
        - MCD43A4: Combined BRDF 反射率
        - MOD13A1: Terra 植被指数 (16天)
        - MYD13A1: Aqua 植被指数 (16天)
        - MOD11A1: Terra 地表温度
        - MYD11A1: Aqua 地表温度
        
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
            
            collection = MODIS_COLLECTIONS.get(
                product.upper(), f"modis-{product.lower()}"
            )
            
            search_params = {
                "collections": [collection],
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
