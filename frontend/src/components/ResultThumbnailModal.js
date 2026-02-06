import React, { useState, useEffect } from 'react';
import { Modal, Spin, Alert, Tabs, Image, Descriptions, Tag } from 'antd';
import axios from 'axios';

const { TabPane } = Tabs;

const ResultThumbnailModal = ({ visible, onClose, task }) => {
  const [loading, setLoading] = useState(false);
  const [thumbnails, setThumbnails] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    if (visible && task?.result?.output_files) {
      loadThumbnails();
    }
  }, [visible, task]);

  const loadThumbnails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const thumbnailData = {};
      
      // 为每个输出文件生成缩略图URL
      for (const file of task.result.output_files) {
        // 使用COG的预览功能或直接使用下载URL
        // 这里我们使用一个简化的方法：直接使用S3预签名URL
        thumbnailData[file.index] = {
          url: file.download_url,
          name: file.name,
          size: file.size_mb,
          s3_key: file.s3_key,
        };
      }
      
      setThumbnails(thumbnailData);
    } catch (err) {
      console.error('加载缩略图失败:', err);
      setError('加载缩略图失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const getIndexColor = (index) => {
    const colors = {
      NDVI: 'green',
      SAVI: 'blue',
      EVI: 'purple',
      VGI: 'orange',
    };
    return colors[index] || 'default';
  };

  const getIndexDescription = (index) => {
    const descriptions = {
      NDVI: '归一化植被指数 - 用于评估植被健康状况',
      SAVI: '土壤调节植被指数 - 减少土壤背景影响',
      EVI: '增强植被指数 - 对高生物量区域更敏感',
      VGI: '植被绿度指数 - 评估植被绿度',
    };
    return descriptions[index] || '';
  };

  return (
    <Modal
      title="处理结果预览"
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
      destroyOnClose
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" tip="加载缩略图中..." />
        </div>
      ) : error ? (
        <Alert message="错误" description={error} type="error" showIcon />
      ) : (
        <>
          <Descriptions bordered size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="任务ID">{task?.task_id}</Descriptions.Item>
            <Descriptions.Item label="任务类型">
              <Tag color="blue">{task?.task_type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color="success">已完成</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={3}>
              {task?.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间" span={3}>
              {task?.completed_at ? new Date(task.completed_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
          </Descriptions>

          <Tabs defaultActiveKey="0">
            {Object.entries(thumbnails).map(([index, data], idx) => (
              <TabPane
                tab={
                  <span>
                    <Tag color={getIndexColor(index)}>{index}</Tag>
                    {data.name}
                  </span>
                }
                key={idx}
              >
                <div style={{ padding: '16px 0' }}>
                  <Alert
                    message={getIndexDescription(index)}
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Descriptions bordered size="small" style={{ marginBottom: 16 }}>
                    <Descriptions.Item label="文件名">{data.name}</Descriptions.Item>
                    <Descriptions.Item label="大小">{data.size} MB</Descriptions.Item>
                    <Descriptions.Item label="S3路径" span={2}>
                      <code style={{ fontSize: '12px' }}>{data.s3_key}</code>
                    </Descriptions.Item>
                  </Descriptions>

                  <div style={{ textAlign: 'center', marginTop: 16 }}>
                    <Alert
                      message="缩略图预览"
                      description="由于GeoTIFF文件格式特殊，这里显示的是下载链接。点击下载后可使用QGIS等GIS软件查看完整数据。"
                      type="warning"
                      showIcon
                      style={{ marginBottom: 16, textAlign: 'left' }}
                    />
                    <a
                      href={data.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-block',
                        padding: '12px 24px',
                        background: '#1890ff',
                        color: 'white',
                        borderRadius: '4px',
                        textDecoration: 'none',
                      }}
                    >
                      下载 {index} 结果文件
                    </a>
                  </div>
                </div>
              </TabPane>
            ))}
          </Tabs>
        </>
      )}
    </Modal>
  );
};

export default ResultThumbnailModal;
