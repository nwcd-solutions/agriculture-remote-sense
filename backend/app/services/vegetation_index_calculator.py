"""
植被指数计算器

实现标准植被指数的计算，包括：
- NDVI (归一化植被指数)
- SAVI (土壤调节植被指数)
- EVI (增强植被指数)
- VGI (植被绿度指数)
"""

import numpy as np
from typing import Optional


class VegetationIndexCalculator:
    """
    植被指数计算器类
    
    提供多种植被指数的计算方法，用于评估植被健康状况和覆盖度。
    所有方法都接受 numpy 数组作为输入，并返回计算后的指数数组。
    """
    
    def calculate_ndvi(self, nir: np.ndarray, red: np.ndarray) -> np.ndarray:
        """
        计算归一化植被指数 (NDVI)
        
        公式: NDVI = (NIR - Red) / (NIR + Red)
        
        NDVI 是最常用的植被指数，用于评估植被的生长状态和覆盖度。
        值范围通常在 -1 到 1 之间，其中：
        - 负值通常表示水体
        - 接近 0 表示裸土或建筑
        - 正值表示植被，值越高植被越茂盛
        
        参数:
            nir: 近红外波段数据 (numpy 数组)
            red: 红光波段数据 (numpy 数组)
            
        返回:
            NDVI 计算结果 (numpy 数组)
            
        验证: 需求 5.2
        """
        # 避免除零错误，使用 numpy 的 divide 函数
        # 当分母为 0 时，返回 0
        denominator = nir + red
        with np.errstate(divide='ignore', invalid='ignore'):
            ndvi = np.where(
                denominator != 0,
                (nir - red) / denominator,
                0
            )
        return ndvi
    
    def calculate_savi(
        self, 
        nir: np.ndarray, 
        red: np.ndarray, 
        L: float = 0.5
    ) -> np.ndarray:
        """
        计算土壤调节植被指数 (SAVI)
        
        公式: SAVI = (1 + L) * (NIR - Red) / (NIR + Red + L)
        
        SAVI 是 NDVI 的改进版本，通过引入土壤调节因子 L 来减少土壤背景的影响。
        适用于植被覆盖度较低的区域。
        
        参数:
            nir: 近红外波段数据 (numpy 数组)
            red: 红光波段数据 (numpy 数组)
            L: 土壤调节因子，默认为 0.5
               - L = 0: 高植被覆盖度
               - L = 0.5: 中等植被覆盖度
               - L = 1: 低植被覆盖度
            
        返回:
            SAVI 计算结果 (numpy 数组)
            
        验证: 需求 5.3
        """
        # 避免除零错误
        denominator = nir + red + L
        with np.errstate(divide='ignore', invalid='ignore'):
            savi = np.where(
                denominator != 0,
                (1 + L) * (nir - red) / denominator,
                0
            )
        return savi
    
    def calculate_evi(
        self, 
        nir: np.ndarray, 
        red: np.ndarray, 
        blue: np.ndarray
    ) -> np.ndarray:
        """
        计算增强植被指数 (EVI)
        
        公式: EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
        
        EVI 是为了改善 NDVI 在高生物量区域的饱和问题而开发的。
        它对大气条件和土壤背景的敏感度较低，适用于高植被覆盖度区域。
        
        参数:
            nir: 近红外波段数据 (numpy 数组)
            red: 红光波段数据 (numpy 数组)
            blue: 蓝光波段数据 (numpy 数组)
            
        返回:
            EVI 计算结果 (numpy 数组)
            
        验证: 需求 5.4
        """
        # 避免除零错误
        denominator = nir + 6 * red - 7.5 * blue + 1
        with np.errstate(divide='ignore', invalid='ignore'):
            evi = np.where(
                denominator != 0,
                2.5 * (nir - red) / denominator,
                0
            )
        return evi
    
    def calculate_vgi(self, green: np.ndarray, red: np.ndarray) -> np.ndarray:
        """
        计算植被绿度指数 (VGI)
        
        公式: VGI = Green / Red
        
        VGI 是一个简单的比值指数，用于评估植被的绿度。
        较高的 VGI 值表示更高的叶绿素含量和更健康的植被。
        
        参数:
            green: 绿光波段数据 (numpy 数组)
            red: 红光波段数据 (numpy 数组)
            
        返回:
            VGI 计算结果 (numpy 数组)
            
        验证: 需求 5.6
        """
        # 避免除零错误
        with np.errstate(divide='ignore', invalid='ignore'):
            vgi = np.where(
                red != 0,
                green / red,
                0
            )
        return vgi
