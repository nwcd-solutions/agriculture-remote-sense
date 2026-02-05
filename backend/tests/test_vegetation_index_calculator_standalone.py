"""
植被指数计算器独立测试

直接测试 VegetationIndexCalculator 类，不依赖其他模块
"""

import sys
import os
import pytest
import numpy as np

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 直接导入类定义，避免通过 __init__.py
from app.services.vegetation_index_calculator import VegetationIndexCalculator


class TestVegetationIndexCalculatorStandalone:
    """独立测试植被指数计算器"""
    
    @pytest.fixture
    def calculator(self):
        """创建计算器实例"""
        return VegetationIndexCalculator()
    
    # NDVI 测试
    def test_ndvi_formula_correctness(self, calculator):
        """验证 NDVI 公式: (NIR - Red) / (NIR + Red)"""
        nir = np.array([0.5, 0.6, 0.7])
        red = np.array([0.2, 0.3, 0.4])
        
        result = calculator.calculate_ndvi(nir, red)
        
        # 手动计算期望值
        expected = (nir - red) / (nir + red)
        np.testing.assert_array_almost_equal(result, expected, decimal=10)
    
    def test_ndvi_known_value(self, calculator):
        """测试 NDVI 已知值: NIR=0.5, Red=0.2 -> NDVI=0.428571"""
        nir = np.array([0.5])
        red = np.array([0.2])
        
        result = calculator.calculate_ndvi(nir, red)
        
        # (0.5 - 0.2) / (0.5 + 0.2) = 0.3 / 0.7 = 0.428571...
        assert result[0] == pytest.approx(0.428571428571, rel=1e-9)
    
    def test_ndvi_zero_handling(self, calculator):
        """测试 NDVI 零值处理"""
        nir = np.array([0.0, 0.5])
        red = np.array([0.0, 0.2])
        
        result = calculator.calculate_ndvi(nir, red)
        
        # 第一个: (0-0)/(0+0) = 0/0 -> 应返回 0
        assert result[0] == 0
        # 第二个: 正常计算
        assert result[1] == pytest.approx(0.428571428571, rel=1e-9)
    
    # SAVI 测试
    def test_savi_formula_correctness(self, calculator):
        """验证 SAVI 公式: (1 + L) * (NIR - Red) / (NIR + Red + L)"""
        nir = np.array([0.5, 0.6])
        red = np.array([0.2, 0.3])
        L = 0.5
        
        result = calculator.calculate_savi(nir, red, L=L)
        
        # 手动计算期望值
        expected = (1 + L) * (nir - red) / (nir + red + L)
        np.testing.assert_array_almost_equal(result, expected, decimal=10)
    
    def test_savi_default_L_value(self, calculator):
        """测试 SAVI 默认 L=0.5"""
        nir = np.array([0.5])
        red = np.array([0.2])
        
        result = calculator.calculate_savi(nir, red)
        
        # (1 + 0.5) * (0.5 - 0.2) / (0.5 + 0.2 + 0.5)
        # = 1.5 * 0.3 / 1.2 = 0.45 / 1.2 = 0.375
        assert result[0] == pytest.approx(0.375, rel=1e-9)
    
    def test_savi_L_zero_equals_ndvi(self, calculator):
        """测试 SAVI 当 L=0 时等于 NDVI"""
        nir = np.array([0.5, 0.6, 0.7])
        red = np.array([0.2, 0.3, 0.4])
        
        savi_L0 = calculator.calculate_savi(nir, red, L=0.0)
        ndvi = calculator.calculate_ndvi(nir, red)
        
        np.testing.assert_array_almost_equal(savi_L0, ndvi, decimal=10)
    
    # EVI 测试
    def test_evi_formula_correctness(self, calculator):
        """验证 EVI 公式: 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)"""
        nir = np.array([0.5])
        red = np.array([0.2])
        blue = np.array([0.1])
        
        result = calculator.calculate_evi(nir, red, blue)
        
        # 手动计算
        expected = 2.5 * (nir - red) / (nir + 6*red - 7.5*blue + 1)
        np.testing.assert_array_almost_equal(result, expected, decimal=10)
    
    def test_evi_known_value(self, calculator):
        """测试 EVI 已知值"""
        nir = np.array([0.5])
        red = np.array([0.2])
        blue = np.array([0.1])
        
        result = calculator.calculate_evi(nir, red, blue)
        
        # 2.5 * (0.5 - 0.2) / (0.5 + 6*0.2 - 7.5*0.1 + 1)
        # = 2.5 * 0.3 / (0.5 + 1.2 - 0.75 + 1)
        # = 0.75 / 1.95
        # = 0.384615384615...
        expected = 0.75 / 1.95
        assert result[0] == pytest.approx(expected, rel=1e-9)
    
    def test_evi_multiple_values(self, calculator):
        """测试 EVI 多个值"""
        nir = np.array([0.5, 0.6, 0.7])
        red = np.array([0.2, 0.3, 0.4])
        blue = np.array([0.1, 0.15, 0.2])
        
        result = calculator.calculate_evi(nir, red, blue)
        
        # 手动计算每个值
        for i in range(3):
            expected = 2.5 * (nir[i] - red[i]) / (nir[i] + 6*red[i] - 7.5*blue[i] + 1)
            assert result[i] == pytest.approx(expected, rel=1e-9)
    
    # VGI 测试
    def test_vgi_formula_correctness(self, calculator):
        """验证 VGI 公式: Green / Red"""
        green = np.array([0.4, 0.5, 0.6])
        red = np.array([0.2, 0.25, 0.3])
        
        result = calculator.calculate_vgi(green, red)
        
        # 手动计算期望值
        expected = green / red
        np.testing.assert_array_almost_equal(result, expected, decimal=10)
    
    def test_vgi_known_values(self, calculator):
        """测试 VGI 已知值"""
        green = np.array([0.4, 0.5])
        red = np.array([0.2, 0.25])
        
        result = calculator.calculate_vgi(green, red)
        
        assert result[0] == pytest.approx(2.0, rel=1e-9)
        assert result[1] == pytest.approx(2.0, rel=1e-9)
    
    def test_vgi_zero_handling(self, calculator):
        """测试 VGI 零值处理"""
        green = np.array([0.4, 0.5])
        red = np.array([0.0, 0.25])
        
        result = calculator.calculate_vgi(green, red)
        
        # 第一个: 0.4 / 0.0 -> 应返回 0
        assert result[0] == 0
        # 第二个: 正常计算
        assert result[1] == pytest.approx(2.0, rel=1e-9)
    
    # 边界情况测试
    def test_all_indices_with_2d_arrays(self, calculator):
        """测试所有指数对 2D 数组的支持"""
        shape = (3, 4)
        nir = np.random.rand(*shape) * 0.5 + 0.3
        red = np.random.rand(*shape) * 0.3 + 0.1
        green = np.random.rand(*shape) * 0.4 + 0.2
        blue = np.random.rand(*shape) * 0.2 + 0.05
        
        ndvi = calculator.calculate_ndvi(nir, red)
        savi = calculator.calculate_savi(nir, red)
        evi = calculator.calculate_evi(nir, red, blue)
        vgi = calculator.calculate_vgi(green, red)
        
        assert ndvi.shape == shape
        assert savi.shape == shape
        assert evi.shape == shape
        assert vgi.shape == shape
    
    def test_no_nan_or_inf_in_results(self, calculator):
        """测试结果中没有 NaN 或 Inf"""
        nir = np.array([0.5, 0.6, 0.0])
        red = np.array([0.2, 0.3, 0.0])
        green = np.array([0.4, 0.5, 0.3])
        blue = np.array([0.1, 0.15, 0.1])
        
        ndvi = calculator.calculate_ndvi(nir, red)
        savi = calculator.calculate_savi(nir, red)
        evi = calculator.calculate_evi(nir, red, blue)
        vgi = calculator.calculate_vgi(green, red)
        
        # 所有结果都应该是有限的数值
        assert np.all(np.isfinite(ndvi))
        assert np.all(np.isfinite(savi))
        assert np.all(np.isfinite(evi))
        assert np.all(np.isfinite(vgi))
    
    def test_requirements_validation(self, calculator):
        """验证需求 5.2, 5.3, 5.4, 5.6"""
        # 需求 5.2: NDVI = (NIR - Red) / (NIR + Red)
        nir, red = 0.6, 0.3
        ndvi = calculator.calculate_ndvi(np.array([nir]), np.array([red]))
        expected_ndvi = (nir - red) / (nir + red)
        assert ndvi[0] == pytest.approx(expected_ndvi, rel=1e-9)
        
        # 需求 5.3: SAVI = (1 + L) * (NIR - Red) / (NIR + Red + L), L=0.5
        savi = calculator.calculate_savi(np.array([nir]), np.array([red]))
        expected_savi = (1 + 0.5) * (nir - red) / (nir + red + 0.5)
        assert savi[0] == pytest.approx(expected_savi, rel=1e-9)
        
        # 需求 5.4: EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
        blue = 0.2
        evi = calculator.calculate_evi(np.array([nir]), np.array([red]), np.array([blue]))
        expected_evi = 2.5 * (nir - red) / (nir + 6*red - 7.5*blue + 1)
        assert evi[0] == pytest.approx(expected_evi, rel=1e-9)
        
        # 需求 5.6: VGI = Green / Red
        green = 0.5
        vgi = calculator.calculate_vgi(np.array([green]), np.array([red]))
        expected_vgi = green / red
        assert vgi[0] == pytest.approx(expected_vgi, rel=1e-9)


if __name__ == "__main__":
    # 允许直接运行此文件进行测试
    pytest.main([__file__, "-v"])
