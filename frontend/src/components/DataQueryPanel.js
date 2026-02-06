import React, { useState, useMemo } from 'react';
import { Card, Select, DatePicker, Slider, Button, Space, Form, message, Divider } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import './DataQueryPanel.css';

const { RangePicker } = DatePicker;

/**
 * 卫星类型配置 — 每种卫星的产品级别、是否支持云量过滤、极化选项等
 */
const SATELLITE_CONFIG = {
  'sentinel-2': {
    label: 'Sentinel-2 (光学)',
    productLevels: [
      { value: 'L2A', label: 'L2A - 地表反射率' },
      { value: 'L1C', label: 'L1C - 大气顶层反射率' },
    ],
    defaultProductLevel: 'L2A',
    hasCloudCover: true,
    hasPolarization: false,
  },
  'sentinel-1': {
    label: 'Sentinel-1 (SAR)',
    productLevels: [
      { value: 'GRD', label: 'GRD - 地距检测' },
      { value: 'RTC', label: 'RTC - 辐射地形校正' },
    ],
    defaultProductLevel: 'GRD',
    hasCloudCover: false,
    hasPolarization: true,
    polarizationOptions: [
      { value: 'VV', label: 'VV' },
      { value: 'VH', label: 'VH' },
      { value: 'VV+VH', label: 'VV+VH (双极化)' },
    ],
  },
  'landsat-8': {
    label: 'Landsat 8 (光学)',
    productLevels: [
      { value: 'L2', label: 'L2 - Collection 2 Level-2' },
      { value: 'L1', label: 'L1 - Collection 2 Level-1' },
    ],
    defaultProductLevel: 'L2',
    hasCloudCover: true,
    hasPolarization: false,
  },
  'modis': {
    label: 'MODIS',
    productLevels: [
      { value: 'MCD43A4', label: 'MCD43A4 - BRDF 反射率 (Combined)' },
      { value: 'MOD09A1', label: 'MOD09A1 - 反射率 (Terra)' },
      { value: 'MYD09A1', label: 'MYD09A1 - 反射率 (Aqua)' },
      { value: 'MOD13A1', label: 'MOD13A1 - 植被指数 (Terra)' },
      { value: 'MYD13A1', label: 'MYD13A1 - 植被指数 (Aqua)' },
      { value: 'MOD11A1', label: 'MOD11A1 - 地表温度 (Terra)' },
      { value: 'MYD11A1', label: 'MYD11A1 - 地表温度 (Aqua)' },
    ],
    defaultProductLevel: 'MCD43A4',
    hasCloudCover: false,
    hasPolarization: false,
  },
};

/**
 * 数据查询面板组件 - 支持多卫星类型查询
 * 
 * 属性：
 * - satellites: 可用卫星列表
 * - onQuery: 查询提交回调函数
 * - aoi: 当前选中的 AOI (GeoJSON)
 * - loading: 查询加载状态
 */
const DataQueryPanel = ({ 
  satellites = ['sentinel-2', 'sentinel-1', 'landsat-8', 'modis'], 
  onQuery,
  aoi = null,
  loading = false 
}) => {
  const [form] = Form.useForm();
  const [satelliteType, setSatelliteType] = useState('sentinel-2');
  const [productLevel, setProductLevel] = useState('L2A');
  const [dateRange, setDateRange] = useState([
    dayjs().subtract(3, 'month'),
    dayjs()
  ]);
  const [cloudCover, setCloudCover] = useState(20);
  const [polarization, setPolarization] = useState(null);

  // 当前卫星的配置
  const currentConfig = useMemo(() => {
    return SATELLITE_CONFIG[satelliteType] || SATELLITE_CONFIG['sentinel-2'];
  }, [satelliteType]);

  // 处理查询提交
  const handleSubmit = () => {
    if (!aoi) {
      message.warning('请先在地图上绘制或上传 AOI');
      return;
    }

    const queryParams = {
      satellite: satelliteType,
      product_level: productLevel,
      date_range: {
        start: dateRange[0].format('YYYY-MM-DD'),
        end: dateRange[1].format('YYYY-MM-DD')
      },
      aoi: aoi,
    };

    // 光学卫星才传云量参数
    if (currentConfig.hasCloudCover) {
      queryParams.cloud_cover_max = cloudCover;
    }

    // Sentinel-1 传极化参数
    if (currentConfig.hasPolarization && polarization) {
      queryParams.polarization = polarization === 'VV+VH' ? ['VV', 'VH'] : [polarization];
    }

    if (onQuery) {
      onQuery(queryParams);
    }
  };

  // 处理卫星类型变化 — 重置产品级别和极化
  const handleSatelliteChange = (value) => {
    setSatelliteType(value);
    const config = SATELLITE_CONFIG[value];
    if (config) {
      setProductLevel(config.defaultProductLevel);
      setPolarization(null);
    }
  };

  return (
    <Card 
      title="数据查询" 
      className="data-query-panel"
      bordered={false}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {/* 卫星类型选择 */}
        <Form.Item label="卫星类型">
          <Select
            value={satelliteType}
            onChange={handleSatelliteChange}
            placeholder="选择卫星类型"
            disabled={loading}
          >
            {satellites.map(sat => (
              <Select.Option key={sat} value={sat}>
                {SATELLITE_CONFIG[sat]?.label || sat}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        {/* 产品级别选择 — 根据卫星类型动态显示 */}
        <Form.Item label="产品级别">
          <Select
            value={productLevel}
            onChange={(value) => setProductLevel(value)}
            placeholder="选择产品级别"
            disabled={loading}
          >
            {currentConfig.productLevels.map(pl => (
              <Select.Option key={pl.value} value={pl.value}>
                {pl.label}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        {/* Sentinel-1 极化选择 */}
        {currentConfig.hasPolarization && (
          <Form.Item label="极化方式">
            <Select
              value={polarization}
              onChange={(value) => setPolarization(value)}
              placeholder="选择极化方式（可选）"
              allowClear
              disabled={loading}
            >
              {currentConfig.polarizationOptions.map(opt => (
                <Select.Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        )}

        <Divider style={{ margin: '12px 0' }} />

        {/* 日期范围选择器 */}
        <Form.Item label="时间范围">
          <RangePicker
            value={dateRange}
            onChange={(dates) => { if (dates && dates.length === 2) setDateRange(dates); }}
            format="YYYY-MM-DD"
            style={{ width: '100%' }}
            disabled={loading}
            disabledDate={(current) => current && current > dayjs().endOf('day')}
          />
        </Form.Item>

        {/* 云量阈值滑块 — 仅光学卫星显示 */}
        {currentConfig.hasCloudCover && (
          <Form.Item label={`云量阈值: ${cloudCover}%`}>
            <Slider
              value={cloudCover}
              onChange={(value) => setCloudCover(value)}
              min={0}
              max={100}
              step={5}
              marks={{ 0: '0%', 50: '50%', 100: '100%' }}
              disabled={loading}
            />
          </Form.Item>
        )}

        {/* 查询提交按钮 */}
        <Form.Item>
          <Space style={{ width: '100%' }}>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSubmit}
              loading={loading}
              disabled={!aoi}
              block
            >
              {loading ? '查询中...' : '查询数据'}
            </Button>
          </Space>
        </Form.Item>

        {/* AOI 状态提示 */}
        {!aoi && (
          <div className="aoi-hint">
            <small style={{ color: '#8c8c8c' }}>
              💡 请先在地图上绘制 AOI 或上传 GeoJSON/Shapefile
            </small>
          </div>
        )}
      </Form>
    </Card>
  );
};

export default DataQueryPanel;
