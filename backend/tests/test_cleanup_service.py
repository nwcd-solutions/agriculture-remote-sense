"""
资源清理服务单元测试

测试任务记录清理、S3 文件清理和 CloudWatch 日志清理。
需求：10.9
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock, call

from app.services.cleanup_service import CleanupService, CleanupResult
from app.services.task_repository import TaskNotFoundError
from app.models.processing import ProcessingTask


@pytest.fixture
def mock_task_repository():
    """模拟任务仓库"""
    repo = Mock()
    return repo


@pytest.fixture
def mock_s3_service():
    """模拟 S3 存储服务"""
    service = Mock()
    service.bucket_name = "test-bucket"
    service.s3_client = Mock()
    return service


@pytest.fixture
def mock_logs_client():
    """模拟 CloudWatch Logs 客户端"""
    return Mock()


@pytest.fixture
def cleanup_service(mock_task_repository, mock_s3_service, mock_logs_client):
    """创建清理服务实例"""
    return CleanupService(
        task_repository=mock_task_repository,
        s3_service=mock_s3_service,
        logs_client=mock_logs_client,
        retention_days=30,
        s3_task_prefix="tasks/",
        log_group_prefix="/aws/batch/",
    )


def _make_task(task_id: str, created_at: datetime) -> ProcessingTask:
    """创建测试用任务"""
    return ProcessingTask(
        task_id=task_id,
        task_type="indices",
        status="completed",
        progress=100,
        created_at=created_at,
        updated_at=created_at,
        parameters={},
    )


class TestCleanupResult:
    """测试 CleanupResult"""

    def test_initial_state(self):
        result = CleanupResult()
        assert result.deleted_tasks == 0
        assert result.deleted_s3_files == 0
        assert result.deleted_log_groups == 0
        assert result.total_deleted == 0
        assert result.errors == []

    def test_total_deleted(self):
        result = CleanupResult()
        result.deleted_tasks = 5
        result.deleted_s3_files = 10
        result.deleted_log_groups = 3
        assert result.total_deleted == 18

    def test_to_dict(self):
        result = CleanupResult()
        result.deleted_tasks = 2
        result.deleted_s3_files = 4
        result.errors.append("some error")
        d = result.to_dict()
        assert d["deleted_tasks"] == 2
        assert d["deleted_s3_files"] == 4
        assert d["total_deleted"] == 6
        assert len(d["errors"]) == 1


class TestCleanupExpiredTasks:
    """测试任务记录清理"""

    def test_deletes_old_tasks(self, cleanup_service, mock_task_repository):
        """过期任务应被删除"""
        now = datetime.now(timezone.utc)
        old_task = _make_task("task_old", now - timedelta(days=45))
        recent_task = _make_task("task_recent", now - timedelta(days=5))

        mock_task_repository.list_tasks.return_value = (
            [old_task, recent_task],
            None,
        )
        mock_task_repository.delete_task.return_value = True

        count = cleanup_service.cleanup_expired_tasks()

        assert count == 1
        mock_task_repository.delete_task.assert_called_once_with("task_old")

    def test_no_tasks_to_delete(self, cleanup_service, mock_task_repository):
        """没有过期任务时返回 0"""
        now = datetime.now(timezone.utc)
        recent = _make_task("task_1", now - timedelta(days=1))

        mock_task_repository.list_tasks.return_value = ([recent], None)

        count = cleanup_service.cleanup_expired_tasks()

        assert count == 0
        mock_task_repository.delete_task.assert_not_called()

    def test_handles_pagination(self, cleanup_service, mock_task_repository):
        """分页场景下应清理所有过期任务"""
        now = datetime.now(timezone.utc)
        old1 = _make_task("task_old1", now - timedelta(days=60))
        old2 = _make_task("task_old2", now - timedelta(days=90))

        page_key = {"task_id": "task_old1"}
        mock_task_repository.list_tasks.side_effect = [
            ([old1], page_key),
            ([old2], None),
        ]
        mock_task_repository.delete_task.return_value = True

        count = cleanup_service.cleanup_expired_tasks()

        assert count == 2

    def test_handles_already_deleted_task(self, cleanup_service, mock_task_repository):
        """任务已被删除时应跳过并继续"""
        now = datetime.now(timezone.utc)
        old = _make_task("task_gone", now - timedelta(days=45))

        mock_task_repository.list_tasks.return_value = ([old], None)
        mock_task_repository.delete_task.side_effect = TaskNotFoundError("gone")

        count = cleanup_service.cleanup_expired_tasks()

        assert count == 0

    def test_custom_cutoff_date(self, cleanup_service, mock_task_repository):
        """使用自定义截止日期"""
        now = datetime.now(timezone.utc)
        task = _make_task("task_1", now - timedelta(days=10))

        mock_task_repository.list_tasks.return_value = ([task], None)
        mock_task_repository.delete_task.return_value = True

        # 使用 5 天前作为截止日期，task 应被删除
        cutoff = now - timedelta(days=5)
        count = cleanup_service.cleanup_expired_tasks(cutoff_date=cutoff)

        assert count == 1


class TestCleanupExpiredS3Files:
    """测试 S3 文件清理"""

    def test_deletes_old_files(self, cleanup_service, mock_s3_service):
        """过期 S3 文件应被删除"""
        now = datetime.now(timezone.utc)
        mock_s3_service.s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "tasks/old_task/result.tif", "LastModified": now - timedelta(days=45)},
                {"Key": "tasks/new_task/result.tif", "LastModified": now - timedelta(days=5)},
            ],
            "IsTruncated": False,
        }
        mock_s3_service.delete_file.return_value = True

        count = cleanup_service.cleanup_expired_s3_files()

        assert count == 1
        mock_s3_service.delete_file.assert_called_once_with("tasks/old_task/result.tif")

    def test_no_files_to_delete(self, cleanup_service, mock_s3_service):
        """没有过期文件时返回 0"""
        now = datetime.now(timezone.utc)
        mock_s3_service.s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "tasks/new/file.tif", "LastModified": now - timedelta(days=1)},
            ],
            "IsTruncated": False,
        }

        count = cleanup_service.cleanup_expired_s3_files()

        assert count == 0
        mock_s3_service.delete_file.assert_not_called()

    def test_empty_bucket(self, cleanup_service, mock_s3_service):
        """空桶时返回 0"""
        mock_s3_service.s3_client.list_objects_v2.return_value = {
            "IsTruncated": False,
        }

        count = cleanup_service.cleanup_expired_s3_files()

        assert count == 0

    def test_handles_pagination(self, cleanup_service, mock_s3_service):
        """分页场景下应清理所有过期文件"""
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=60)

        mock_s3_service.s3_client.list_objects_v2.side_effect = [
            {
                "Contents": [{"Key": "tasks/a/f.tif", "LastModified": old_date}],
                "IsTruncated": True,
                "NextContinuationToken": "token1",
            },
            {
                "Contents": [{"Key": "tasks/b/f.tif", "LastModified": old_date}],
                "IsTruncated": False,
            },
        ]
        mock_s3_service.delete_file.return_value = True

        count = cleanup_service.cleanup_expired_s3_files()

        assert count == 2

    def test_continues_on_delete_error(self, cleanup_service, mock_s3_service):
        """单个文件删除失败时应继续处理其他文件"""
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=60)

        mock_s3_service.s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "tasks/a/f.tif", "LastModified": old_date},
                {"Key": "tasks/b/f.tif", "LastModified": old_date},
            ],
            "IsTruncated": False,
        }
        mock_s3_service.delete_file.side_effect = [Exception("fail"), True]

        count = cleanup_service.cleanup_expired_s3_files()

        # Only the second file was successfully deleted
        assert count == 1


class TestCleanupExpiredLogs:
    """测试 CloudWatch 日志清理"""

    def test_deletes_old_log_streams(self, cleanup_service, mock_logs_client):
        """过期日志流应被删除"""
        now = datetime.now(timezone.utc)
        old_ts = int((now - timedelta(days=60)).timestamp() * 1000)
        recent_ts = int((now - timedelta(days=5)).timestamp() * 1000)

        # Mock paginator for log groups
        group_paginator = Mock()
        group_paginator.paginate.return_value = [
            {"logGroups": [{"logGroupName": "/aws/batch/job-def"}]}
        ]

        # Mock paginator for log streams
        stream_paginator = Mock()
        stream_paginator.paginate.return_value = [
            {
                "logStreams": [
                    {"logStreamName": "old-stream", "lastEventTimestamp": old_ts},
                    {"logStreamName": "new-stream", "lastEventTimestamp": recent_ts},
                ]
            }
        ]

        mock_logs_client.get_paginator.side_effect = lambda name: (
            group_paginator if name == "describe_log_groups" else stream_paginator
        )

        count = cleanup_service.cleanup_expired_logs()

        assert count == 1
        mock_logs_client.delete_log_stream.assert_called_once_with(
            logGroupName="/aws/batch/job-def",
            logStreamName="old-stream",
        )

    def test_no_log_groups(self, cleanup_service, mock_logs_client):
        """没有日志组时返回 0"""
        paginator = Mock()
        paginator.paginate.return_value = [{"logGroups": []}]
        mock_logs_client.get_paginator.return_value = paginator

        count = cleanup_service.cleanup_expired_logs()

        assert count == 0


class TestRunFullCleanup:
    """测试完整清理流程"""

    def test_runs_all_cleanup_steps(self, cleanup_service):
        """完整清理应执行所有三个步骤"""
        cleanup_service.cleanup_expired_tasks = Mock(return_value=3)
        cleanup_service.cleanup_expired_s3_files = Mock(return_value=5)
        cleanup_service.cleanup_expired_logs = Mock(return_value=2)

        result = cleanup_service.run_full_cleanup()

        assert result.deleted_tasks == 3
        assert result.deleted_s3_files == 5
        assert result.deleted_log_groups == 2
        assert result.total_deleted == 10
        assert result.errors == []

    def test_captures_errors_without_stopping(self, cleanup_service):
        """单个步骤失败不应阻止其他步骤执行"""
        cleanup_service.cleanup_expired_tasks = Mock(
            side_effect=Exception("db error")
        )
        cleanup_service.cleanup_expired_s3_files = Mock(return_value=5)
        cleanup_service.cleanup_expired_logs = Mock(return_value=2)

        result = cleanup_service.run_full_cleanup()

        assert result.deleted_tasks == 0
        assert result.deleted_s3_files == 5
        assert result.deleted_log_groups == 2
        assert len(result.errors) == 1
        assert "Task cleanup error" in result.errors[0]
