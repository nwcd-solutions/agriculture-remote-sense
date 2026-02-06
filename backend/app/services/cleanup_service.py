"""
资源清理服务

定期清理过期的任务记录（> 30 天）、S3 中的过期文件和 CloudWatch 日志。

需求：10.9
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from app.services.task_repository import TaskRepository, TaskNotFoundError
from app.services.s3_storage_service import S3StorageService

logger = logging.getLogger(__name__)


class CleanupResult:
    """清理操作结果"""

    def __init__(self):
        self.deleted_tasks: int = 0
        self.deleted_s3_files: int = 0
        self.deleted_log_groups: int = 0
        self.errors: List[str] = []

    @property
    def total_deleted(self) -> int:
        return self.deleted_tasks + self.deleted_s3_files + self.deleted_log_groups

    def to_dict(self) -> Dict:
        return {
            "deleted_tasks": self.deleted_tasks,
            "deleted_s3_files": self.deleted_s3_files,
            "deleted_log_groups": self.deleted_log_groups,
            "total_deleted": self.total_deleted,
            "errors": self.errors,
        }


class CleanupService:
    """
    资源清理服务

    负责清理过期的任务记录、S3 文件和 CloudWatch 日志。
    """

    def __init__(
        self,
        task_repository: TaskRepository,
        s3_service: S3StorageService,
        logs_client=None,
        retention_days: int = 30,
        s3_task_prefix: str = "tasks/",
        log_group_prefix: str = "/aws/batch/",
    ):
        """
        初始化清理服务

        Args:
            task_repository: 任务数据库访问层
            s3_service: S3 存储服务
            logs_client: CloudWatch Logs 客户端（可选，默认自动创建）
            retention_days: 保留天数，超过此天数的记录将被清理
            s3_task_prefix: S3 中任务文件的前缀
            log_group_prefix: CloudWatch 日志组前缀
        """
        self.task_repository = task_repository
        self.s3_service = s3_service
        self.retention_days = retention_days
        self.s3_task_prefix = s3_task_prefix
        self.log_group_prefix = log_group_prefix

        self.logs_client = logs_client or boto3.client(
            "logs",
            region_name=os.getenv("AWS_REGION", "us-west-2"),
        )

    def cleanup_expired_tasks(self, cutoff_date: Optional[datetime] = None) -> int:
        """
        清理过期的任务记录（> retention_days 天）

        Args:
            cutoff_date: 截止日期，早于此日期的任务将被删除。
                         默认为当前时间减去 retention_days。

        Returns:
            int: 删除的任务数量
        """
        if cutoff_date is None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        deleted_count = 0
        last_key = None

        try:
            while True:
                tasks, last_key = self.task_repository.list_tasks(
                    limit=100, last_evaluated_key=last_key
                )

                for task in tasks:
                    task_created = task.created_at
                    # Ensure timezone-aware comparison
                    if task_created.tzinfo is None:
                        task_created = task_created.replace(tzinfo=timezone.utc)

                    if task_created < cutoff_date:
                        try:
                            self.task_repository.delete_task(task.task_id)
                            deleted_count += 1
                            logger.info(f"Deleted expired task: {task.task_id}")
                        except TaskNotFoundError:
                            logger.warning(f"Task already deleted: {task.task_id}")
                        except Exception as e:
                            logger.error(f"Failed to delete task {task.task_id}: {e}")

                if not last_key:
                    break

        except Exception as e:
            logger.error(f"Error during task cleanup: {e}")

        logger.info(f"Cleaned up {deleted_count} expired tasks")
        return deleted_count

    def cleanup_expired_s3_files(self, cutoff_date: Optional[datetime] = None) -> int:
        """
        清理 S3 中过期的任务文件

        Args:
            cutoff_date: 截止日期，早于此日期的文件将被删除。
                         默认为当前时间减去 retention_days。

        Returns:
            int: 删除的文件数量
        """
        if cutoff_date is None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        deleted_count = 0

        try:
            # List all objects under the task prefix
            response = self.s3_service.s3_client.list_objects_v2(
                Bucket=self.s3_service.bucket_name,
                Prefix=self.s3_task_prefix,
                MaxKeys=1000,
            )

            while True:
                contents = response.get("Contents", [])
                for obj in contents:
                    last_modified = obj["LastModified"]
                    # Ensure timezone-aware comparison
                    if last_modified.tzinfo is None:
                        last_modified = last_modified.replace(tzinfo=timezone.utc)

                    if last_modified < cutoff_date:
                        try:
                            self.s3_service.delete_file(obj["Key"])
                            deleted_count += 1
                            logger.debug(f"Deleted expired S3 file: {obj['Key']}")
                        except Exception as e:
                            logger.error(f"Failed to delete S3 file {obj['Key']}: {e}")

                # Handle pagination
                if response.get("IsTruncated"):
                    response = self.s3_service.s3_client.list_objects_v2(
                        Bucket=self.s3_service.bucket_name,
                        Prefix=self.s3_task_prefix,
                        MaxKeys=1000,
                        ContinuationToken=response["NextContinuationToken"],
                    )
                else:
                    break

        except Exception as e:
            logger.error(f"Error during S3 cleanup: {e}")

        logger.info(f"Cleaned up {deleted_count} expired S3 files")
        return deleted_count

    def cleanup_expired_logs(self, cutoff_date: Optional[datetime] = None) -> int:
        """
        清理 CloudWatch 中过期的日志流

        Args:
            cutoff_date: 截止日期，早于此日期的日志流将被删除。
                         默认为当前时间减去 retention_days。

        Returns:
            int: 删除的日志流数量
        """
        if cutoff_date is None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        cutoff_ms = int(cutoff_date.timestamp() * 1000)
        deleted_count = 0

        try:
            # List log groups matching the prefix
            paginator = self.logs_client.get_paginator("describe_log_groups")
            for page in paginator.paginate(logGroupNamePrefix=self.log_group_prefix):
                for log_group in page.get("logGroups", []):
                    group_name = log_group["logGroupName"]
                    deleted_count += self._cleanup_log_streams(
                        group_name, cutoff_ms
                    )

        except Exception as e:
            logger.error(f"Error during CloudWatch log cleanup: {e}")

        logger.info(f"Cleaned up {deleted_count} expired log streams")
        return deleted_count

    def _cleanup_log_streams(self, log_group_name: str, cutoff_ms: int) -> int:
        """
        清理指定日志组中过期的日志流

        Args:
            log_group_name: 日志组名称
            cutoff_ms: 截止时间戳（毫秒）

        Returns:
            int: 删除的日志流数量
        """
        deleted_count = 0

        try:
            paginator = self.logs_client.get_paginator("describe_log_streams")
            for page in paginator.paginate(
                logGroupName=log_group_name,
                orderBy="LastEventTime",
            ):
                for stream in page.get("logStreams", []):
                    last_event = stream.get("lastEventTimestamp", 0)
                    if last_event > 0 and last_event < cutoff_ms:
                        try:
                            self.logs_client.delete_log_stream(
                                logGroupName=log_group_name,
                                logStreamName=stream["logStreamName"],
                            )
                            deleted_count += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to delete log stream "
                                f"{stream['logStreamName']}: {e}"
                            )

        except Exception as e:
            logger.error(f"Error cleaning log streams for {log_group_name}: {e}")

        return deleted_count

    def run_full_cleanup(self) -> CleanupResult:
        """
        执行完整的资源清理

        Returns:
            CleanupResult: 清理结果
        """
        result = CleanupResult()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        logger.info(
            f"Starting full cleanup (retention={self.retention_days} days, "
            f"cutoff={cutoff_date.isoformat()})"
        )

        # 1. 清理过期任务记录
        try:
            result.deleted_tasks = self.cleanup_expired_tasks(cutoff_date)
        except Exception as e:
            result.errors.append(f"Task cleanup error: {str(e)}")

        # 2. 清理过期 S3 文件
        try:
            result.deleted_s3_files = self.cleanup_expired_s3_files(cutoff_date)
        except Exception as e:
            result.errors.append(f"S3 cleanup error: {str(e)}")

        # 3. 清理过期 CloudWatch 日志
        try:
            result.deleted_log_groups = self.cleanup_expired_logs(cutoff_date)
        except Exception as e:
            result.errors.append(f"Log cleanup error: {str(e)}")

        logger.info(
            f"Cleanup complete: {result.to_dict()}"
        )

        return result
