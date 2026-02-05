import React, { useState } from 'react';
import { Card, Select, DatePicker, Slider, Button, Space, Form, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import './DataQueryPanel.css';

const { RangePicker } = DatePicker;

/**
 * 数据查询面板组件 - 数据查询和过滤界面
 * 
 * 属性：
 * - satellites: 可用卫星列表
 * - onQuery: 查询提交回调函数
 * - aoi: 当前选中的 AOI (GeoJSON)
 * - loading: 查询加载状态
 */
const DataQueryPanel = ({ 
  satellites = ['sentinel-2'], 
  onQuery,
  aoi = null,
  loading = false 
}) => {
  const [form] = Form.useForm();
  const [satelliteType, setSatelliteType] = useState('sentinel-2');
  const [dateRange, setDateRange] = useState([
    dayjs().subtract(3, 'month'),
    dayjs()
  ]);
  const [cloudCover, setCloudCover] = useState(20);

  // 处理查询提交
  const handleSubmit = () => {
    if (!aoi) {
      message.warning('请先在地图上绘制或上传 AOI');
      return;
    }

    const queryParams = {
      satellite: satelliteType,
      product_level: 'L2A', // 初期只支持 Sentinel-2 L2A
      date_range: {
        start: dateRange[0].format('YYYY-MM-DD'),
        end: dateRange[1].format('YYYY-MM-DD')
      },
      aoi: aoi,
      cloud_cover_max: cloudCover
    };

    if (onQuery) {
      onQuery(queryParams);
    }
  };

  // 处理卫星类型变化
  const handleSatelliteChange = (value) => {
    setSatelliteType(value);
  };

  // 处理日期范围变化
  const handleDateRangeChange = (dates) => {
    if (dates && dates.length === 2) {
      setDateRange(dates);
    }
  };

  // 处理云量阈值变化
  const handleCloudCoverChange = (value) => {
    setCloudCover(value);
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
        <Form.Item 
          label="卫星类型"
          name="satellite"
          initialValue={satelliteType}
        >
          <Select
            value={satelliteType}
            onChange={handleSatelliteChange}
            placeholder="选择卫星类型"
            disabled={loading}
          >
            {satellites.map(sat => (
              <Select.Option key={sat} value={sat}>
                {sat === 'sentinel-2' ? 'Sentinel-2' : sat}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        {/* 日期范围选择器 */}
        <Form.Item 
          label="时间范围"
          name="dateRange"
          initialValue={dateRange}
        >
          <RangePicker
            value={dateRange}
            onChange={handleDateRangeChange}
            format="YYYY-MM-DD"
            style={{ width: '100%' }}
            disabled={loading}
            disabledDate={(current) => {
              // 禁用未来日期
              return current && current > dayjs().endOf('day');
            }}
          />
        </Form.Item>

        {/* 云量阈值滑块 */}
        <Form.Item 
          label={`云量阈值: ${cloudCover}%`}
          name="cloudCover"
          initialValue={cloudCover}
        >
          <Slider
            value={cloudCover}
            onChange={handleCloudCoverChange}
            min={0}
            max={100}
            step={5}
            marks={{
              0: '0%',
              50: '50%',
              100: '100%'
            }}
            disabled={loading}
          />
        </Form.Item>

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
