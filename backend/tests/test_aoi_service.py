"""
AOI 服务单元测试
"""
import pytest
import json
from app.models.aoi import GeoJSON
from app.services.aoi_service import AOIService


@pytest.fixture
def aoi_service():
    """创建 AOI 服务实例"""
    return AOIService()


@pytest.fixture
def valid_polygon():
    """有效的多边形 GeoJSON"""
    return GeoJSON(
        type="Polygon",
        coordinates=[[
            [116.3, 39.9],
            [116.4, 39.9],
            [116.4, 40.0],
            [116.3, 40.0],
            [116.3, 39.9]
        ]]
    )


@pytest.fixture
def valid_geojson_file():
    """有效的 GeoJSON 文件内容"""
    data = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0],
                [116.3, 39.9]
            ]]
        },
        "properties": {}
    }
    return json.dumps(data).encode('utf-8')


def test_validate_geometry_valid(aoi_service, valid_polygon):
    """测试验证有效几何"""
    result = aoi_service.validate_geometry(valid_polygon)
    assert result is True


def test_validate_geometry_invalid_self_intersecting(aoi_service):
    """测试验证自相交的无效几何"""
    # 创建自相交的多边形（蝴蝶结形状）
    invalid_polygon = GeoJSON(
        type="Polygon",
        coordinates=[[
            [0.0, 0.0],
            [1.0, 1.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [0.0, 0.0]
        ]]
    )
    
    with pytest.raises(ValueError, match="Invalid geometry"):
        aoi_service.validate_geometry(invalid_polygon)


def test_calculate_area_km2(aoi_service, valid_polygon):
    """测试面积计算"""
    area = aoi_service.calculate_area_km2(valid_polygon)
    
    # 验证面积为正数
    assert area > 0
    
    # 验证面积在合理范围内（约 0.1 度 x 0.1 度 ≈ 100-150 km²）
    assert 50 < area < 200


def test_calculate_centroid(aoi_service, valid_polygon):
    """测试质心计算"""
    centroid = aoi_service.calculate_centroid(valid_polygon)
    
    # 验证返回格式
    assert len(centroid) == 2
    assert isinstance(centroid[0], float)
    assert isinstance(centroid[1], float)
    
    # 验证质心在多边形范围内
    assert 116.3 <= centroid[0] <= 116.4
    assert 39.9 <= centroid[1] <= 40.0


def test_calculate_bounds(aoi_service, valid_polygon):
    """测试边界框计算"""
    bounds = aoi_service.calculate_bounds(valid_polygon)
    
    # 验证返回格式 [minx, miny, maxx, maxy]
    assert len(bounds) == 4
    assert bounds[0] == 116.3  # minx
    assert bounds[1] == 39.9   # miny
    assert bounds[2] == 116.4  # maxx
    assert bounds[3] == 40.0   # maxy


def test_parse_geojson_file_feature(aoi_service, valid_geojson_file):
    """测试解析 Feature 类型的 GeoJSON 文件"""
    result = aoi_service.parse_geojson_file(valid_geojson_file)
    
    assert result.type == "Polygon"
    assert len(result.coordinates) == 1
    assert len(result.coordinates[0]) == 5


def test_parse_geojson_file_feature_collection(aoi_service):
    """测试解析 FeatureCollection 类型的 GeoJSON 文件"""
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0.0, 0.0],
                        [1.0, 0.0],
                        [1.0, 1.0],
                        [0.0, 1.0],
                        [0.0, 0.0]
                    ]]
                }
            }
        ]
    }
    content = json.dumps(data).encode('utf-8')
    
    result = aoi_service.parse_geojson_file(content)
    assert result.type == "Polygon"


def test_parse_geojson_file_geometry_only(aoi_service):
    """测试解析纯几何对象的 GeoJSON 文件"""
    data = {
        "type": "Polygon",
        "coordinates": [[
            [0.0, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
            [0.0, 0.0]
        ]]
    }
    content = json.dumps(data).encode('utf-8')
    
    result = aoi_service.parse_geojson_file(content)
    assert result.type == "Polygon"


def test_parse_geojson_file_invalid_json(aoi_service):
    """测试解析无效 JSON"""
    invalid_content = b"not a json"
    
    with pytest.raises(ValueError, match="Invalid JSON format"):
        aoi_service.parse_geojson_file(invalid_content)


def test_parse_geojson_file_empty_feature_collection(aoi_service):
    """测试解析空的 FeatureCollection"""
    data = {
        "type": "FeatureCollection",
        "features": []
    }
    content = json.dumps(data).encode('utf-8')
    
    with pytest.raises(ValueError, match="FeatureCollection is empty"):
        aoi_service.parse_geojson_file(content)


def test_standardize_geojson(aoi_service, valid_polygon):
    """测试 GeoJSON 标准化"""
    result = aoi_service.standardize_geojson(valid_polygon)
    
    assert result.type == "Polygon"
    assert len(result.coordinates) == 1
    # 验证多边形闭合
    assert result.coordinates[0][0] == result.coordinates[0][-1]
