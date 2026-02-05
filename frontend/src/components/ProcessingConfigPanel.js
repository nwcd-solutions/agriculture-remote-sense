import React, { useState, useEffect } from 'react';
import { Card, Checkbox, Button, Space, Form, Progress, Alert, Typography, Divider, Tag, Tooltip } from 'antd';
import { ThunderboltOutlined, CheckCircleOutlined, CloseCircleOutlined, StopOutlined, SyncOutlined } from '@ant-design/icons';
import './ProcessingConfigPanel.css';

const { Text, Link } = Typography;

/**
 * 处理配置面板组件 - 处理参数配置
 * 
 * 属性：
 * - availableIndices: 可用植被指数列表
 * - onProcess: 处理提交回调函数
 * - selectedImage: 当前选中的影像
 * - processingTask: 当前处理任务状态
 * - disabled: 是否禁用
 * - onCancelTask: 取消任务回调函数
 * - onRefreshTask: 刷新任务状态回调函数
 */
const ProcessingConfigPanel = ({ 
  availableIndices = ['NDVI', 'SAVI', 'EVI', 'VGI'],
  onProcess,
  selectedImage = null,
  processingTask = null,
  disabled = false,
  onCancelTask,
  onRefreshTask
}) => {
  const [form] = Form.useForm();
  const [selectedIndices, setSelectedIndices] = useState(['NDVI']);

  // 植被指数信息
  const indicesInfo = {
    NDVI: {
      name: 'NDVI',
      fullName: '归一化植被指数',
      formula: '(NIR - Red) / (NIR + Red)',
      description: '最常用的植被指数，用于评估植被健康状况'
    },
    SAVI: {
      name: 'SAVI',
      fullName: '土壤调节植被指数',
      formula: '(1 + L) * (NIR - Red) / (NIR + Red + L)',
      description: '考虑土壤背景影响的植被指数，L=0.5'
    },
    EVI: {
      name: 'EVI',
      fullName: '增强植被指数',
      formula: '2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)',
      description: '改进的植被指数，减少大气和土壤影响'
    },
    VGI: {
      name: 'VGI',
      fullName: '可见光植被指数',
      formula: 'Green / Red',
      description: '基于可见光波段的简单植被指数'
    }
  };

  // 处理指数选择变化
  const handleIndicesChange = (checkedValues) => {
    setSelectedIndices(checkedValues);
  };

  // 处理提交
  const handleSubmit = () => {
    if (!selectedImage) {
      return;
    }

    if (selectedIndices.length === 0) {
      return;
    }

    if (onProcess) {
      onProcess({
        image: selectedImage,
        indices: selectedIndices
      });
    }
  };

  // 获取任务进度
  const getTaskProgress = () => {
    if (!processingTask) return 0;
    return processingTask.progress || 0;
  };

  // 获取任务状态文本
  const getTaskStatusText = () => {
    if (!processingTask) return '';
    
    switch (processingTask.status) {
      case 'queued':
        return '任务已创建，等待处理...';
      case 'running':
        return '正在处理中...';
      case 'completed':
        return '处理完成！';
      case 'failed':
        return '处理失败';
      default:
        return '';
    }
  };

  // 获取 Batch 状态文本
  const getBatchStatusText = () => {
    if (!processingTask || !processingTask.batch_job_status) return '';
    
    const statusMap = {
      'SUBMITTED': '已提交',
      'PENDING': '等待中',
      'RUNNABLE': '可运行',
      'STARTING': '启动中',
      'RUNNING': '运行中',
      'SUCCEEDED': '成功',
      'FAILED': '失败'
    };
    
    return statusMap[processingTask.batch_job_status] || processingTask.batch_job_status;
  };

  // 获取 Batch 状态颜色
  const getBatchStatusColor = () => {
    if (!processingTask || !processingTask.batch_job_status) return 'default';
    
    const colorMap = {
      'SUBMITTED': 'blue',
      'PENDING': 'blue',
      'RUNNABLE': 'cyan',
      'STARTING': 'processing',
      'RUNNING': 'processing',
      'SUCCEEDED': 'success',
      'FAILED': 'error'
    };
    
    return colorMap[processingTask.batch_job_status] || 'default';
  };

  // 获取进度条状态
  const getProgressStatus = () => {
    if (!processingTask) return 'normal';
    
    switch (processingTask.status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'exception';
      case 'running':
        return 'active';
      default:
        return 'normal';
    }
  };

  // 处理取消任务
  const handleCancelTask = () => {
    if (onCancelTask && processingTask) {
      onCancelTask(processingTask.task_id);
    }
  };

  // 处理刷新任务状态
  const handleRefreshTask = () => {
    if (onRefreshTask && processingTask) {
      onRefreshTask(processingTask.task_id);
    }
  };

  // 判断任务是否可以取消
  const canCancelTask = () => {
    if (!processingTask) return false;
    return processingTask.status === 'queued' || processingTask.status === 'running';
  };

  // 判断任务是否正在进行
  const isTaskActive = () => {
    if (!processingTask) return false;
    return processingTask.status === 'queued' || processingTask.status === 'running';
  };

  return (
    <Card 
      title="植被指数处理" 
      className="processing-config-panel"
      bordered={false}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {/* 选中影像信息 */}
        {selectedImage ? (
          <Alert
            message="已选择影像"
            description={
              <div>
                <Text ellipsis style={{ maxWidth: '100%', display: 'block' }}>
                  {selectedImage.id}
                </Text>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {selectedImage.satellite} - {selectedImage.product_level}
                </Text>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        ) : (
          <Alert
            message="请先选择影像"
            description="在查询结果中点击影像以选择"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 植被指数多选框 */}
        <Form.Item 
          label="选择植被指数"
          name="indices"
          initialValue={selectedIndices}
        >
          <Checkbox.Group
            value={selectedIndices}
            onChange={handleIndicesChange}
            style={{ width: '100%' }}
            disabled={disabled || !selectedImage}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {availableIndices.map(index => (
                <div key={index} className="index-option">
                  <Checkbox value={index}>
                    <div className="index-info">
                      <Text strong>{indicesInfo[index]?.name}</Text>
                      <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
                        {indicesInfo[index]?.fullName}
                      </Text>
                      <Text type="secondary" style={{ fontSize: '11px', display: 'block', marginTop: 4 }}>
                        {indicesInfo[index]?.description}
                      </Text>
                    </div>
                  </Checkbox>
                </div>
              ))}
            </Space>
          </Checkbox.Group>
        </Form.Item>

        {/* 处理提交按钮 */}
        <Form.Item>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleSubmit}
            disabled={disabled || !selectedImage || selectedIndices.length === 0 || isTaskActive()}
            loading={isTaskActive()}
            block
          >
            {isTaskActive() 
              ? '处理中...' 
              : '开始处理'}
          </Button>
        </Form.Item>

        {/* 任务进度条 */}
        {processingTask && (
          <div className="task-progress">
            <Divider style={{ margin: '12px 0' }} />
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* 任务 ID 和 Batch Job ID */}
              <div className="task-ids">
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary" style={{ fontSize: '12px' }}>任务 ID: </Text>
                    <Text code style={{ fontSize: '11px' }}>{processingTask.task_id}</Text>
                  </div>
                  {processingTask.batch_job_id && (
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>Batch Job ID: </Text>
                      <Text code style={{ fontSize: '11px' }}>{processingTask.batch_job_id}</Text>
                    </div>
                  )}
                </Space>
              </div>

              {/* 任务状态和 Batch 状态 */}
              <div className="task-status">
                <Space>
                  {processingTask.status === 'completed' && (
                    <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
                  )}
                  {processingTask.status === 'failed' && (
                    <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />
                  )}
                  {isTaskActive() && (
                    <SyncOutlined spin style={{ color: '#1890ff', fontSize: 16 }} />
                  )}
                  <Text strong>{getTaskStatusText()}</Text>
                  {processingTask.batch_job_status && (
                    <Tag color={getBatchStatusColor()}>
                      {getBatchStatusText()}
                    </Tag>
                  )}
                </Space>
              </div>
              
              {/* 进度条 */}
              <Progress 
                percent={getTaskProgress()} 
                status={getProgressStatus()}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />

              {/* 操作按钮 */}
              <Space style={{ width: '100%' }}>
                {canCancelTask() && (
                  <Button
                    danger
                    size="small"
                    icon={<StopOutlined />}
                    onClick={handleCancelTask}
                  >
                    取消任务
                  </Button>
                )}
                <Button
                  size="small"
                  icon={<SyncOutlined />}
                  onClick={handleRefreshTask}
                  disabled={!processingTask.task_id}
                >
                  刷新状态
                </Button>
              </Space>

              {/* 错误信息 */}
              {processingTask.status === 'failed' && processingTask.error && (
                <Alert
                  message="错误信息"
                  description={processingTask.error}
                  type="error"
                  showIcon
                  closable
                />
              )}

              {/* 完成信息和下载链接 */}
              {processingTask.status === 'completed' && processingTask.result && (
                <Alert
                  message="处理完成"
                  description={
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text>已生成 {processingTask.result.output_files?.length || 0} 个文件</Text>
                      {processingTask.result.output_files && processingTask.result.output_files.length > 0 && (
                        <div className="output-files">
                          {processingTask.result.output_files.map((file, index) => (
                            <div key={index} style={{ marginTop: 8 }}>
                              <Space>
                                <Text strong>{file.index || file.name}</Text>
                                <Text type="secondary">({file.size_mb} MB)</Text>
                                {file.download_url && (
                                  <Link href={file.download_url} target="_blank" download>
                                    下载
                                  </Link>
                                )}
                              </Space>
                            </div>
                          ))}
                        </div>
                      )}
                    </Space>
                  }
                  type="success"
                  showIcon
                />
              )}
            </Space>
          </div>
        )}
      </Form>
    </Card>
  );
};

export default ProcessingConfigPanel;
