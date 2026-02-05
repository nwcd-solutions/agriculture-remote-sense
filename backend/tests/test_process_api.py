"""
数据处理 API 端点测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from main import app
from app.models.processing import ProcessingResult, ProcessingTask


client = TestClient(app)


@pytest.fixture
def valid_indices_request():
    """有效的植被指数计算请求"""
    return {
        "image_id": "S2A_MSIL2A_20240115T023541",
        "indices": ["NDVI", "EVI"],
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0],
                [116.3, 39.9]
            ]]
        },
        "output_format": "COG",
        "band_urls": {
            "red": "https://example.com/red.tif",
            "nir": "https://example.com/nir.tif",
            "blue": "https://example.com/blue.tif"
        }
    }


@pytest.fixture
def mock_batch_services():
    """Mock AWS Batch services"""
    with patch('app.api.process.BATCH_AVAILABLE', True), \
         patch('app.api.process.batch_manager') as mock_batch, \
         patch('app.api.process.task_repository') as mock_repo, \
         patch('app.api.process.s3_service') as mock_s3:
        
        # Mock batch manager
        mock_batch.submit_job.return_value = "batch-job-123"
        mock_batch.get_job_status.return_value = {
            'job_id': 'batch-job-123',
            'job_name': 'test-job',
            'status': 'RUNNING',
            'status_reason': '',
            'created_at': 1234567890000,
            'started_at': 1234567900000
        }
        mock_batch.cancel_job.return_value = True
        
        # Mock task repository
        mock_repo.create_task.return_value = "task_abc123"
        mock_repo.get_task.return_value = ProcessingTask(
            task_id="task_abc123",
            task_type="indices",
            status="queued",
            progress=0,
            batch_job_id="batch-job-123",
            batch_job_status="SUBMITTED",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            parameters={}
        )
        mock_repo.update_task_status.return_value = True
        mock_repo.list_tasks.return_value = ([], None)
        
        # Mock S3 service
        mock_s3.file_exists.return_value = True
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/presigned-url"
        mock_s3.get_file_size.return_value = 1024 * 1024  # 1 MB
        
        yield {
            'batch': mock_batch,
            'repo': mock_repo,
            's3': mock_s3
        }


def test_process_indices_success(valid_indices_request, mock_batch_services):
    """测试成功创建植被指数计算任务"""
    response = client.post("/api/process/indices", json=valid_indices_request)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "task_id" in data
    assert data["status"] == "queued"
    assert "batch_job_id" in data
    assert data["batch_job_id"] == "batch-job-123"
    assert "estimated_time" in data
    assert data["estimated_time"] > 0
    
    # Verify batch manager was called
    mock_batch_services['batch'].submit_job.assert_called_once()
    mock_batch_services['repo'].create_task.assert_called_once()


def test_process_indices_empty_indices(mock_batch_services):
    """测试空指数列表"""
    request = {
        "image_id": "S2A_MSIL2A_20240115T023541",
        "indices": [],  # 空列表
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9],
                [116.4, 40.0],
                [116.3, 40.0],
                [116.3, 39.9]
            ]]
        },
        "band_urls": {
            "red": "https://example.com/red.tif",
            "nir": "https://example.com/nir.tif"
        }
    }
    
    response = client.post("/api/process/indices", json=request)
    
    assert response.status_code == 400
    assert "At least one vegetation index must be specified" in response.json()["detail"]


def test_process_indices_all_indices(valid_indices_request, mock_batch_services):
    """测试计算所有植被指数"""
    valid_indices_request["indices"] = ["NDVI", "SAVI", "EVI", "VGI"]
    valid_indices_request["band_urls"]["green"] = "https://example.com/green.tif"
    
    response = client.post("/api/process/indices", json=valid_indices_request)
    
    assert response.status_code == 200
    data = response.json()
    
    # 估算时间应该是 4 个指数 * 30 秒
    assert data["estimated_time"] == 120


def test_process_indices_batch_unavailable():
    """测试 Batch 不可用的情况"""
    with patch('app.api.process.BATCH_AVAILABLE', False):
        request = {
            "image_id": "S2A_MSIL2A_20240115T023541",
            "indices": ["NDVI"],
            "aoi": {
                "type": "Polygon",
                "coordinates": [[
                    [116.3, 39.9],
                    [116.4, 39.9],
                    [116.4, 40.0],
                    [116.3, 40.0],
                    [116.3, 39.9]
                ]]
            },
            "band_urls": {
                "red": "https://example.com/red.tif",
                "nir": "https://example.com/nir.tif"
            }
        }
        
        response = client.post("/api/process/indices", json=request)
        
        assert response.status_code == 503
        assert "AWS Batch integration is not available" in response.json()["detail"]


def test_get_task_status_success(mock_batch_services):
    """测试获取任务状态"""
    response = client.get("/api/process/tasks/task_abc123")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["task_id"] == "task_abc123"
    assert data["task_type"] == "indices"
    assert data["status"] in ["queued", "running", "completed", "failed"]
    assert "progress" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "batch_job_id" in data
    
    # Verify batch status was queried
    mock_batch_services['batch'].get_job_status.assert_called_once()


def test_get_task_status_not_found(mock_batch_services):
    """测试获取不存在的任务"""
    from app.services.task_repository import TaskNotFoundError
    mock_batch_services['repo'].get_task.side_effect = TaskNotFoundError("Task not found")
    
    response = client.get("/api/process/tasks/nonexistent-task-id")
    
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]


def test_list_tasks(mock_batch_services):
    """测试列出所有任务"""
    mock_batch_services['repo'].list_tasks.return_value = (
        [
            ProcessingTask(
                task_id="task_1",
                task_type="indices",
                status="completed",
                progress=100,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                parameters={}
            )
        ],
        None
    )
    
    response = client.get("/api/process/tasks")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "tasks" in data
    assert "total" in data
    assert "limit" in data
    assert isinstance(data["tasks"], list)


def test_list_tasks_with_status_filter(mock_batch_services):
    """测试按状态过滤任务列表"""
    response = client.get("/api/process/tasks?status=completed")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "tasks" in data
    mock_batch_services['repo'].list_tasks.assert_called_once()


def test_list_tasks_with_limit(mock_batch_services):
    """测试带限制的任务列表"""
    response = client.get("/api/process/tasks?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["limit"] == 10


def test_list_tasks_invalid_status(mock_batch_services):
    """测试无效的状态过滤"""
    response = client.get("/api/process/tasks?status=invalid")
    
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_cancel_task_success(mock_batch_services):
    """测试成功取消任务"""
    response = client.delete("/api/process/tasks/task_abc123")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["task_id"] == "task_abc123"
    assert data["status"] == "cancelled"
    
    # Verify batch job was cancelled
    mock_batch_services['batch'].cancel_job.assert_called_once()
    mock_batch_services['repo'].update_task_status.assert_called_once()


def test_cancel_task_already_completed(mock_batch_services):
    """测试取消已完成的任务"""
    mock_batch_services['repo'].get_task.return_value = ProcessingTask(
        task_id="task_abc123",
        task_type="indices",
        status="completed",
        progress=100,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        parameters={}
    )
    
    response = client.delete("/api/process/tasks/task_abc123")
    
    assert response.status_code == 400
    assert "Cannot cancel task in status" in response.json()["detail"]


def test_cancel_task_not_found(mock_batch_services):
    """测试取消不存在的任务"""
    from app.services.task_repository import TaskNotFoundError
    mock_batch_services['repo'].get_task.side_effect = TaskNotFoundError("Task not found")
    
    response = client.delete("/api/process/tasks/nonexistent-task-id")
    
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]


def test_process_indices_invalid_aoi():
    """测试无效的 AOI"""
    request = {
        "image_id": "S2A_MSIL2A_20240115T023541",
        "indices": ["NDVI"],
        "aoi": {
            "type": "Polygon",
            "coordinates": [[
                [116.3, 39.9],
                [116.4, 39.9]
                # 不是有效的多边形
            ]]
        },
        "band_urls": {
            "red": "https://example.com/red.tif",
            "nir": "https://example.com/nir.tif"
        }
    }
    
    response = client.post("/api/process/indices", json=request)
    
    assert response.status_code == 422  # Validation error

