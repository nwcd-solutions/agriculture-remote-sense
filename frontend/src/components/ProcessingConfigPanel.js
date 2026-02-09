import React, { useState } from 'react';
import { Card, Checkbox, Button, Space, Form, Progress, Alert, Typography, Divider, Tag, Switch, Radio } from 'antd';
import { ThunderboltOutlined, CheckCircleOutlined, CloseCircleOutlined, StopOutlined, SyncOutlined, EyeOutlined } from '@ant-design/icons';
import ResultThumbnailModal from './ResultThumbnailModal';
import './ProcessingConfigPanel.css';

const { Text, Link } = Typography;

/**
 * 处理配置面板组件
 *
 * 支持两种处理模式：
 * 1. 植被指数计算 — 对单张影像计算 NDVI/SAVI/EVI/VGI
 * 2. 时间合成 — 对查询结果中的多张影像按月度合成
 */
const ProcessingConfigPanel = ({
  availableIndices = ['NDVI', 'SAVI', 'EVI', 'VGI'],
  onProcess,
  onComposite,
  selectedImage = null,
  queryResults = [],
  processingTask = null,
  disabled = false,
  onCancelTask,
  onRefreshTask,
  aoi = null,
  satelliteType = 'sentinel-2',
  selectedImages = [], // 新增：选中的影像ID数组
}) => {
  const [form] = Form.useForm();
  const [selectedIndices, setSelectedIndices] = useState(['NDVI']);
  const [processingMode, setProcessingMode] = useState('indices'); // 'indices' | 'composite'
  const [compositeMode, setCompositeMode] = useState('monthly');
  const [applyCloudMask, setApplyCloudMask] = useState(true);
  const [thumbnailModalVisible, setThumbnailModalVisible] = useState(false);

  const indicesInfo = {
    NDVI: { name: 'NDVI', fullName: '归一化植被指数', description: '最常用的植被指数，评估植被健康状况' },
    SAVI: { name: 'SAVI', fullName: '土壤调节植被指数', description: '考虑土壤背景影响，L=0.5' },
    EVI:  { name: 'EVI',  fullName: '增强植被指数',     description: '减少大气和土壤影响' },
    VGI:  { name: 'VGI',  fullName: '可见光植被指数',   description: '基于可见光波段的简单指数' },
  };

  // 是否为光学卫星（支持云掩膜）
  const isOpticalSatellite = ['sentinel-2', 'landsat-8'].includes(satelliteType);

  // 提交植被指数处理
  const handleSubmitIndices = () => {
    if (!selectedImage || selectedIndices.length === 0) return;
    if (onProcess) {
      onProcess({ image: selectedImage, indices: selectedIndices });
    }
  };

  // 提交批量植被指数处理
  const handleSubmitBatchIndices = () => {
    if (!selectedImages || selectedImages.length === 0 || selectedIndices.length === 0) return;
    
    // 获取选中的影像对象
    const images = queryResults.filter(img => selectedImages.includes(img.id));
    
    if (onProcess) {
      onProcess({ images, indices: selectedIndices });
    }
  };

  // 提交时间合成
  const handleSubmitComposite = () => {
    if (!queryResults || queryResults.length === 0) return;
    if (!aoi) return;
    if (onComposite) {
      onComposite({
        results: queryResults,
        compositeMode,
        applyCloudMask: isOpticalSatellite ? applyCloudMask : false,
        satellite: satelliteType,
        indices: selectedIndices,
        aoi,
      });
    }
  };

  const handleSubmit = () => {
    if (processingMode === 'indices') {
      handleSubmitIndices();
    } else {
      handleSubmitComposite();
    }
  };

  // --- Task status helpers (unchanged) ---
  const getTaskProgress = () => processingTask?.progress || 0;
  const getTaskStatusText = () => {
    if (!processingTask) return '';
    const map = { queued: '任务已创建，等待处理...', running: '正在处理中...', completed: '处理完成！', failed: '处理失败' };
    return map[processingTask.status] || '';
  };
  const getBatchStatusText = () => {
    if (!processingTask?.batch_job_status) return '';
    const map = { SUBMITTED: '已提交', PENDING: '等待中', RUNNABLE: '可运行', STARTING: '启动中', RUNNING: '运行中', SUCCEEDED: '成功', FAILED: '失败' };
    return map[processingTask.batch_job_status] || processingTask.batch_job_status;
  };
  const getBatchStatusColor = () => {
    if (!processingTask?.batch_job_status) return 'default';
    const map = { SUBMITTED: 'blue', PENDING: 'blue', RUNNABLE: 'cyan', STARTING: 'processing', RUNNING: 'processing', SUCCEEDED: 'success', FAILED: 'error' };
    return map[processingTask.batch_job_status] || 'default';
  };
  const getProgressStatus = () => {
    if (!processingTask) return 'normal';
    const map = { completed: 'success', failed: 'exception', running: 'active' };
    return map[processingTask.status] || 'normal';
  };
  const canCancelTask = () => processingTask && ['queued', 'running'].includes(processingTask.status);
  const isTaskActive = () => processingTask && ['queued', 'running'].includes(processingTask.status);

  // 提交按钮是否可用
  const canSubmit = () => {
    if (disabled || isTaskActive()) return false;
    if (processingMode === 'indices') {
      return selectedImage && selectedIndices.length > 0;
    }
    return queryResults.length > 0 && aoi;
  };

  return (
    <Card
      title="数据处理"
      className="processing-config-panel"
      bordered={false}
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit}>

        {/* 处理模式切换 */}
        <Form.Item label="处理模式">
          <Radio.Group
            value={processingMode}
            onChange={(e) => setProcessingMode(e.target.value)}
            disabled={disabled || isTaskActive()}
            buttonStyle="solid"
            size="small"
          >
            <Radio.Button value="indices">植被指数</Radio.Button>
            <Radio.Button value="composite">时间合成</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {/* ========== 植被指数模式 ========== */}
        {processingMode === 'indices' && (
          <>
            {selectedImage ? (
              <Alert
                message="已选择影像"
                description={
                  <div>
                    <Text ellipsis style={{ maxWidth: '100%', display: 'block' }}>{selectedImage.id}</Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>{selectedImage.satellite} - {selectedImage.product_level}</Text>
                  </div>
                }
                type="info" showIcon style={{ marginBottom: 16 }}
              />
            ) : (
              <Alert message="请先选择影像" description="在查询结果中点击影像以选择" type="warning" showIcon style={{ marginBottom: 16 }} />
            )}

            <Form.Item label="选择植被指数">
              <Checkbox.Group
                value={selectedIndices}
                onChange={(v) => setSelectedIndices(v)}
                style={{ width: '100%' }}
                disabled={disabled || !selectedImage}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  {availableIndices.map(idx => (
                    <div key={idx} className="index-option">
                      <Checkbox value={idx}>
                        <div className="index-info">
                          <Text strong>{indicesInfo[idx]?.name}</Text>
                          <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>{indicesInfo[idx]?.fullName}</Text>
                          <Text type="secondary" style={{ fontSize: '11px', display: 'block', marginTop: 2 }}>{indicesInfo[idx]?.description}</Text>
                        </div>
                      </Checkbox>
                    </div>
                  ))}
                </Space>
              </Checkbox.Group>
            </Form.Item>
          </>
        )}

        {/* ========== 时间合成模式 ========== */}
        {processingMode === 'composite' && (
          <>
            <Alert
              message={`查询结果: ${queryResults.length} 张影像`}
              description={queryResults.length > 0
                ? '将对查询结果中的所有影像进行时间合成'
                : '请先执行数据查询获取影像列表'}
              type={queryResults.length > 0 ? 'info' : 'warning'}
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item label="合成周期">
              <Radio.Group
                value={compositeMode}
                onChange={(e) => setCompositeMode(e.target.value)}
                disabled={disabled}
              >
                <Radio value="monthly">月度合成</Radio>
              </Radio.Group>
            </Form.Item>

            {isOpticalSatellite && (
              <Form.Item label="云掩膜">
                <Space>
                  <Switch
                    checked={applyCloudMask}
                    onChange={(v) => setApplyCloudMask(v)}
                    disabled={disabled}
                  />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {applyCloudMask ? '合成前去除云覆盖像素' : '不应用云掩膜'}
                  </Text>
                </Space>
              </Form.Item>
            )}
          </>
        )}

        <Divider style={{ margin: '8px 0 16px' }} />

        {/* 提交按钮 */}
        <Form.Item>
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={handleSubmit}
              disabled={!canSubmit()}
              loading={isTaskActive()}
              block
            >
              {isTaskActive()
                ? '处理中...'
                : processingMode === 'indices' ? '计算植被指数' : '开始时间合成'}
            </Button>
            
            {/* 批量处理按钮 - 仅在植被指数模式且有选中影像时显示 */}
            {processingMode === 'indices' && selectedImages && selectedImages.length > 0 && (
              <Button
                type="default"
                icon={<ThunderboltOutlined />}
                onClick={handleSubmitBatchIndices}
                disabled={disabled || isTaskActive() || selectedIndices.length === 0}
                loading={isTaskActive()}
                block
              >
                批量计算 ({selectedImages.length} 个影像)
              </Button>
            )}
          </Space>
        </Form.Item>

        {/* ========== 任务进度 ========== */}
        {processingTask && (
          <div className="task-progress">
            <Divider style={{ margin: '12px 0' }} />
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div className="task-ids">
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary" style={{ fontSize: '12px' }}>任务 ID: </Text>
                    <Text code style={{ fontSize: '11px' }}>{processingTask.task_id}</Text>
                  </div>
                  {processingTask.batch_job_id && (
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>Batch Job: </Text>
                      <Text code style={{ fontSize: '11px' }}>{processingTask.batch_job_id}</Text>
                    </div>
                  )}
                  {processingTask.task_type === 'composite' && (
                    <div>
                      <Tag color="purple">时间合成</Tag>
                    </div>
                  )}
                </Space>
              </div>

              <div className="task-status">
                <Space>
                  {processingTask.status === 'completed' && <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />}
                  {processingTask.status === 'failed' && <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />}
                  {isTaskActive() && <SyncOutlined spin style={{ color: '#1890ff', fontSize: 16 }} />}
                  <Text strong>{getTaskStatusText()}</Text>
                  {processingTask.batch_job_status && <Tag color={getBatchStatusColor()}>{getBatchStatusText()}</Tag>}
                </Space>
              </div>

              <Progress percent={getTaskProgress()} status={getProgressStatus()} strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }} />

              <Space style={{ width: '100%' }}>
                {canCancelTask() && (
                  <Button danger size="small" icon={<StopOutlined />} onClick={() => onCancelTask?.(processingTask.task_id)}>取消任务</Button>
                )}
                <Button size="small" icon={<SyncOutlined />} onClick={() => onRefreshTask?.(processingTask.task_id)} disabled={!processingTask.task_id}>刷新状态</Button>
              </Space>

              {processingTask.status === 'failed' && processingTask.error && (
                <Alert message="错误信息" description={processingTask.error} type="error" showIcon closable />
              )}

              {processingTask.status === 'completed' && processingTask.result && (
                <Alert
                  message="处理完成"
                  description={
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text>已生成 {processingTask.result.output_files?.length || 0} 个文件</Text>
                      {processingTask.result.output_files?.map((file, i) => (
                        <div key={i} style={{ marginTop: 8 }}>
                          <Space>
                            <Text strong>{file.index || file.name}</Text>
                            <Text type="secondary">({file.size_mb} MB)</Text>
                            {file.download_url && <Link href={file.download_url} target="_blank" download>下载</Link>}
                          </Space>
                        </div>
                      ))}
                      <Button
                        type="primary"
                        icon={<EyeOutlined />}
                        onClick={() => setThumbnailModalVisible(true)}
                        style={{ marginTop: 8 }}
                        block
                      >
                        查看结果
                      </Button>
                    </Space>
                  }
                  type="success" showIcon
                />
              )}
            </Space>
          </div>
        )}
      </Form>

      {/* 结果缩略图模态框 */}
      <ResultThumbnailModal
        visible={thumbnailModalVisible}
        onClose={() => setThumbnailModalVisible(false)}
        task={processingTask}
      />
    </Card>
  );
};

export default ProcessingConfigPanel;
