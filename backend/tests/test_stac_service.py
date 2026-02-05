"""
STAC 查询服务单元测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from app.services.stac_service import STACQueryService


@pytest.fixture
def stac_service():
    """创建 STAC 查询服务实例"""
    return STACQueryService()


@pytest.fixture
def valid_aoi():
    """有效的 AOI GeoJSON"""
    return {
        "type": "Polygon",
        "coordinates": [[
            [116.3, 39.9],
            [116.4, 39.9],
            [116.4, 40.0],
            [116.3, 40.0],
            [116.3, 39.9]
        ]]
    }


@pytest.fixture
def valid_date_range():
    """有效的时间范围"""
    return {
        "start": datetime(2024, 1, 1),
        "end": datetime(2024, 1, 31)
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
    
    # 模拟资产
    thumbnail_asset = Mock()
    thumbnail_asset.href = "https://example.com/thumbnail.jpg"
    
    visual_asset = Mock()
    visual_asset.href = "https://example.com/visual.tif"
    visual_asset.media_type = "image/tiff; application=geotiff; profile=cloud-optimized"
    visual_asset.title = "True color image"
    visual_asset.roles = ["visual"]
    
    item.assets = {
        "thumbnail": thumbnail_asset,
        "visual": visual_asset
    }
    
    return item


def test_geojson_to_bbox(stac_service, valid_aoi):
    """测试 GeoJSON 转 bbox"""
    bbox = stac_service._geojson_to_bbox(valid_aoi)
    
    assert len(bbox) == 4
    assert bbox == [116.3, 39.9, 116.4, 40.0]


def test_geojson_to_bbox_irregular_polygon(stac_service):
    """测试不规则多边形的 bbox 计算"""
    aoi = {
        "type": "Polygon",
        "coordinates": [[
            [0.0, 0.0],
            [2.0, 1.0],
            [1.0, 3.0],
            [-1.0, 2.0],
            [0.0, 0.0]
        ]]
    }
    
    bbox = stac_service._geojson_to_bbox(aoi)
    
    assert bbox == [-1.0, 0.0, 2.0, 3.0]


@patch('app.services.stac_service.Client')
def test_search_sentinel2_basic(mock_client_class, stac_service, valid_aoi, valid_date_range, mock_stac_item):
    """测试基本的 Sentinel-2 查询"""
    # 设置 mock
    mock_client = Mock()
    mock_search = Mock()
    mock_search.items.return_value = [mock_stac_item]
    mock_client.search.return_value = mock_search
    mock_client_class.open.return_value = mock_client
    
    # 执行查询
    results = stac_service.search_sentinel2(
        aoi=valid_aoi,
        date_range=valid_date_range,
        product_level="L2A"
    )
    
    # 验证结果
    assert len(results) == 1
    assert results[0].id == mock_stac_item.id
    
    # 验证调用参数
    mock_client.search.assert_called_once()
    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["collections"] == ["sentinel-2-l2a"]
    assert call_kwargs["bbox"] == [116.3, 39.9, 116.4, 40.0]


@patch('app.services.stac_service.Client')
def test_search_sentinel2_with_cloud_cover(mock_client_class, stac_service, valid_aoi, valid_date_range, mock_stac_item):
    """测试带云量过滤的 Sentinel-2 查询"""
    mock_client = Mock()
    mock_search = Mock()
    mock_search.items.return_value = [mock_stac_item]
    mock_client.search.return_value = mock_search
    mock_client_class.open.return_value = mock_client
    
    # 执行查询
    results = stac_service.search_sentinel2(
        aoi=valid_aoi,
        date_range=valid_date_range,
        cloud_cover_max=20.0,
        product_level="L2A"
    )
    
    # 验证云量过滤参数
    call_kwargs = mock_client.search.call_args[1]
    assert "query" in call_kwargs
    assert call_kwargs["query"]["eo:cloud_cover"]["lte"] == 20.0


@patch('app.services.stac_service.Client')
def test_search_sentinel1(mock_client_class, stac_service, valid_aoi, valid_date_range):
    """测试 Sentinel-1 查询"""
    mock_client = Mock()
    mock_search = Mock()
    mock_search.items.return_value = []
    mock_client.search.return_value = mock_search
    mock_client_class.open.return_value = mock_client
    
    # 执行查询
    results = stac_service.search_sentinel1(
        aoi=valid_aoi,
        date_range=valid_date_range,
        product_type="GRD"
    )
    
    # 验证调用参数
    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["collections"] == ["sentinel-1-grd"]


@patch('app.services.stac_service.Client')
def test_search_landsat8(mock_client_class, stac_service, valid_aoi, valid_date_range):
    """测试 Landsat 8 查询"""
    mock_client = Mock()
    mock_search = Mock()
    mock_search.items.return_value = []
    mock_client.search.return_value = mock_search
    mock_client_class.open.return_value = mock_client
    
    # 执行查询
    results = stac_service.search_landsat8(
        aoi=valid_aoi,
        date_range=valid_date_range,
        product_level="L2"
    )
    
    # 验证调用参数
    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["collections"] == ["landsat-c2-l2"]


@patch('app.services.stac_service.Client')
def test_search_modis(mock_client_class, stac_service, valid_aoi, valid_date_range):
    """测试 MODIS 查询"""
    mock_client = Mock()
    mock_search = Mock()
    mock_search.items.return_value = []
    mock_client.search.return_value = mock_search
    mock_client_class.open.return_value = mock_client
    
    # 执行查询
    results = stac_service.search_modis(
        aoi=valid_aoi,
        date_range=valid_date_range,
        product="MCD43A4"
    )
    
    # 验证调用参数
    call_kwargs = mock_client.search.call_args[1]
    assert call_kwargs["collections"] == ["modis-mcd43a4"]


@patch('app.services.stac_service.Client')
def test_search_error_handling(mock_client_class, stac_service, valid_aoi, valid_date_range):
    """测试查询错误处理"""
    mock_client = Mock()
    mock_client.search.side_effect = Exception("STAC API error")
    mock_client_class.open.return_value = mock_client
    
    # 验证异常被正确抛出
    with pytest.raises(Exception, match="STAC API error"):
        stac_service.search_sentinel2(
            aoi=valid_aoi,
            date_range=valid_date_range
        )


def test_client_reuse(stac_service):
    """测试客户端重用"""
    client1 = stac_service._get_client()
    client2 = stac_service._get_client()
    
    # 验证返回同一个客户端实例
    assert client1 is client2
