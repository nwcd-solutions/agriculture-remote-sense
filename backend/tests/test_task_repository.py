"""
任务仓库单元测试
"""
import os
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from app.services.task_repository import (
    TaskRepository,
    TaskRepositoryError,
    TaskNotFoundError,
    DatabaseConnectionError
)
from app.models.processing import ProcessingTask, ProcessingResult


@pytest.fixture
def mock_dynamodb_table():
    """模拟 DynamoDB 表"""
    table = Mock()
    table.table_name = "ProcessingTasks"
    table.load = Mock()
    return table


@pytest.fixture
def mock_dynamodb_resource(mock_dynamodb_table):
    """模拟 DynamoDB 资源"""
    resource = Mock()
    resource.Table.return_value = mock_dynamodb_table
    return resource


@pytest.fixture
def task_repository(mock_dynamodb_resource):
    """创建任务仓库实例"""
    with patch("boto3.resource", return_value=mock_dynamodb_resource):
        repo = TaskRepository(
            table_name="ProcessingTasks",
            region="us-west-2"
        )
        return repo


@pytest.fixture
def sample_task():
    """创建示例任务"""
    return ProcessingTask(
        task_id="task_123456",
        task_type="indices",
        status="queued",
        progress=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        parameters={
            "image_id": "S2A_MSIL2A_20240115",
            "indices": ["NDVI", "SAVI"],
            "aoi": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        }
    )


class TestTaskRepositoryInit:
    """测试任务仓库初始化"""
    
    def test_init_with_defaults(self, mock_dynamodb_resource):
        """测试使用默认参数初始化"""
        with patch("boto3.resource", return_value=mock_dynamodb_resource):
            repo = TaskRepository()
            assert repo.table_name == "ProcessingTasks"
            assert repo.region == "us-west-2"
    
    def test_init_with_custom_params(self, mock_dynamodb_resource):
        """测试使用自定义参数初始化"""
        with patch("boto3.resource", return_value=mock_dynamodb_resource):
            repo = TaskRepository(
                table_name="CustomTable",
                region="us-east-1"
            )
            assert repo.table_name == "CustomTable"
            assert repo.region == "us-east-1"
    
    def test_init_with_endpoint_url(self, mock_dynamodb_resource):
        """测试使用端点 URL 初始化（本地开发）"""
        with patch("boto3.resource", return_value=mock_dynamodb_resource) as mock_boto3:
            repo = TaskRepository(endpoint_url="http://localhost:8000")
            mock_boto3.assert_called_once()
            call_kwargs = mock_boto3.call_args[1]
            assert call_kwargs["endpoint_url"] == "http://localhost:8000"
    
    def test_init_connection_error(self):
        """测试连接错误"""
        with patch("boto3.resource") as mock_boto3:
            mock_resource = Mock()
            mock_table = Mock()
            mock_table.load.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}},
                "DescribeTable"
            )
            mock_resource.Table.return_value = mock_table
            mock_boto3.return_value = mock_resource
            
            with pytest.raises(DatabaseConnectionError):
                TaskRepository()


class TestCreateTask:
    """测试创建任务"""
    
    def test_create_task_success(self, task_repository, sample_task):
        """测试成功创建任务"""
        task_repository.table.put_item = Mock()
        
        task_id = task_repository.create_task(sample_task)
        
        assert task_id == sample_task.task_id
        task_repository.table.put_item.assert_called_once()
        
        # 验证调用参数
        call_args = task_repository.table.put_item.call_args
        item = call_args[1]["Item"]
        assert item["task_id"] == sample_task.task_id
        assert item["status"] == "queued"
        assert "ttl" in item
    
    def test_create_task_generates_id(self, task_repository, sample_task):
        """测试自动生成任务 ID"""
        sample_task.task_id = ""
        task_repository.table.put_item = Mock()
        
        task_id = task_repository.create_task(sample_task)
        
        assert task_id.startswith("task_")
        assert len(task_id) > 5
    
    def test_create_task_client_error(self, task_repository, sample_task):
        """测试创建任务时的客户端错误"""
        task_repository.table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException"}},
            "PutItem"
        )
        
        with pytest.raises(DatabaseConnectionError):
            task_repository.create_task(sample_task)


