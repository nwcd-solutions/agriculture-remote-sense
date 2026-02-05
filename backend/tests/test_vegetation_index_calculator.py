"""
植被指数计算器测试

测试 VegetationIndexCalculator 类的所有方法，包括：
- NDVI 计算
- SAVI 计算
- EVI 计算
- VGI 计算
"""

import pytest
import numpy as np
from app.services.vegetation_index_calculator import VegetationIndexCalculator


class TestVegetationIndexCalculator:
    """测试植被指数计算器"""
    
    @pytest.fixture
    def calculator(self):
        """创建计算器实例"""
        return VegetationIndexCalculator()
    
    # NDVI 测试
    def test_ndvi_calculation_known_values(self, calculator):
        """测试 NDVI 计算的已知参考值"""
        nir = np.array([0.5, 0.6, 0.7])
        red = np.array([0.2, 0.3, 0.4])
        expected = np.array([0.42857143, 0.33333333, 0.27272727])
        
        result = calculator.calculate_ndvi(nir, red)
        
        np.testing.assert_array_almost_equal(result, expected, decimal=6)
    
    def test_ndvi_zero_denominator(self, calculator):
        """测试 NDVI 在分母为零时的处理"""
        nir = np.array([0.0, 0.0, 0.5])
        red = np.array([0.0, 0.0, 0.2])
        
        result = calculator.calculate_ndvi(nir, red)
        
        # 前两个值分母为 0，应该返回 0
        assert result[0] == 0
        assert result[1] == 0
        # 第三个值正常计算
        assert result[2] == pytest.approx(0.42857143, rel=1e-6)
    
    def test_ndvi_negative_values(self, calculator):
        """测试 NDVI 对负值的处理（水体）"""
        nir = np.array([0.1, 0.2])
        red = np.array([0.3, 0.4])
        
        result = calculator.calculate_ndvi(nir, red)
        
        # 水体通常有负的 NDVI 值
        assert result[0] < 0
        assert result[1] < 0
    
    def test_ndvi_array_shapes(self, calculator):
        """测试 NDVI 对不同数组形状的处理"""
        # 2D 数组
        nir = np.array([[0.5, 0.6], [0.7, 0.8]])
        red = np.array([[0.2, 0.3], [0.4, 0.5]])
        
        result = calculator.calculate_ndvi(nir, red)
        
        assert result.shape == (2, 2)
        assert result[0, 0] == pytest.approx(0.42857143, rel=1e-6)
    
    # SAVI 测试
    def test_savi_calculation_default_L(self, calculator):
        """测试 SAVI 计算（默认 L=0.5）"""
        nir = np.array([0.5, 0.6, 0.7])
        red = np.array([0.2, 0.3, 0.4])
        # SAVI = (1 + 0.5) * (NIR - Red) / (NIR + Red + 0.5)
        expected = np.array([0.45, 0.375, 0.3125])
        
        result = calculator.calculate_savi(nir, red)
        
        np.testing.assert_array_almost_equal(result, expected, decimal=6)
    
    def test_savi_calculation_custom_L(self, calculator):
        """测试 SAVI 计算（自定义 L 值）"""
        nir = np.array([0.5])
        red = np.array([0.2])
        
        # L = 0 (高植被覆盖度)
        result_L0 = calculator.calculate_savi(nir, red, L=0.0)
        # L = 1 (低植被覆盖度)
        result_L1 = calculator.calculate_savi(nir, red, L=1.0)
        
        # L=0 时，SAVI = (NIR - Red) / (NIR + Red) = NDVI
        ndvi = calculator.calculate_ndvi(nir, red)
        np.testing.assert_array_almost_equal(result_L0, ndvi, decimal=6)
        
        # L=1 时，SAVI = 2 * (NIR - Red) / (NIR + Red + 1)
        expected_L1 = 2 * (0.5 - 0.2) / (0.5 + 0.2 + 1)
        assert result_L1[0] == pytest.approx(expected_L1, rel=1e-6)
    
    def test_savi_zero_denominator(self, calculator):
        """测试 SAVI 在分母为零时的处理"""
        # 这种情况很少见，因为有 L 的存在
        nir = np.array([0.0])
        red = np.array([0.0])
        
        result = calculator.calculate_savi(nir, red, L=-0.0)  # 极端情况
        
        # 应该安全处理，不抛出异常
        assert not np.isnan(result[0])
    
    # EVI 测试
    def test_evi_calculation_known_values(self, calculator):
        """测试 EVI 计算的已知参考值"""
        nir = np.array([0.5])
        red = np.array([0.2])
        blue = np.array([0.1])
        # EVI = 2.5 * (0.5 - 0.2) / (0.5 + 6*0.2 - 7.5*0.1 + 1)
        # EVI = 2.5 * 0.3 / (0.5 + 1.2 - 0.75 + 1)
        # EVI = 0.75 / 1.95
        expected = 0.75 / 1.95
        
        result = calculator.calculate_evi(nir, red, blue)
        
        assert result[0] == pytest.approx(expected, rel=1e-6)
    
    def test_evi_multiple_pixels(self, calculator):
        """测试 EVI 对多个像素的计算"""
        nir = np.array([0.5, 0.6, 0.7])
        red = np.array([0.2, 0.3, 0.4])
        blue = np.array([0.1, 0.15, 0.2])
        
        result = calculator.calculate_evi(nir, red, blue)
        
        assert result.shape == (3,)
        # 验证第一个值
        expected_0 = 2.5 * (0.5 - 0.2) / (0.5 + 6*0.2 - 7.5*0.1 + 1)
        assert result[0] == pytest.approx(expected_0, rel=1e-6)
    
    def test_evi_zero_denominator(self, calculator):
        """测试 EVI 在分母为零时的处理"""
        # 构造一个使分母接近 0 的情况
        # NIR + 6*Red - 7.5*Blue + 1 = 0
        # 这在实际中很难发生，因为有常数项 1
        nir = np.array([0.0])
        red = np.array([0.0])
        blue = np.array([0.0])
        
        result = calculator.calculate_evi(nir, red, blue)
        
        # 应该安全处理
        assert not np.isnan(result[0])
    
    def test_evi_2d_array(self, calculator):
        """测试 EVI 对 2D 数组的处理"""
        nir = np.array([[0.5, 0.6], [0.7, 0.8]])
        red = np.array([[0.2, 0.3], [0.4, 0.5]])
        blue = np.array([[0.1, 0.15], [0.2, 0.25]])
        
        result = calculator.calculate_evi(nir, red, blue)
        
        assert result.shape == (2, 2)
    
    # VGI 测试
    def test_vgi_calculation_known_values(self, calculator):
        """测试 VGI 计算的已知参考值"""
        green = np.array([0.4, 0.5, 0.6])
        red = np.array([0.2, 0.25, 0.3])
        expected = np.array([2.0, 2.0, 2.0])
        
        result = calculator.calculate_vgi(green, red)
        
        np.testing.assert_array_almost_equal(result, expected, decimal=6)
    
    def test_vgi_zero_denominator(self, calculator):
        """测试 VGI 在分母为零时的处理"""
        green = np.array([0.4, 0.5])
        red = np.array([0.0, 0.2])
        
        result = calculator.calculate_vgi(green, red)
        
        # 第一个值分母为 0，应该返回 0
        assert result[0] == 0
        # 第二个值正常计算
        assert result[1] == pytest.approx(2.5, rel=1e-6)
    
    def test_vgi_various_ratios(self, calculator):
        """测试 VGI 对不同比值的计算"""
        green = np.array([0.3, 0.4, 0.5])
        red = np.array([0.3, 0.2, 0.1])
        expected = np.array([1.0, 2.0, 5.0])
        
        result = calculator.calculate_vgi(green, red)
        
        np.testing.assert_array_almost_equal(result, expected, decimal=6)
    
    # 集成测试
    def test_all_indices_same_input(self, calculator):
        """测试所有指数使用相同输入的计算"""
        nir = np.array([0.6])
        red = np.array([0.3])
        green = np.array([0.4])
        blue = np.array([0.2])
        
        ndvi = calculator.calculate_ndvi(nir, red)
        savi = calculator.calculate_savi(nir, red)
        evi = calculator.calculate_evi(nir, red, blue)
        vgi = calculator.calculate_vgi(green, red)
        
        # 所有结果都应该是有效的数值
        assert not np.isnan(ndvi[0])
        assert not np.isnan(savi[0])
        assert not np.isnan(evi[0])
        assert not np.isnan(vgi[0])
        
        # NDVI 应该在 -1 到 1 之间
        assert -1 <= ndvi[0] <= 1
    
    def test_large_array_performance(self, calculator):
        """测试大数组的处理性能"""
        # 模拟一个 1000x1000 的影像
        size = (1000, 1000)
        nir = np.random.rand(*size) * 0.8 + 0.2
        red = np.random.rand(*size) * 0.5
        green = np.random.rand(*size) * 0.6
        blue = np.random.rand(*size) * 0.4
        
        # 应该能够快速计算，不抛出异常
        ndvi = calculator.calculate_ndvi(nir, red)
        savi = calculator.calculate_savi(nir, red)
        evi = calculator.calculate_evi(nir, red, blue)
        vgi = calculator.calculate_vgi(green, red)
        
        assert ndvi.shape == size
        assert savi.shape == size
        assert evi.shape == size
        assert vgi.shape == size
