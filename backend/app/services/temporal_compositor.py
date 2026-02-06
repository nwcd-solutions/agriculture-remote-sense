"""
时间合成处理器

实现多时相卫星影像的时间合成功能，支持月度合成周期。
在合成前对光学数据应用云掩膜，然后计算时间维度上的均值。

需求: 7.1, 7.2, 9.4, 9.5
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

import numpy as np
import xarray as xr

logger = logging.getLogger(__name__)


class TemporalCompositor:
    """
    时间合成处理器

    将多张影像按时间周期分组，对每组计算像素级均值，
    输出每个周期一张合成影像。
    """

    def composite_monthly(
        self,
        images: List[xr.DataArray],
        timestamps: List[datetime],
    ) -> List[Tuple[str, xr.DataArray]]:
        """
        按月度周期合成影像。

        将 images 按 (year, month) 分组，对每组调用 _aggregate_mean。

        Args:
            images: 已裁剪到 AOI 的栅格数据列表（可含 NaN 表示被掩膜像素）
            timestamps: 与 images 一一对应的获取时间列表

        Returns:
            列表，每个元素为 (period_label, composite_data)，
            period_label 格式为 "YYYY-MM"，composite_data 为均值合成结果。
            按时间升序排列。

        Raises:
            ValueError: 如果 images 和 timestamps 长度不一致或为空
        """
        if len(images) != len(timestamps):
            raise ValueError(
                f"images ({len(images)}) and timestamps ({len(timestamps)}) must have the same length"
            )
        if not images:
            raise ValueError("images list must not be empty")

        # 按 (year, month) 分组
        groups: Dict[str, List[xr.DataArray]] = defaultdict(list)
        for img, ts in zip(images, timestamps):
            key = f"{ts.year:04d}-{ts.month:02d}"
            groups[key].append(img)

        # 按时间排序
        sorted_keys = sorted(groups.keys())

        results: List[Tuple[str, xr.DataArray]] = []
        for key in sorted_keys:
            group_images = groups[key]
            logger.info(
                f"Compositing period {key}: {len(group_images)} images"
            )
            composite = self._aggregate_mean(group_images)
            results.append((key, composite))

        logger.info(
            f"Monthly composite complete: {len(results)} periods from {len(images)} images"
        )
        return results

    @staticmethod
    def _aggregate_mean(images: List[xr.DataArray]) -> xr.DataArray:
        """
        计算影像列表在时间维度上的像素级均值。

        使用 nanmean 忽略 NaN 值（被云掩膜标记的像素），
        这样云覆盖的像素不会影响合成结果。

        如果某个像素在所有影像中都是 NaN，则结果也为 NaN。

        Args:
            images: 栅格数据列表，形状应一致

        Returns:
            xr.DataArray: 均值合成结果，保留第一张影像的空间元数据

        Raises:
            ValueError: 如果 images 为空
        """
        if not images:
            raise ValueError("Cannot aggregate empty image list")

        if len(images) == 1:
            return images[0].copy()

        # 将所有影像堆叠到一个新的 "time" 维度
        # 先确保所有数据都是 float 以支持 NaN
        float_images = [img.astype(np.float32) for img in images]
        stacked = xr.concat(float_images, dim="time")

        # 沿 time 维度计算 nanmean
        composite = stacked.mean(dim="time", skipna=True)

        # 保留第一张影像的空间元数据 (CRS, transform)
        ref = images[0]
        if hasattr(ref, "rio") and ref.rio.crs is not None:
            composite.rio.write_crs(ref.rio.crs, inplace=True)
            if ref.rio.transform() is not None:
                composite.rio.write_transform(ref.rio.transform(), inplace=True)
            if ref.rio.nodata is not None:
                composite.rio.write_nodata(ref.rio.nodata, inplace=True)

        return composite
