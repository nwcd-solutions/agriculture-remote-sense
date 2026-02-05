"""
数据处理服务

处理植被指数计算和其他栅格处理任务
"""
import os
import tempfile
from typing import Dict, List
import numpy as np
import xarray as xr
from app.models.processing import IndicesProcessingRequest, ProcessingResult
from app.models.aoi import GeoJSON
from app.services.raster_processor import RasterProcessor
from app.services.vegetation_index_calculator import VegetationIndexCalculator


class ProcessingService:
    """
    数据处理服务类
    
    集成栅格处理器和植被指数计算器，提供完整的数据处理流程
    """
    
    def __init__(self, output_dir: str = None):
        """
        初始化处理服务
        
        Args:
            output_dir: 输出目录，None 表示使用临时目录
        """
        self.raster_processor = RasterProcessor()
        self.index_calculator = VegetationIndexCalculator()
        
        if output_dir is None:
            self.output_dir = tempfile.mkdtemp(prefix="satellite_gis_")
        else:
            self.output_dir = output_dir
            os.makedirs(self.output_dir, exist_ok=True)
    
    def process_vegetation_indices(
        self,
        request: IndicesProcessingRequest
    ) -> ProcessingResult:
        """
        处理植被指数计算请求
        
        Args:
            request: 植被指数计算请求
            
        Returns:
            ProcessingResult: 处理结果
            
        Raises:
            ValueError: 如果处理失败
        """
        try:
            # 1. 读取所需的波段数据
            band_data = self._load_bands(request.band_urls, request.aoi)
            
            # 2. 计算每个指定的植被指数
            output_files = []
            
            for index_name in request.indices:
                try:
                    # 计算指数
                    index_data = self._calculate_index(index_name, band_data)
                    
                    # 保存为 COG
                    output_filename = f"{request.image_id}_{index_name}.tif"
                    output_path = os.path.join(self.output_dir, output_filename)
                    
                    # 将 numpy 数组转换为 xarray DataArray
                    index_xr = self._numpy_to_xarray(
                        index_data,
                        band_data['template']
                    )
                    
                    # 保存为 COG
                    self.raster_processor.to_cog(
                        index_xr,
                        output_path,
                        compress='DEFLATE',
                        nodata=-9999
                    )
                    
                    # 获取文件大小
                    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    
                    output_files.append({
                        "name": output_filename,
                        "path": output_path,
                        "url": f"/api/download/{output_filename}",  # 需要实现下载端点
                        "size_mb": round(file_size_mb, 2),
                        "index": index_name
                    })
                    
                except Exception as e:
                    raise ValueError(f"Failed to calculate {index_name}: {str(e)}")
            
            # 3. 返回处理结果
            result = ProcessingResult(
                output_files=output_files,
                metadata={
                    "image_id": request.image_id,
                    "indices": request.indices,
                    "aoi": request.aoi.model_dump(),
                    "output_format": request.output_format
                }
            )
            
            return result
            
        except Exception as e:
            raise ValueError(f"Processing failed: {str(e)}")
    
    def _load_bands(
        self,
        band_urls: Dict[str, str],
        aoi: GeoJSON
    ) -> Dict[str, xr.DataArray]:
        """
        加载并裁剪波段数据
        
        Args:
            band_urls: 波段 URL 字典
            aoi: 感兴趣区域
            
        Returns:
            Dict[str, xr.DataArray]: 波段数据字典
        """
        band_data = {}
        template = None
        
        for band_name, url in band_urls.items():
            # 读取波段数据
            data = self.raster_processor.read_cog_from_url(url)
            
            # 裁剪到 AOI
            clipped = self.raster_processor.clip_to_aoi(data, aoi)
            
            # 如果是多波段，取第一个波段
            if len(clipped.shape) == 3:
                clipped = clipped.isel(band=0)
            
            band_data[band_name] = clipped
            
            # 保存第一个波段作为模板（用于保持空间参考）
            if template is None:
                template = clipped
        
        # 添加模板到结果中
        band_data['template'] = template
        
        return band_data
    
    def _calculate_index(
        self,
        index_name: str,
        band_data: Dict[str, xr.DataArray]
    ) -> np.ndarray:
        """
        计算指定的植被指数
        
        Args:
            index_name: 指数名称
            band_data: 波段数据字典
            
        Returns:
            np.ndarray: 计算结果
            
        Raises:
            ValueError: 如果缺少必需的波段
        """
        # 将 xarray 转换为 numpy 数组
        def get_band(name: str) -> np.ndarray:
            if name not in band_data:
                raise ValueError(f"Missing required band: {name}")
            return band_data[name].values.astype(np.float32)
        
        if index_name == "NDVI":
            nir = get_band("nir")
            red = get_band("red")
            return self.index_calculator.calculate_ndvi(nir, red)
        
        elif index_name == "SAVI":
            nir = get_band("nir")
            red = get_band("red")
            return self.index_calculator.calculate_savi(nir, red, L=0.5)
        
        elif index_name == "EVI":
            nir = get_band("nir")
            red = get_band("red")
            blue = get_band("blue")
            return self.index_calculator.calculate_evi(nir, red, blue)
        
        elif index_name == "VGI":
            green = get_band("green")
            red = get_band("red")
            return self.index_calculator.calculate_vgi(green, red)
        
        else:
            raise ValueError(f"Unknown index: {index_name}")
    
    def _numpy_to_xarray(
        self,
        data: np.ndarray,
        template: xr.DataArray
    ) -> xr.DataArray:
        """
        将 numpy 数组转换为 xarray DataArray，保持空间参考
        
        Args:
            data: numpy 数组
            template: 模板 DataArray（用于获取坐标和 CRS）
            
        Returns:
            xr.DataArray: 转换后的 DataArray
        """
        # 创建新的 DataArray
        result = xr.DataArray(
            data,
            coords={
                'y': template.coords['y'],
                'x': template.coords['x']
            },
            dims=['y', 'x']
        )
        
        # 复制空间参考信息
        result.rio.write_crs(template.rio.crs, inplace=True)
        result.rio.write_transform(template.rio.transform(), inplace=True)
        
        return result
    
    def get_required_bands(self, indices: List[str]) -> List[str]:
        """
        获取计算指定指数所需的波段列表
        
        Args:
            indices: 指数名称列表
            
        Returns:
            List[str]: 所需波段列表
        """
        required_bands = set()
        
        band_requirements = {
            "NDVI": ["nir", "red"],
            "SAVI": ["nir", "red"],
            "EVI": ["nir", "red", "blue"],
            "VGI": ["green", "red"]
        }
        
        for index in indices:
            if index in band_requirements:
                required_bands.update(band_requirements[index])
        
        return list(required_bands)
