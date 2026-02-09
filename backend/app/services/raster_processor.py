"""
栅格数据处理服务
"""
import os
import tempfile
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask
from rasterio.crs import CRS
import rioxarray
import xarray as xr
from shapely.geometry import shape, mapping
from app.models.aoi import GeoJSON


class RasterProcessor:
    """栅格数据处理器类"""
    
    def __init__(self):
        """初始化栅格处理器"""
        # 配置 GDAL 环境变量以支持云优化访问
        os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'EMPTY_DIR'
        os.environ['CPL_VSIL_CURL_ALLOWED_EXTENSIONS'] = '.tif,.tiff,.jp2'
        
        # 增加网络超时和重试配置
        os.environ['GDAL_HTTP_TIMEOUT'] = '600'        # 10分钟超时
        os.environ['GDAL_HTTP_MAX_RETRY'] = '5'        # 最多重试5次
        os.environ['GDAL_HTTP_RETRY_DELAY'] = '10'     # 重试间隔10秒
        os.environ['CPL_VSIL_CURL_CHUNK_SIZE'] = '10485760'  # 10MB 块大小
        os.environ['GDAL_HTTP_CONNECTTIMEOUT'] = '60'  # 连接超时60秒
        
        # 启用内存数据集（用于 rioxarray clip 操作）
        os.environ['GDAL_MEM_ENABLE_OPEN'] = 'YES'
        
        # 启用 GDAL 缓存
        os.environ['GDAL_CACHEMAX'] = '512'  # 512MB 缓存
    
    def read_cog_from_url(
        self, 
        url: str, 
        bands: Optional[List[int]] = None
    ) -> xr.DataArray:
        """
        从 S3 URL 读取云优化 GeoTIFF (COG) 数据
        
        支持的格式：
        - GeoTIFF (.tif, .tiff)
        - JPEG2000 (.jp2) - Sentinel-2 原生格式
        - COG (Cloud Optimized GeoTIFF)
        
        Args:
            url: S3 URL 或 HTTP URL
            bands: 要读取的波段列表（1-based index），None 表示读取所有波段
            
        Returns:
            xr.DataArray: 栅格数据数组
            
        Raises:
            ValueError: 如果 URL 无效或读取失败
        """
        original_url = url
        try:
            # 使用 rioxarray 读取 COG
            # rioxarray 会自动处理 /vsicurl/ 前缀
            if url.startswith('s3://'):
                # 转换 s3:// 到 /vsis3/
                url = url.replace('s3://', '/vsis3/')
            elif url.startswith('http://') or url.startswith('https://'):
                # HTTP URL 需要添加 /vsicurl/ 前缀以使用GDAL虚拟文件系统
                if not url.startswith('/vsicurl/'):
                    url = f'/vsicurl/{url}'
            elif url.startswith('/vsicurl/') or url.startswith('/vsis3/'):
                # 已经是GDAL虚拟文件系统格式，直接使用
                pass
            else:
                # 本地文件路径，直接使用
                pass
            
            # 读取数据
            # rioxarray 支持 GeoTIFF 和 JPEG2000 格式
            data = rioxarray.open_rasterio(url, chunks='auto')
            
            # 如果指定了波段，只读取这些波段
            if bands is not None:
                # 转换为 0-based index
                band_indices = [b - 1 for b in bands]
                data = data.isel(band=band_indices)
            
            return data
            
        except Exception as e:
            error_msg = str(e)
            # 提供更友好的错误信息
            if "404" in error_msg or "HTTP response code: 404" in error_msg:
                raise ValueError(
                    f"Failed to read COG from URL {original_url}: "
                    f"File not found (HTTP 404). Please verify the URL is correct and the file exists."
                )
            elif "403" in error_msg or "HTTP response code: 403" in error_msg:
                raise ValueError(
                    f"Failed to read COG from URL {original_url}: "
                    f"Access denied (HTTP 403). Please check authentication or permissions."
                )
            elif "does not exist in the file system" in error_msg:
                raise ValueError(
                    f"Failed to read COG from URL {original_url}: "
                    f"File not found. This may be due to: "
                    f"1) The file does not exist at this location, "
                    f"2) Missing AWS credentials for S3 access, or "
                    f"3) Incorrect S3 bucket/path. "
                    f"For S3 access, ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are configured."
                )
            elif "timeout" in error_msg.lower():
                raise ValueError(
                    f"Failed to read COG from URL {original_url}: "
                    f"Connection timeout. The server may be slow or unreachable."
                )
            else:
                raise ValueError(f"Failed to read COG from URL {original_url}: {error_msg}")
    
    def clip_to_aoi(
        self, 
        data: xr.DataArray, 
        aoi: GeoJSON,
        all_touched: bool = True
    ) -> xr.DataArray:
        """
        将栅格数据裁剪到感兴趣区域 (AOI)
        
        Args:
            data: 输入栅格数据
            aoi: GeoJSON 格式的 AOI
            all_touched: 是否包含所有接触 AOI 的像素
            
        Returns:
            xr.DataArray: 裁剪后的栅格数据
            
        Raises:
            ValueError: 如果裁剪失败
        """
        try:
            from shapely.geometry import box as shapely_box
            
            # 转换 GeoJSON 到 shapely 几何对象
            geom = shape(aoi.model_dump())
            
            # 确保数据有 CRS
            if data.rio.crs is None:
                raise ValueError("Input data must have a CRS")
            
            # 获取 AOI 的 CRS（假设为 WGS84）
            aoi_crs = CRS.from_epsg(4326)
            
            # 如果 AOI 和数据的 CRS 不同，需要重投影 AOI
            if data.rio.crs != aoi_crs:
                from pyproj import Transformer
                transformer = Transformer.from_crs(
                    aoi_crs, 
                    data.rio.crs, 
                    always_xy=True
                )
                from shapely.ops import transform as shapely_transform
                geom = shapely_transform(transformer.transform, geom)
            
            # 检查 AOI 与栅格数据的空间重叠
            raster_bounds = data.rio.bounds()  # (left, bottom, right, top)
            raster_box = shapely_box(*raster_bounds)
            
            intersection = geom.intersection(raster_box)
            if intersection.is_empty:
                raise ValueError(
                    f"AOI does not overlap with raster data. "
                    f"Raster bounds: {raster_bounds}, AOI bounds: {geom.bounds}"
                )
            
            # 使用交集区域进行裁剪，避免 NoDataInBounds 错误
            clip_geom = intersection
            
            # 使用 rioxarray 的 clip 方法
            clipped = data.rio.clip(
                [mapping(clip_geom)], 
                data.rio.crs,
                drop=True,
                all_touched=all_touched
            )
            
            return clipped
            
        except Exception as e:
            raise ValueError(f"Failed to clip raster to AOI: {str(e)}")
    
    def to_cog(
        self,
        data: xr.DataArray,
        output_path: str,
        compress: str = 'DEFLATE',
        tile_size: int = 512,
        overview_levels: Optional[List[int]] = None,
        nodata: Optional[float] = None
    ) -> str:
        """
        将栅格数据保存为云优化 GeoTIFF (COG) 格式
        
        Args:
            data: 输入栅格数据
            output_path: 输出文件路径
            compress: 压缩方法 (DEFLATE, LZW, ZSTD, etc.)
            tile_size: 瓦片大小（像素）
            overview_levels: 概览层级列表，None 表示自动生成
            nodata: NoData 值
            
        Returns:
            str: 输出文件路径
            
        Raises:
            ValueError: 如果保存失败
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 配置 COG 参数
            cog_profile = {
                'driver': 'GTiff',
                'compress': compress,
                'tiled': True,
                'blockxsize': tile_size,
                'blockysize': tile_size,
                'COPY_SRC_OVERVIEWS': 'YES',
                'TILED': 'YES',
            }
            
            # 如果指定了 nodata 值
            if nodata is not None:
                cog_profile['nodata'] = nodata
            
            # 使用 rioxarray 保存
            # 首先保存为临时文件
            temp_path = output_path + '.tmp'
            data.rio.to_raster(
                temp_path,
                driver='GTiff',
                compress=compress,
                tiled=True,
                blockxsize=tile_size,
                blockysize=tile_size
            )
            
            # 使用 GDAL 添加概览和优化为 COG
            with rasterio.open(temp_path) as src:
                profile = src.profile.copy()
                profile.update(cog_profile)
                
                # 计算概览层级
                if overview_levels is None:
                    # 自动计算概览层级
                    max_dim = max(src.width, src.height)
                    overview_levels = []
                    level = 2
                    while max_dim / level > tile_size:
                        overview_levels.append(level)
                        level *= 2
                
                # 读取数据
                data_array = src.read()
                
                # 写入 COG
                with rasterio.open(output_path, 'w', **profile) as dst:
                    dst.write(data_array)
                    
                    # 构建概览
                    if overview_levels:
                        dst.build_overviews(overview_levels, Resampling.average)
                        dst.update_tags(ns='rio_overview', resampling='average')
            
            # 删除临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # 验证 COG 格式
            self._validate_cog(output_path)
            
            return output_path
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise ValueError(f"Failed to save as COG: {str(e)}")
    
    def _validate_cog(self, file_path: str) -> bool:
        """
        验证文件是否为有效的 COG 格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为有效的 COG
            
        Raises:
            ValueError: 如果不是有效的 COG
        """
        try:
            with rasterio.open(file_path) as src:
                # 检查是否为瓦片格式
                if not src.profile.get('tiled', False):
                    raise ValueError("File is not tiled")
                
                # 检查是否有概览
                if not src.overviews(1):
                    # 概览是可选的，只发出警告
                    pass
                
                # 检查是否有压缩
                if src.profile.get('compress') is None:
                    # 压缩是可选的，只发出警告
                    pass
                
                return True
                
        except Exception as e:
            raise ValueError(f"COG validation failed: {str(e)}")
    
    def reproject_raster(
        self,
        data: xr.DataArray,
        target_crs: str,
        resolution: Optional[Tuple[float, float]] = None,
        resampling: str = 'bilinear'
    ) -> xr.DataArray:
        """
        重投影栅格数据
        
        Args:
            data: 输入栅格数据
            target_crs: 目标坐标系（EPSG 代码或 WKT）
            resolution: 目标分辨率 (x_res, y_res)，None 表示保持原分辨率
            resampling: 重采样方法
            
        Returns:
            xr.DataArray: 重投影后的栅格数据
        """
        try:
            # 转换重采样方法
            resampling_methods = {
                'nearest': Resampling.nearest,
                'bilinear': Resampling.bilinear,
                'cubic': Resampling.cubic,
                'average': Resampling.average,
            }
            resampling_method = resampling_methods.get(
                resampling.lower(), 
                Resampling.bilinear
            )
            
            # 使用 rioxarray 重投影
            reprojected = data.rio.reproject(
                target_crs,
                resolution=resolution,
                resampling=resampling_method
            )
            
            return reprojected
            
        except Exception as e:
            raise ValueError(f"Failed to reproject raster: {str(e)}")
    
    def get_raster_info(self, data: xr.DataArray) -> Dict[str, Any]:
        """
        获取栅格数据信息
        
        Args:
            data: 栅格数据
            
        Returns:
            Dict: 栅格信息字典
        """
        info = {
            'shape': data.shape,
            'dims': list(data.dims),
            'crs': str(data.rio.crs) if data.rio.crs else None,
            'bounds': data.rio.bounds() if data.rio.crs else None,
            'resolution': data.rio.resolution() if data.rio.crs else None,
            'nodata': data.rio.nodata,
            'dtype': str(data.dtype),
        }
        
        # 添加统计信息
        try:
            info['min'] = float(data.min().values)
            info['max'] = float(data.max().values)
            info['mean'] = float(data.mean().values)
        except:
            pass
        
        return info

    def apply_cloud_mask(
        self,
        data: xr.DataArray,
        qa_band: xr.DataArray,
        satellite: str = "sentinel-2"
    ) -> xr.DataArray:
        """
        应用云和质量掩膜到光学卫星数据
        
        支持 Sentinel-2 SCL (Scene Classification Layer) 和
        Landsat 8 QA_PIXEL 质量波段。
        
        被掩膜的像素设为 NaN，以便在时间合成时被排除。
        
        Args:
            data: 输入栅格数据
            qa_band: 质量波段数据
            satellite: 卫星类型 ("sentinel-2" 或 "landsat-8")
            
        Returns:
            xr.DataArray: 应用掩膜后的数据（云像素为 NaN）
            
        Raises:
            ValueError: 如果卫星类型不支持或数据形状不匹配
        """
        if satellite not in ("sentinel-2", "landsat-8"):
            raise ValueError(f"Cloud masking not supported for satellite: {satellite}")

        # 获取 QA 值的 numpy 数组
        qa_values = qa_band.values
        # 如果 qa_band 有 band 维度，取第一个
        if qa_values.ndim == 3:
            qa_values = qa_values[0]

        if satellite == "sentinel-2":
            # Sentinel-2 SCL (Scene Classification Layer) 分类值:
            #   0: No Data
            #   1: Saturated or defective
            #   2: Dark area pixels (topographic shadows)
            #   3: Cloud shadows
            #   6: Water
            #   8: Cloud medium probability
            #   9: Cloud high probability
            #  10: Thin cirrus
            #  11: Snow/Ice
            # 保留: 4 (Vegetation), 5 (Not vegetated), 7 (Unclassified)
            bad_classes = {0, 1, 3, 8, 9, 10}
            cloud_mask = np.isin(qa_values, list(bad_classes))
        else:
            # Landsat 8 QA_PIXEL 位掩码:
            #   Bit 1: Dilated Cloud
            #   Bit 3: Cloud
            #   Bit 4: Cloud Shadow
            # 如果这些位中任何一个为 1，则标记为云
            cloud_bit = 1 << 3       # bit 3: Cloud
            shadow_bit = 1 << 4      # bit 4: Cloud Shadow
            dilated_bit = 1 << 1     # bit 1: Dilated Cloud
            qa_int = qa_values.astype(np.uint16)
            cloud_mask = (
                ((qa_int & cloud_bit) != 0) |
                ((qa_int & shadow_bit) != 0) |
                ((qa_int & dilated_bit) != 0)
            )

        # 将 data 转为 float（如果还不是）以支持 NaN
        masked = data.astype(np.float32).copy()

        # 广播掩膜到数据维度
        if masked.values.ndim == 3:
            # (band, y, x) — 对每个 band 应用同一个 (y, x) 掩膜
            for i in range(masked.values.shape[0]):
                masked.values[i][cloud_mask] = np.nan
        else:
            masked.values[cloud_mask] = np.nan

        return masked
