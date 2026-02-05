import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProcessingConfigPanel from './ProcessingConfigPanel';

describe('ProcessingConfigPanel', () => {
  const mockOnProcess = jest.fn();
  const mockOnCancelTask = jest.fn();
  const mockOnRefreshTask = jest.fn();

  const mockSelectedImage = {
    id: 'S2A_MSIL2A_20240615T103031_N0510_R108_T32TQM_20240615T142856',
    satellite: 'sentinel-2',
    product_level: 'L2A',
    datetime: '2024-06-15T10:30:31Z',
    cloud_cover: 15.2
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('任务状态显示', () => {
    test('应该显示排队状态', () => {
      const task = {
        task_id: 'task_123',
        status: 'queued',
        progress: 0,
        batch_job_id: 'batch_abc',
        batch_job_status: 'SUBMITTED'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.getByText('任务已创建，等待处理...')).toBeInTheDocument();
      expect(screen.getByText('task_123')).toBeInTheDocument();
      expect(screen.getByText('batch_abc')).toBeInTheDocument();
      expect(screen.getByText('已提交')).toBeInTheDocument();
    });

    test('应该显示运行状态', () => {
      const task = {
        task_id: 'task_123',
        status: 'running',
        progress: 50,
        batch_job_id: 'batch_abc',
        batch_job_status: 'RUNNING'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.getByText('正在处理中...')).toBeInTheDocument();
      expect(screen.getByText('运行中')).toBeInTheDocument();
    });

    test('应该显示完成状态和下载链接', () => {
      const task = {
        task_id: 'task_123',
        status: 'completed',
        progress: 100,
        batch_job_id: 'batch_abc',
        batch_job_status: 'SUCCEEDED',
        result: {
          output_files: [
            {
              name: 'NDVI.tif',
              index: 'NDVI',
              size_mb: 45.2,
              download_url: 'https://example.com/download/NDVI.tif'
            },
            {
              name: 'EVI.tif',
              index: 'EVI',
              size_mb: 45.5,
              download_url: 'https://example.com/download/EVI.tif'
            }
          ]
        }
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.getByText('处理完成！')).toBeInTheDocument();
      expect(screen.getByText('成功')).toBeInTheDocument();
      expect(screen.getByText('已生成 2 个文件')).toBeInTheDocument();
      expect(screen.getAllByText('NDVI')[0]).toBeInTheDocument();
      expect(screen.getAllByText('EVI')[0]).toBeInTheDocument();
      expect(screen.getByText('(45.2 MB)')).toBeInTheDocument();
      expect(screen.getByText('(45.5 MB)')).toBeInTheDocument();
    });

    test('应该显示失败状态和错误信息', () => {
      const task = {
        task_id: 'task_123',
        status: 'failed',
        progress: 0,
        batch_job_id: 'batch_abc',
        batch_job_status: 'FAILED',
        error: 'Processing failed: Out of memory'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.getByText('处理失败')).toBeInTheDocument();
      expect(screen.getByText('失败')).toBeInTheDocument();
      expect(screen.getByText('Processing failed: Out of memory')).toBeInTheDocument();
    });

    test('应该显示 Batch Job ID', () => {
      const task = {
        task_id: 'task_123',
        status: 'running',
        progress: 30,
        batch_job_id: 'abc-def-123-456',
        batch_job_status: 'RUNNING'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.getByText('Batch Job ID:')).toBeInTheDocument();
      expect(screen.getByText('abc-def-123-456')).toBeInTheDocument();
    });
  });

  describe('任务进度轮询', () => {
    test('应该显示进度条', () => {
      const task = {
        task_id: 'task_123',
        status: 'running',
        progress: 65,
        batch_job_id: 'batch_abc',
        batch_job_status: 'RUNNING'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute('aria-valuenow', '65');
    });

    test('应该在任务运行时显示刷新按钮', () => {
      const task = {
        task_id: 'task_123',
        status: 'running',
        progress: 50,
        batch_job_id: 'batch_abc',
        batch_job_status: 'RUNNING'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      const refreshButton = screen.getByText('刷新状态');
      expect(refreshButton).toBeInTheDocument();
    });

    test('点击刷新按钮应该调用 onRefreshTask', () => {
      const task = {
        task_id: 'task_123',
        status: 'running',
        progress: 50,
        batch_job_id: 'batch_abc',
        batch_job_status: 'RUNNING'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      const refreshButton = screen.getByText('刷新状态');
      fireEvent.click(refreshButton);

      expect(mockOnRefreshTask).toHaveBeenCalledWith('task_123');
    });
  });

  describe('下载功能', () => {
    test('应该显示下载链接', () => {
      const task = {
        task_id: 'task_123',
        status: 'completed',
        progress: 100,
        batch_job_id: 'batch_abc',
        batch_job_status: 'SUCCEEDED',
        result: {
          output_files: [
            {
              name: 'NDVI.tif',
              index: 'NDVI',
              size_mb: 45.2,
              download_url: 'https://s3.amazonaws.com/bucket/NDVI.tif?signature=abc'
            }
          ]
        }
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      const downloadLink = screen.getByText('下载');
      expect(downloadLink).toBeInTheDocument();
      expect(downloadLink).toHaveAttribute('href', 'https://s3.amazonaws.com/bucket/NDVI.tif?signature=abc');
      expect(downloadLink).toHaveAttribute('target', '_blank');
    });

    test('应该显示多个文件的下载链接', () => {
      const task = {
        task_id: 'task_123',
        status: 'completed',
        progress: 100,
        batch_job_id: 'batch_abc',
        batch_job_status: 'SUCCEEDED',
        result: {
          output_files: [
            {
              name: 'NDVI.tif',
              index: 'NDVI',
              size_mb: 45.2,
              download_url: 'https://example.com/NDVI.tif'
            },
            {
              name: 'EVI.tif',
              index: 'EVI',
              size_mb: 45.5,
              download_url: 'https://example.com/EVI.tif'
            },
            {
              name: 'SAVI.tif',
              index: 'SAVI',
              size_mb: 45.3,
              download_url: 'https://example.com/SAVI.tif'
            }
          ]
        }
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      const downloadLinks = screen.getAllByText('下载');
      expect(downloadLinks).toHaveLength(3);
    });
  });

  describe('任务取消功能', () => {
    test('应该在任务排队时显示取消按钮', () => {
      const task = {
        task_id: 'task_123',
        status: 'queued',
        progress: 0,
        batch_job_id: 'batch_abc',
        batch_job_status: 'SUBMITTED'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.getByText('取消任务')).toBeInTheDocument();
    });

    test('应该在任务运行时显示取消按钮', () => {
      const task = {
        task_id: 'task_123',
        status: 'running',
        progress: 50,
        batch_job_id: 'batch_abc',
        batch_job_status: 'RUNNING'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.getByText('取消任务')).toBeInTheDocument();
    });

    test('不应该在任务完成时显示取消按钮', () => {
      const task = {
        task_id: 'task_123',
        status: 'completed',
        progress: 100,
        batch_job_id: 'batch_abc',
        batch_job_status: 'SUCCEEDED',
        result: {
          output_files: []
        }
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.queryByText('取消任务')).not.toBeInTheDocument();
    });

    test('点击取消按钮应该调用 onCancelTask', () => {
      const task = {
        task_id: 'task_123',
        status: 'running',
        progress: 50,
        batch_job_id: 'batch_abc',
        batch_job_status: 'RUNNING'
      };

      render(
        <ProcessingConfigPanel
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      const cancelButton = screen.getByText('取消任务');
      fireEvent.click(cancelButton);

      expect(mockOnCancelTask).toHaveBeenCalledWith('task_123');
    });
  });

  describe('植被指数选择', () => {
    test('应该显示可用的植被指数', () => {
      render(
        <ProcessingConfigPanel
          availableIndices={['NDVI', 'SAVI', 'EVI', 'VGI']}
          selectedImage={mockSelectedImage}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      expect(screen.getByText('NDVI')).toBeInTheDocument();
      expect(screen.getByText('SAVI')).toBeInTheDocument();
      expect(screen.getByText('EVI')).toBeInTheDocument();
      expect(screen.getByText('VGI')).toBeInTheDocument();
    });

    test('应该在没有选择影像时禁用处理按钮', () => {
      render(
        <ProcessingConfigPanel
          availableIndices={['NDVI', 'SAVI', 'EVI', 'VGI']}
          selectedImage={null}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      const processButton = screen.getByRole('button', { name: /开始处理/i });
      expect(processButton).toBeDisabled();
    });

    test('应该在任务运行时禁用处理按钮', () => {
      const task = {
        task_id: 'task_123',
        status: 'running',
        progress: 50,
        batch_job_id: 'batch_abc',
        batch_job_status: 'RUNNING'
      };

      render(
        <ProcessingConfigPanel
          availableIndices={['NDVI', 'SAVI', 'EVI', 'VGI']}
          selectedImage={mockSelectedImage}
          processingTask={task}
          onProcess={mockOnProcess}
          onCancelTask={mockOnCancelTask}
          onRefreshTask={mockOnRefreshTask}
        />
      );

      const processButton = screen.getByRole('button', { name: /处理中/i });
      expect(processButton).toBeDisabled();
    });
  });
});
