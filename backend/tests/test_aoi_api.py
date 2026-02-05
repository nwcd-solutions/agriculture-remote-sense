"""
AOI API 端点单元测试
"""
import pytest
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_validate_aoi_valid_polygon():
    """测试验证有效的多边形 AOI"""
    request_data = {
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0],
                [116.3, 39.9]
            ]]
        }
    }
    
    response = client.post("/api/aoi/validate", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["valid"] is True
    assert data["area_km2"] > 0
    assert len(data["centroid"]) == 2
    assert len(data["bounds"]) == 4


def test_validate_aoi_invalid_not_closed():
    """测试验证未闭合的多边形"""
    request_data = {
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0]
                # 缺少闭合点
            ]]
        }
    }
    
    response = client.post("/api/aoi/validate", json=request_data)
    
    # 应该在 Pydantic 验证阶段失败
    assert response.status_code == 422


def test_validate_aoi_invalid_coordinates_out_of_range():
    """测试验证坐标超出范围的多边形"""
    request_data = {
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [200.0, 39.9],  # 经度超出范围
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0],
                [200.0, 39.9]
            ]]
        }
    }
    
    response = client.post("/api/aoi/validate", json=request_data)
    
    # 应该在 Pydantic 验证阶段失败
    assert response.status_code == 422


def test_upload_aoi_valid_geojson():
    """测试上传有效的 GeoJSON 文件"""
    geojson_data = {
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
    
    files = {
        "file": ("test.geojson", json.dumps(geojson_data), "application/json")
    }
    
    response = client.post("/api/aoi/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["aoi"]["type"] == "Polygon"
    assert data["area_km2"] > 0
    assert len(data["bounds"]) == 4


def test_upload_aoi_feature_collection():
    """测试上传 FeatureCollection 类型的 GeoJSON"""
    geojson_data = {
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
    
    files = {
        "file": ("test.json", json.dumps(geojson_data), "application/json")
    }
    
    response = client.post("/api/aoi/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["aoi"]["type"] == "Polygon"


def test_upload_aoi_invalid_file_format():
    """测试上传无效文件格式"""
    files = {
        "file": ("test.txt", b"not a geojson", "text/plain")
    }
    
    response = client.post("/api/aoi/upload", files=files)
    
    assert response.status_code == 400
    assert "invalid_file_format" in response.json()["detail"]["error"]


def test_upload_aoi_empty_file():
    """测试上传空文件"""
    files = {
        "file": ("test.geojson", b"", "application/json")
    }
    
    response = client.post("/api/aoi/upload", files=files)
    
    assert response.status_code == 400


def test_upload_aoi_invalid_json():
    """测试上传无效的 JSON 文件"""
    files = {
        "file": ("test.geojson", b"not valid json", "application/json")
    }
    
    response = client.post("/api/aoi/upload", files=files)
    
    assert response.status_code == 400
