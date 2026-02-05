"""
卫星数据查询 API 端点测试
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from main import app


client = TestClient(app)


@pytest.fixture
def valid_query_payload():
    """有效的查询请求负载"""
    return {
        "satellite": "sentinel-2",
        "product_level": "L2A",
        "date_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        },
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0],
                [116.3, 39.9]
            ]]
        },
        "cloud_cover_max": 20.0
    }


@pytest.fixture
def mock_stac_item():
    """模拟 STAC Item"""
    item = Mock()
    item.id = "S2A_MSIL2A_20240115T023541_N0510_R089_T50TLK_20240115T045807"
    item.datetime = datetime(2024, 1, 15, 2, 35, 41)
    item.properties = {
        "eo:cloud_cover": 15.2,
        "s2:product_type": "S2MSI2A"
    }
    item.geometry = {
        "type": "Polygon",
        "coordinates": [[
            [116.3, 39.9],
            [116.4, 39.9],
            [116.4, 40.0],
            [116.3, 40.0],
            [116.3, 39.9]
        ]]
    }
    item.bbox = [116.3, 39.9, 116.4, 40.0]
    
    # 模拟资产 - 使用 spec 来避免返回 Mock 对象
    thumbnail_asset = Mock(spec=['href'])
    thumbnail_asset.href = "https://example.com/thumbnail.jpg"
    
    visual_asset = Mock(spec=['href', 'media_type', 'title', 'roles'])
    visual_asset.href = "https://example.com/visual.tif"
    visual_asset.media_type = "image/tiff"
    visual_asset.title = "True color image"
    visual_asset.roles = ["visual"]
    
    item.assets = {
        "thumbnail": thumbnail_asset,
        "visual": visual_asset
    }
    
    return item


@patch('app.api.query.stac_service.search_sentinel2')
def test_query_sentinel2_success(mock_search, valid_query_payload, mock_stac_item):
    """测试成功的 Sentinel-2 查询"""
    mock_search.return_value = [mock_stac_item]
    
    response = client.post("/api/query", json=valid_query_payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] == 1
    assert len(data["results"]) == 1
    
    result = data["results"][0]
    assert result["id"] == mock_stac_item.id
    assert result["satellite"] == "sentinel-2"
    assert result["cloud_cover"] == 15.2
    assert "assets" in result


@patch('app.api.query.stac_service.search_sentinel1')
def test_query_sentinel1(mock_search, mock_stac_item):
    """测试 Sentinel-1 查询"""
    mock_search.return_value = [mock_stac_item]
    
    payload = {
        "satellite": "sentinel-1",
        "product_level": "GRD",
        "date_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        },
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
    
    response = client.post("/api/query", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1


@patch('app.api.query.stac_service.search_landsat8')
def test_query_landsat8(mock_search, mock_stac_item):
    """测试 Landsat 8 查询"""
    mock_search.return_value = [mock_stac_item]
    
    payload = {
        "satellite": "landsat-8",
        "product_level": "L2",
        "date_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        },
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0],
                [116.3, 39.9]
            ]]
        },
        "cloud_cover_max": 30.0
    }
    
    response = client.post("/api/query", json=payload)
    
    assert response.status_code == 200


@patch('app.api.query.stac_service.search_modis')
def test_query_modis(mock_search, mock_stac_item):
    """测试 MODIS 查询"""
    mock_search.return_value = [mock_stac_item]
    
    payload = {
        "satellite": "modis",
        "product_level": "MCD43A4",
        "date_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        },
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
    
    response = client.post("/api/query", json=payload)
    
    assert response.status_code == 200


def test_query_invalid_aoi():
    """测试无效的 AOI"""
    payload = {
        "satellite": "sentinel-2",
        "date_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        },
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0]
                # 缺少闭合点
            ]]
        }
    }
    
    response = client.post("/api/query", json=payload)
    
    assert response.status_code == 422  # Validation error


def test_query_invalid_date_range():
    """测试无效的时间范围（结束日期早于开始日期）"""
    payload = {
        "satellite": "sentinel-2",
        "date_range": {
            "start": "2024-01-31T00:00:00",
            "end": "2024-01-01T23:59:59"  # 结束早于开始
        },
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
    
    response = client.post("/api/query", json=payload)
    
    assert response.status_code == 422


def test_query_invalid_cloud_cover():
    """测试无效的云量值"""
    payload = {
        "satellite": "sentinel-2",
        "date_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        },
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0],
                [116.3, 39.9]
            ]]
        },
        "cloud_cover_max": 150.0  # 超出范围
    }
    
    response = client.post("/api/query", json=payload)
    
    assert response.status_code == 422


@patch('app.api.query.stac_service.search_sentinel2')
def test_query_empty_results(mock_search, valid_query_payload):
    """测试空结果"""
    mock_search.return_value = []
    
    response = client.post("/api/query", json=valid_query_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert len(data["results"]) == 0


@patch('app.api.query.stac_service.search_sentinel2')
def test_query_service_error(mock_search, valid_query_payload):
    """测试服务错误处理"""
    mock_search.side_effect = Exception("STAC API connection failed")
    
    response = client.post("/api/query", json=valid_query_payload)
    
    assert response.status_code == 500
    assert "Failed to query satellite data" in response.json()["detail"]


@patch('app.api.query.stac_service.search_sentinel2')
def test_query_default_product_level(mock_search, mock_stac_item):
    """测试默认产品级别"""
    mock_search.return_value = [mock_stac_item]
    
    payload = {
        "satellite": "sentinel-2",
        # 不指定 product_level
        "date_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:59"
        },
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
    
    response = client.post("/api/query", json=payload)
    
    assert response.status_code == 200
    # 验证使用了默认的 L2A
    mock_search.assert_called_once()
    call_kwargs = mock_search.call_args[1]
    assert call_kwargs["product_level"] == "L2A"
