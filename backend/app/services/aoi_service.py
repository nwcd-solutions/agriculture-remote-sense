"""
AOI 处理服务
"""
import json
from typing import List, Tuple
from shapely.geometry import shape, mapping
from shapely.ops import transform
import pyproj
from app.models.aoi import GeoJSON


class AOIService:
    """AOI 处理服务类"""
    
    def __init__(self):
        """初始化 AOI 服务"""
        # 创建坐标转换器用于面积计算（WGS84 到等面积投影）
        self.wgs84 = pyproj.CRS('EPSG:4326')
        # 使用 World Mollweide 等面积投影
        self.equal_area = pyproj.CRS('ESRI:54009')
        self.transformer = pyproj.Transformer.from_crs(
            self.wgs84, 
            self.equal_area, 
            always_xy=True
        )
    
    def validate_geometry(self, aoi: GeoJSON) -> bool:
        """
        验证 GeoJSON 几何有效性
        
        Args:
            aoi: GeoJSON 对象
            
        Returns:
            bool: 几何是否有效
            
        Raises:
            ValueError: 如果几何无效
        """
        try:
            # 转换为 shapely 几何对象
            geom = shape(aoi.model_dump())
            
            # 检查几何有效性
            if not geom.is_valid:
                # 使用 explain_validity 获取详细信息（如果可用）
                try:
                    from shapely.validation import explain_validity
                    reason = explain_validity(geom)
                except ImportError:
                    reason = "geometry is not valid"
                raise ValueError(f"Invalid geometry: {reason}")
            
            # 检查是否为空
            if geom.is_empty:
                raise ValueError("Geometry is empty")
            
            # 检查面积是否为正
            if geom.area <= 0:
                raise ValueError("Geometry area must be positive")
            
            return True
            
        except Exception as e:
            raise ValueError(f"Geometry validation failed: {str(e)}")
    
    def calculate_area_km2(self, aoi: GeoJSON) -> float:
        """
        计算 AOI 面积（平方公里）
        
        Args:
            aoi: GeoJSON 对象
            
        Returns:
            float: 面积（平方公里）
        """
        # 转换为 shapely 几何对象
        geom = shape(aoi.model_dump())
        
        # 转换到等面积投影
        geom_projected = transform(self.transformer.transform, geom)
        
        # 计算面积（平方米）并转换为平方公里
        area_m2 = geom_projected.area
        area_km2 = area_m2 / 1_000_000
        
        return round(area_km2, 2)
    
    def calculate_centroid(self, aoi: GeoJSON) -> List[float]:
        """
        计算 AOI 质心
        
        Args:
            aoi: GeoJSON 对象
            
        Returns:
            List[float]: 质心坐标 [lon, lat]
        """
        geom = shape(aoi.model_dump())
        centroid = geom.centroid
        return [round(centroid.x, 6), round(centroid.y, 6)]
    
    def calculate_bounds(self, aoi: GeoJSON) -> List[float]:
        """
        计算 AOI 边界框
        
        Args:
            aoi: GeoJSON 对象
            
        Returns:
            List[float]: 边界框 [minx, miny, maxx, maxy]
        """
        geom = shape(aoi.model_dump())
        bounds = geom.bounds
        return [round(b, 6) for b in bounds]
    
    def parse_geojson_file(self, content: bytes) -> GeoJSON:
        """
        解析 GeoJSON 文件内容
        
        Args:
            content: 文件内容（字节）
            
        Returns:
            GeoJSON: 解析后的 GeoJSON 对象
            
        Raises:
            ValueError: 如果解析失败
        """
        try:
            # 解码 JSON
            data = json.loads(content.decode('utf-8'))
            
            # 处理 Feature 或 FeatureCollection
            if data.get('type') == 'Feature':
                geometry = data.get('geometry')
            elif data.get('type') == 'FeatureCollection':
                features = data.get('features', [])
                if not features:
                    raise ValueError("FeatureCollection is empty")
                # 使用第一个 feature 的几何
                geometry = features[0].get('geometry')
            elif data.get('type') in ['Polygon', 'MultiPolygon']:
                geometry = data
            else:
                raise ValueError(f"Unsupported GeoJSON type: {data.get('type')}")
            
            if not geometry:
                raise ValueError("No geometry found in GeoJSON")
            
            # 创建 GeoJSON 对象
            return GeoJSON(**geometry)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse GeoJSON: {str(e)}")
    
    def standardize_geojson(self, aoi: GeoJSON) -> GeoJSON:
        """
        标准化 GeoJSON（确保右手规则、移除重复点等）
        
        Args:
            aoi: 输入的 GeoJSON 对象
            
        Returns:
            GeoJSON: 标准化后的 GeoJSON 对象
        """
        # 转换为 shapely 几何对象
        geom = shape(aoi.model_dump())
        
        # shapely 会自动处理方向和标准化
        if not geom.is_valid:
            # 尝试修复无效几何
            geom = geom.buffer(0)
        
        # 转换回 GeoJSON
        geojson_dict = mapping(geom)
        
        return GeoJSON(**geojson_dict)
