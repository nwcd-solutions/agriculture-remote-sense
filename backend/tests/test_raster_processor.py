"""
RasterProcessor 服务单元测试
"""
import os
import tempfile
import pytest

# 尝试导入依赖，如果失败则跳过测试
try:
    import numpy as np
    import xarray as xr
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="GDAL/rasterio dependencies not available")

from app.services.raster_processor import RasterProcessor
from app.models.aoi import GeoJSON


@pytest.fixture
def raster_processor():
    """创建 RasterProcessor 实例"""
    return RasterProcessor()


@pytest.fixture
def sample_data_array():
    """创建示例 xarray DataArray"""
    # 创建一个简单的 10x10 栅格
    data = np.random.rand(1, 10, 10).astype(np.float32)
    
    # 定义坐标和变换
    transform = from_bounds(-180, -90, 180, 90, 10, 10)
    
    # 创建 DataArray
    da = xr.DataArray(
        data,
        dims=['band', 'y', 'x'],
        coords={
            'band': [1],
            'y': np.linspace(90, -90, 10),
            'x': np.linspace(-180, 180, 10)
        }
    )
    
    # 添加空间参考信息
    da.rio.write_crs('EPSG:4326', inplace=True)
    da.rio.write_transform(transform, inplace=True)
    
    return da


@pytest.fixture
def sample_aoi():
    """创建示例 AOI"""
    # 创建一个小的多边形 AOI
    return GeoJSON(
        type="Polygon",
        coordinates=[[
            [-10.0, -10.0],
            [10.0, -10.0],
            [10.0, 10.0],
            [-10.0, 10.0],
            [-10.0, -10.0]
        ]]
    )


class TestRasterProcessor:
    """RasterProcessor 测试类"""
    
    def test_initialization(self, raster_processor):
        """测试 RasterProcessor 初始化"""
        assert raster_processor is not None
        # 验证 GDAL 环境变量已设置
        assert os.environ.get('GDAL_DISABLE_READDIR_ON_OPEN') == 'EMPTY_DIR'
    
    def test_clip_to_aoi_basic(self, raster_processor, sample_data_array, sample_aoi):
        """测试基本的 AOI 裁剪功能"""
        # 裁剪数据
        clipped = raster_processor.clip_to_aoi(sample_data_array, sample_aoi)
        
        # 验证结果
        assert clipped is not None
        assert isinstance(clipped, xr.DataArray)
        # 裁剪后的数据应该比原始数据小
        assert clipped.shape[1] <= sample_data_array.shape[1]
        assert clipped.shape[2] <= sample_data_array.shape[2]
        # 验证 CRS 保持不变
        assert clipped.rio.crs == sample_data_array.rio.crs
    
    def test_clip_to_aoi_no_crs(self, raster_processor, sample_aoi):
        """测试没有 CRS 的数据裁剪应该失败"""
        # 创建没有 CRS 的数据
        data = xr.DataArray(
            np.random.rand(1, 10, 10),
            dims=['band', 'y', 'x']
        )
        
        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="must have a CRS"):
            raster_processor.clip_to_aoi(data, sample_aoi)
    
    def test_to_cog_basic(self, raster_processor, sample_data_array):
        """测试基本的 COG 输出功能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test_output.tif')
            
            # 保存为 COG
            result_path = raster_processor.to_cog(sample_data_array, output_path)
            
            # 验证文件已创建
            assert os.path.exists(result_path)
            assert result_path == output_path
            
            # 验证文件可以被读取
            with rasterio.open(result_path) as src:
                assert src.count == 1
                assert src.profile['tiled'] is True
                assert src.profile['compress'] == 'DEFLATE'
    
    def test_to_cog_with_compression(self, raster_processor, sample_data_array):
        """测试不同压缩方法的 COG 输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test_compressed.tif')
            
            # 使用 LZW 压缩
            result_path = raster_processor.to_cog(
                sample_data_array, 
                output_path,
                compress='LZW'
            )
            
            # 验证压缩方法
            with rasterio.open(result_path) as src:
                assert src.profile['compress'] == 'LZW'
    
    def test_to_cog_with_tile_size(self, raster_processor, sample_data_array):
        """测试自定义瓦片大小的 COG 输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test_tiled.tif')
            
            # 使用 256x256 瓦片
            result_path = raster_processor.to_cog(
                sample_data_array,
                output_path,
                tile_size=256
            )
            
            # 验证瓦片大小
            with rasterio.open(result_path) as src:
                assert src.profile['blockxsize'] == 256
                assert src.profile['blockysize'] == 256
    
    def test_to_cog_with_nodata(self, raster_processor, sample_data_array):
        """测试带 NoData 值的 COG 输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'test_nodata.tif')
            
            # 设置 NoData 值
            result_path = raster_processor.to_cog(
                sample_data_array,
                output_path,
                nodata=-9999
            )
            
            # 验证 NoData 值
            with rasterio.open(result_path) as src:
                assert src.nodata == -9999
    
    def test_reproject_raster(self, raster_processor, sample_data_array):
        """测试栅格重投影"""
        # 重投影到 Web Mercator
        reprojected = raster_processor.reproject_raster(
            sample_data_array,
            'EPSG:3857'
        )
        
        # 验证结果
        assert reprojected is not None
        assert reprojected.rio.crs == CRS.from_epsg(3857)
        # 形状可能会改变
        assert reprojected.shape[0] == sample_data_array.shape[0]  # 波段数不变
    
    def test_get_raster_info(self, raster_processor, sample_data_array):
        """测试获取栅格信息"""
        info = raster_processor.get_raster_info(sample_data_array)
        
        # 验证信息完整性
        assert 'shape' in info
        assert 'dims' in info
        assert 'crs' in info
        assert 'bounds' in info
        assert 'resolution' in info
        assert 'dtype' in info
        
        # 验证具体值
        assert info['shape'] == (1, 10, 10)
        assert info['crs'] == 'EPSG:4326'
        assert 'min' in info
        assert 'max' in info
        assert 'mean' in info


class TestRasterProcessorIntegration:
    """RasterProcessor 集成测试"""
    
    def test_clip_and_save_workflow(self, raster_processor, sample_data_array, sample_aoi):
        """测试完整的裁剪和保存工作流"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 裁剪数据
            clipped = raster_processor.clip_to_aoi(sample_data_array, sample_aoi)
            
            # 2. 保存为 COG
            output_path = os.path.join(tmpdir, 'clipped_output.tif')
            result_path = raster_processor.to_cog(clipped, output_path)
            
            # 3. 验证输出
            assert os.path.exists(result_path)
            
            # 4. 读取并验证
            with rasterio.open(result_path) as src:
                assert src.count >= 1
                assert src.profile['tiled'] is True
                # 验证数据范围在 AOI 内
                bounds = src.bounds
                assert bounds.left >= -10.0
                assert bounds.right <= 10.0
                assert bounds.bottom >= -10.0
                assert bounds.top <= 10.0