class TestGetTask:
    """测试获取任务"""
    
    def test_get_task_success(self, task_repository, sample_task):
        """测试成功获取任务"""
        # 模拟 DynamoDB 响应
        dynamodb_item = {
            "task_id": sample_task.task_id,
            "created_at": sample_task.created_at.isoformat(),
            "task_type": sample_task.task_type,
            "status": sample_task.status,
            "progress": sample_task.progress,
            "updated_at": sample_task.updated_at.isoformat(),
            "parameters": sample_task.parameters,
            "retry_count": 0,
            "max_retries": 3
        }
        
        task_repository.table.query = Mock(return_value={
            "Items": [dynamodb_item]
        })
        
        task = task_repository.get_task(sample_task.task_id)
        
        assert task.task_id == sample_task.task_id
        assert task.status == sample_task.status
        assert task.task_type == sample_task.task_type
    
    def test_get_task_not_found(self, task_repository):
        """测试获取不存在的任务"""
        task_repository.table.query = Mock(return_value={"Items": []})
        
        with pytest.raises(TaskNotFoundError):
            task_repository.get_task("nonexistent_task")
    
    def test_get_task_with_result(self, task_repository, sample_task):
        """测试获取包含结果的任务"""
        result_data = {
            "output_files": [
                {
                    "name": "NDVI.tif",
                    "s3_key": "tasks/task_123456/NDVI.tif",
                    "s3_url": "s3://bucket/tasks/task_123456/NDVI.tif",
                    "download_url": "https://...",
                    "size_mb": 45.2
                }
            ],
            "metadata": {"processing_time": 120}
        }
        
        dynamodb_item = {
            "task_id": sample_task.task_id,
            "created_at": sample_task.created_at.isoformat(),
            "task_type": sample_task.task_type,
            "status": "completed",
            "progress": 100,
            "updated_at": sample_task.updated_at.isoformat(),
            "parameters": sample_task.parameters,
            "result": result_data,
            "retry_count": 0,
            "max_retries": 3
        }
        
        task_repository.table.query = Mock(return_value={
            "Items": [dynamodb_item]
        })
        
        task = task_repository.get_task(sample_task.task_id)
        
        assert task.result is not None
        assert len(task.result.output_files) == 1
        assert task.result.metadata["processing_time"] == 120


class TestUpdateTaskStatus:
    """测试更新任务状态"""
    
    def test_update_status_basic(self, task_repository, sample_task):
        """测试基本状态更新"""
        # 模拟 get_task
        task_repository.get_task = Mock(return_value=sample_task)
        task_repository.table.update_item = Mock()
        
        success = task_repository.update_task_status(
            sample_task.task_id,
            status="running",
            progress=50
        )
        
        assert success is True
        task_repository.table.update_item.assert_called_once()
        
        # 验证更新表达式
        call_args = task_repository.table.update_item.call_args
        assert "running" in str(call_args)
    
    def test_update_status_with_batch_info(self, task_repository, sample_task):
        """测试更新包含 Batch 信息的状态"""
        task_repository.get_task = Mock(return_value=sample_task)
        task_repository.table.update_item = Mock()
        
        success = task_repository.update_task_status(
            sample_task.task_id,
            status="running",
            batch_job_id="batch_abc123",
            batch_job_status="RUNNING"
        )
        
        assert success is True
        call_args = task_repository.table.update_item.call_args
        update_expr = call_args[1]["UpdateExpression"]
        assert "batch_job_id" in update_expr
        assert "batch_job_status" in update_expr
    
    def test_update_status_with_result(self, task_repository, sample_task):
        """测试更新包含结果的状态"""
        task_repository.get_task = Mock(return_value=sample_task)
        task_repository.table.update_item = Mock()
        
        result = ProcessingResult(
            output_files=[{"name": "NDVI.tif"}],
            metadata={"processing_time": 120}
        )
        
        success = task_repository.update_task_status(
            sample_task.task_id,
            status="completed",
            progress=100,
            result=result,
            completed_at=datetime.utcnow()
        )
        
        assert success is True
    
    def test_update_status_task_not_found(self, task_repository):
        """测试更新不存在的任务"""
        task_repository.get_task = Mock(side_effect=TaskNotFoundError("Task not found"))
        
        with pytest.raises(TaskNotFoundError):
            task_repository.update_task_status("nonexistent", status="running")


class TestDeleteTask:
    """测试删除任务"""
    
    def test_delete_task_success(self, task_repository, sample_task):
        """测试成功删除任务"""
        task_repository.get_task = Mock(return_value=sample_task)
        task_repository.table.delete_item = Mock()
        
        success = task_repository.delete_task(sample_task.task_id)
        
        assert success is True
        task_repository.table.delete_item.assert_called_once()
    
    def test_delete_task_not_found(self, task_repository):
        """测试删除不存在的任务"""
        task_repository.get_task = Mock(side_effect=TaskNotFoundError("Task not found"))
        
        with pytest.raises(TaskNotFoundError):
            task_repository.delete_task("nonexistent")


