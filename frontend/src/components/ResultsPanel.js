import React, { useState, useMemo } from 'react';
import { Card, List, Image, Tag, Empty, Pagination, Select, Space, Typography, Spin, Button, Tooltip, message, Checkbox } from 'antd';
import { CalendarOutlined, CloudOutlined, EnvironmentOutlined, DownloadOutlined, FileOutlined, CloudDownloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import './ResultsPanel.css';

const { Text } = Typography;

/**
 * 结果展示面板组件 - 结果展示和下载管理
 * 
 * 属性：
 * - results: 查询结果数组
 * - tasks: 处理任务状态数组
 * - loading: 加载状态
 * - onImageSelect: 影像选择回调
 * - onDownload: 下载回调函数
 * - onDownloadToS3: 批量下载到S3回调函数
 * - selectedImageId: 当前选中的影像 ID
 * - selectedImages: 选中的影像ID数组
 * - onSelectionChange: 选择变化回调
 */
const ResultsPanel = ({ 
  results = [], 
  tasks = [],
  loading = false,
  onImageSelect,
  onDownload,
  onDownloadToS3,
  selectedImageId = null,
  selectedImages = [],
  onSelectionChange
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortOrder, setSortOrder] = useState('desc'); // 'asc' or 'desc'
  const [downloadingToS3, setDownloadingToS3] = useState(false);

  // 排序结果（按日期）
  const sortedResults = useMemo(() => {
    if (!results || results.length === 0) return [];
    
    return [...results].sort((a, b) => {
      const dateA = dayjs(a.datetime);
      const dateB = dayjs(b.datetime);
      
      if (sortOrder === 'desc') {
        return dateB.diff(dateA);
      } else {
        return dateA.diff(dateB);
      }
    });
  }, [results, sortOrder]);

  // 分页数据
  const paginatedResults = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return sortedResults.slice(startIndex, endIndex);
  }, [sortedResults, currentPage, pageSize]);

  // 处理页码变化
  const handlePageChange = (page, newPageSize) => {
    setCurrentPage(page);
    if (newPageSize !== pageSize) {
      setPageSize(newPageSize);
      setCurrentPage(1); // 重置到第一页
    }
  };

  // 处理排序变化
  const handleSortChange = (value) => {
    setSortOrder(value);
    setCurrentPage(1); // 重置到第一页
  };

  // 处理影像选择
  const handleImageClick = (item) => {
    if (onImageSelect) {
      onImageSelect(item);
    }
  };

  // 格式化云量
  const formatCloudCover = (cloudCover) => {
    if (cloudCover === null || cloudCover === undefined) {
      return 'N/A';
    }
    return `${cloudCover.toFixed(1)}%`;
  };

  // 格式化日期
  const formatDate = (datetime) => {
    return dayjs(datetime).format('YYYY-MM-DD HH:mm');
  };

  // 获取卫星显示名称
  const getSatelliteName = (satellite) => {
    const nameMap = {
      'sentinel-2': 'Sentinel-2',
      'sentinel-1': 'Sentinel-1',
      'landsat-8': 'Landsat 8',
      'modis': 'MODIS'
    };
    return nameMap[satellite] || satellite;
  };

  // 处理下载
  const handleDownload = (item, e) => {
    e.stopPropagation(); // 防止触发影像选择
    
    if (onDownload) {
      onDownload(item);
    } else {
      message.info('下载功能将在后续实现');
    }
  };

  // 处理复选框变化
  const handleCheckboxChange = (imageId, checked, e) => {
    e.stopPropagation(); // 防止触发影像选择
    
    let newSelection;
    if (checked) {
      newSelection = [...selectedImages, imageId];
    } else {
      newSelection = selectedImages.filter(id => id !== imageId);
    }
    
    if (onSelectionChange) {
      onSelectionChange(newSelection);
    }
  };

  // 全选/取消全选
  const handleSelectAll = (checked) => {
    if (checked) {
      const allIds = sortedResults.map(item => item.id);
      if (onSelectionChange) {
        onSelectionChange(allIds);
      }
    } else {
      if (onSelectionChange) {
        onSelectionChange([]);
      }
    }
  };

  // 是否全选
  const isAllSelected = sortedResults.length > 0 && selectedImages.length === sortedResults.length;
  const isIndeterminate = selectedImages.length > 0 && selectedImages.length < sortedResults.length;

  // 处理批量下载到S3
  const handleDownloadToS3 = async () => {
    if (selectedImages.length === 0) {
      message.warning('请先选择要下载的影像');
      return;
    }

    setDownloadingToS3(true);
    try {
      const selectedResults = results.filter(r => selectedImages.includes(r.id));
      if (onDownloadToS3) {
        await onDownloadToS3(selectedResults);
      }
    } catch (error) {
      console.error('下载到S3失败:', error);
      message.error('下载到S3失败');
    } finally {
      setDownloadingToS3(false);
    }
  };

  // 格式化文件大小
  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  // 获取文件格式信息
  const getFileFormatInfo = (item) => {
    // 从 assets 中获取文件信息
    if (item.assets) {
      const assetKeys = Object.keys(item.assets);
      const formats = new Set();
      let totalSize = 0;
      
      assetKeys.forEach(key => {
        const asset = item.assets[key];
        if (asset.type) {
          formats.add(asset.type.split('/')[1]?.toUpperCase() || 'Unknown');
        }
        if (asset.file_size) {
          totalSize += asset.file_size;
        }
      });
      
      return {
        formats: Array.from(formats).join(', ') || 'COG',
        size: totalSize || null
      };
    }
    
    return {
      formats: 'COG',
      size: null
    };
  };

  return (
    <Card 
      title={
        <Space>
          <span>查询结果</span>
          {results.length > 0 && (
            <>
              <Tag color="blue">{results.length} 个影像</Tag>
              {selectedImages.length > 0 && (
                <Tag color="green">已选 {selectedImages.length} 个</Tag>
              )}
            </>
          )}
        </Space>
      }
      className="results-panel"
      bordered={false}
      extra={
        results.length > 0 && (
          <Space>
            <Checkbox
              checked={isAllSelected}
              indeterminate={isIndeterminate}
              onChange={(e) => handleSelectAll(e.target.checked)}
            >
              全选
            </Checkbox>
            <Select
              value={sortOrder}
              onChange={handleSortChange}
              style={{ width: 120 }}
              size="small"
            >
              <Select.Option value="desc">最新优先</Select.Option>
              <Select.Option value="asc">最早优先</Select.Option>
            </Select>
          </Space>
        )
      }
    >
      {loading ? (
        <div className="results-loading">
          <Spin size="large" tip="查询中..." />
        </div>
      ) : results.length === 0 ? (
        <Empty
          description="暂无查询结果"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <>
          <List
            className="results-list"
            dataSource={paginatedResults}
            renderItem={(item) => {
              const fileInfo = getFileFormatInfo(item);
              const isSelected = selectedImageId === item.id;
              const isChecked = selectedImages.includes(item.id);
              
              return (
                <List.Item
                  key={item.id}
                  className={`result-item ${isSelected ? 'result-item-selected' : ''}`}
                  onClick={() => handleImageClick(item)}
                >
                  <div className="result-content">
                    {/* 复选框 */}
                    <div className="result-checkbox">
                      <Checkbox
                        checked={isChecked}
                        onChange={(e) => handleCheckboxChange(item.id, e.target.checked, e)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>

                    {/* 缩略图 */}
                    <div className="result-thumbnail">
                      {item.thumbnail_url ? (
                        <Image
                          src={item.thumbnail_url}
                          alt={item.id}
                          width={100}
                          height={100}
                          preview={false}
                          fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                        />
                      ) : (
                        <div className="thumbnail-placeholder">
                          <EnvironmentOutlined style={{ fontSize: 32, color: '#bfbfbf' }} />
                        </div>
                      )}
                    </div>

                    {/* 影像信息 */}
                    <div className="result-info">
                      <div className="result-header">
                        <Text strong ellipsis style={{ maxWidth: '200px' }}>
                          {item.id}
                        </Text>
                        <Space size="small">
                          <Tag color="green">
                            {getSatelliteName(item.satellite)}
                          </Tag>
                          {item.product_level && (
                            <Tag color="blue">{item.product_level}</Tag>
                          )}
                        </Space>
                      </div>

                      <div className="result-details">
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <Text type="secondary">
                            <CalendarOutlined /> {formatDate(item.datetime)}
                          </Text>
                          {item.cloud_cover !== null && item.cloud_cover !== undefined && (
                            <Text type="secondary">
                              <CloudOutlined /> 云量: {formatCloudCover(item.cloud_cover)}
                            </Text>
                          )}
                          <Text type="secondary">
                            <FileOutlined /> 格式: {fileInfo.formats}
                            {fileInfo.size && ` (${formatFileSize(fileInfo.size)})`}
                          </Text>
                        </Space>
                      </div>

                      {/* 下载按钮 */}
                      <div className="result-actions">
                        <Tooltip title="下载影像">
                          <Button
                            type="primary"
                            size="small"
                            icon={<DownloadOutlined />}
                            onClick={(e) => handleDownload(item, e)}
                          >
                            下载
                          </Button>
                        </Tooltip>
                      </div>
                    </div>
                  </div>
                </List.Item>
              );
            }}
          />

          {/* 分页 */}
          {sortedResults.length > pageSize && (
            <div className="results-pagination">
              <Pagination
                current={currentPage}
                pageSize={pageSize}
                total={sortedResults.length}
                onChange={handlePageChange}
                showSizeChanger
                showQuickJumper
                showTotal={(total) => `共 ${total} 个影像`}
                pageSizeOptions={['10', '20', '50', '100']}
              />
            </div>
          )}

          {/* 批量操作按钮 */}
          {selectedImages.length > 0 && (
            <div className="results-batch-actions" style={{ marginTop: 16, textAlign: 'center' }}>
              <Button
                type="primary"
                icon={<CloudDownloadOutlined />}
                onClick={handleDownloadToS3}
                loading={downloadingToS3}
                size="large"
              >
                下载到 S3 ({selectedImages.length} 个影像)
              </Button>
            </div>
          )}
        </>
      )}
    </Card>
  );
};

export default ResultsPanel;