class TestListTasks:
    """测试列出任务"""
    
    def test_list_tasks_all(self, task_repository):
        """测试列出所有任务"""
        # 模拟 DynamoDB 响应
        items = [
            {
                "task_id": f"task_{i}",
                "created_at": datetime.utcnow().isoformat(),
                "task_type": "indices",
                "status": "queued",
                "progress": 0,
                "updated_at": datetime.utcnow().isoformat(),
                "parameters": {},
                "retry_count": 0,
                "max_retries": 3
            }
            for i in range(5)
        ]
        
        task_repository.table.scan = Mock(return_value={
            "Items": items,
            "LastEvaluatedKey": None
        })
        
        tasks, next_key = task_repository.list_tasks(limit=10)
        
        assert len(tasks) == 5
        assert next_key is None
    
    def test_list_tasks_by_status(self, task_repository):
        """测试按状态过滤任务"""
        items = [
            {
                "task_id": f"task_{i}",
                "created_at": datetime.utcnow().isoformat(),
                "task_type": "indices",
                "status": "completed",
                "progress": 100,
                "updated_at": datetime.utcnow().isoformat(),
                "parameters": {},
                "retry_count": 0,
                "max_retries": 3
            }
            for i in range(3)
        ]
        
        task_repository.table.query = Mock(return_value={
            "Items": items,
            "LastEvaluatedKey": None
        })
        
        tasks, next_key = task_repository.list_tasks(status="completed", limit=10)
        
        assert len(tasks) == 3
        assert all(task.status == "completed" for task in tasks)
    
    def test_list_tasks_with_pagination(self, task_repository):
        """测试分页列出任务"""
        items = [
            {
                "task_id": f"task_{i}",
                "created_at": datetime.utcnow().isoformat(),
                "task_type": "indices",
                "status": "queued",
                "progress": 0,
                "updated_at": datetime.utcnow().isoformat(),
                "parameters": {},
                "retry_count": 0,
                "max_retries": 3
            }
            for i in range(20)
        ]
        
        last_key = {"task_id": "task_19", "created_at": datetime.utcnow().isoformat()}
        
        task_repository.table.scan = Mock(return_value={
            "Items": items,
            "LastEvaluatedKey": last_key
        })
        
        tasks, next_key = task_repository.list_tasks(limit=20)
        
        assert len(tasks) == 20
        assert next_key == last_key


class TestQueryByBatchJobId:
    """测试通过 Batch Job ID 查询"""
    
    def test_query_by_batch_job_id_found(self, task_repository, sample_task):
        """测试找到任务"""
        dynamodb_item = {
            "task_id": sample_task.task_id,
            "created_at": sample_task.created_at.isoformat(),
            "task_type": sample_task.task_type,
            "status": sample_task.status,
            "progress": sample_task.progress,
            "updated_at": sample_task.updated_at.isoformat(),
            "parameters": sample_task.parameters,
            "batch_job_id": "batch_abc123",
            "retry_count": 0,
            "max_retries": 3
        }
        
        task_repository.table.query = Mock(return_value={
            "Items": [dynamodb_item]
        })
        
        task = task_repository.query_by_batch_job_id("batch_abc123")
        
        assert task is not None
        assert task.task_id == sample_task.task_id
        assert task.batch_job_id == "batch_abc123"
    
    def test_query_by_batch_job_id_not_found(self, task_repository):
        """测试未找到任务"""
        task_repository.table.query = Mock(return_value={"Items": []})
        
        task = task_repository.query_by_batch_job_id("nonexistent_batch_job")
        
        assert task is None


class TestConvertDecimals:
    """测试 Decimal 转换"""
    
    def test_convert_decimal_to_int(self, task_repository):
        """测试转换 Decimal 为 int"""
        obj = {"progress": Decimal("100")}
        result = task_repository._convert_decimals(obj)
        assert result["progress"] == 100
        assert isinstance(result["progress"], int)
    
    def test_convert_decimal_to_float(self, task_repository):
        """测试转换 Decimal 为 float"""
        obj = {"size_mb": Decimal("45.2")}
        result = task_repository._convert_decimals(obj)
        assert result["size_mb"] == 45.2
        assert isinstance(result["size_mb"], float)
    
    def test_convert_nested_decimals(self, task_repository):
        """测试转换嵌套的 Decimal"""
        obj = {
            "task": {
                "progress": Decimal("50"),
                "metadata": {
                    "size": Decimal("123.45")
                }
            },
            "items": [Decimal("1"), Decimal("2.5")]
        }
        
        result = task_repository._convert_decimals(obj)
        
        assert result["task"]["progress"] == 50
        assert result["task"]["metadata"]["size"] == 123.45
        assert result["items"] == [1, 2.5]
