"""
DynamoDB 任务数据库访问层
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal
import uuid

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from boto3.dynamodb.conditions import Key, Attr

from app.models.processing import ProcessingTask, ProcessingResult


logger = logging.getLogger(__name__)


class TaskRepositoryError(Exception):
    """任务仓库错误基类"""
    pass


class TaskNotFoundError(TaskRepositoryError):
    """任务未找到错误"""
    pass


class DatabaseConnectionError(TaskRepositoryError):
    """数据库连接错误"""
    pass


class TaskRepository:
    """
    任务数据库访问层
    
    提供对 DynamoDB ProcessingTasks 表的 CRUD 操作
    """
    
    def __init__(
        self,
        table_name: Optional[str] = None,
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None
    ):
        """
        初始化任务仓库
        
        Args:
            table_name: DynamoDB 表名，默认从环境变量 DYNAMODB_TABLE 读取
            region: AWS 区域，默认从环境变量 AWS_REGION 读取
            endpoint_url: DynamoDB 端点 URL（用于本地开发），从环境变量 DYNAMODB_ENDPOINT 读取
        """
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE", "ProcessingTasks")
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.endpoint_url = endpoint_url or os.getenv("DYNAMODB_ENDPOINT")
        
        try:
            # 创建 DynamoDB 资源
            dynamodb_config = {
                "region_name": self.region
            }
            if self.endpoint_url:
                dynamodb_config["endpoint_url"] = self.endpoint_url
            
            self.dynamodb = boto3.resource("dynamodb", **dynamodb_config)
            self.table = self.dynamodb.Table(self.table_name)
            
            # 验证表是否存在
            self.table.load()
            logger.info(f"Connected to DynamoDB table: {self.table_name}")
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to connect to DynamoDB: {error_code} - {str(e)}")
            raise DatabaseConnectionError(f"Cannot connect to DynamoDB table {self.table_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to DynamoDB: {str(e)}")
            raise DatabaseConnectionError(f"Unexpected error: {str(e)}")
    
    def create_task(self, task: ProcessingTask) -> str:
        """
        创建新任务
        
        Args:
            task: 处理任务对象
            
        Returns:
            str: 任务 ID
            
        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 如果没有 task_id，生成一个
            if not task.task_id:
                task.task_id = f"task_{uuid.uuid4().hex[:12]}"
            
            # 设置 TTL（30 天后过期）
            ttl = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
            
            # 转换为 DynamoDB 格式
            item = self._task_to_dynamodb(task)
            item["ttl"] = ttl
            
            # 写入数据库
            self.table.put_item(Item=item)
            
            logger.info(f"Created task: {task.task_id}")
            return task.task_id
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to create task: {error_code} - {str(e)}")
            raise DatabaseConnectionError(f"Failed to create task: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating task: {str(e)}")
            raise DatabaseConnectionError(f"Unexpected error: {str(e)}")
    
    def get_task(self, task_id: str) -> ProcessingTask:
        """
        获取任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            ProcessingTask: 任务对象
            
        Raises:
            TaskNotFoundError: 任务不存在
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 查询任务（需要使用 query 因为有 sort key）
            response = self.table.query(
                KeyConditionExpression=Key("task_id").eq(task_id),
                Limit=1
            )
            
            items = response.get("Items", [])
            if not items:
                raise TaskNotFoundError(f"Task not found: {task_id}")
            
            task = self._dynamodb_to_task(items[0])
            logger.debug(f"Retrieved task: {task_id}")
            return task
            
        except TaskNotFoundError:
            raise
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to get task: {error_code} - {str(e)}")
            raise DatabaseConnectionError(f"Failed to get task: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting task: {str(e)}")
            raise DatabaseConnectionError(f"Unexpected error: {str(e)}")
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        batch_job_id: Optional[str] = None,
        batch_job_status: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[ProcessingResult] = None,
        error: Optional[str] = None,
        retry_count: Optional[int] = None
    ) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            status: 新状态
            progress: 进度（0-100）
            batch_job_id: AWS Batch Job ID
            batch_job_status: AWS Batch Job 状态
            started_at: 开始时间
            completed_at: 完成时间
            result: 处理结果
            error: 错误信息
            retry_count: 重试次数
            
        Returns:
            bool: 是否更新成功
            
        Raises:
            TaskNotFoundError: 任务不存在
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 首先获取任务以获取 created_at（sort key）
            task = self.get_task(task_id)
            
            # 构建更新表达式
            update_expression = "SET #status = :status, updated_at = :updated_at"
            expression_attribute_names = {"#status": "status"}
            expression_attribute_values = {
                ":status": status,
                ":updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if progress is not None:
                update_expression += ", progress = :progress"
                expression_attribute_values[":progress"] = progress
            
            if batch_job_id is not None:
                update_expression += ", batch_job_id = :batch_job_id"
                expression_attribute_values[":batch_job_id"] = batch_job_id
            
            if batch_job_status is not None:
                update_expression += ", batch_job_status = :batch_job_status"
                expression_attribute_values[":batch_job_status"] = batch_job_status
            
            if started_at is not None:
                update_expression += ", started_at = :started_at"
                expression_attribute_values[":started_at"] = started_at.isoformat()
            
            if completed_at is not None:
                update_expression += ", completed_at = :completed_at"
                expression_attribute_values[":completed_at"] = completed_at.isoformat()
            
            if result is not None:
                update_expression += ", #result = :result"
                expression_attribute_names["#result"] = "result"
                expression_attribute_values[":result"] = result.model_dump()
            
            if error is not None:
                update_expression += ", #error = :error"
                expression_attribute_names["#error"] = "error"
                expression_attribute_values[":error"] = error
            
            if retry_count is not None:
                update_expression += ", retry_count = :retry_count"
                expression_attribute_values[":retry_count"] = retry_count
            
            # 执行更新
            self.table.update_item(
                Key={
                    "task_id": task_id,
                    "created_at": task.created_at.isoformat()
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            logger.info(f"Updated task {task_id} status to {status}")
            return True
            
        except TaskNotFoundError:
            raise
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to update task: {error_code} - {str(e)}")
            raise DatabaseConnectionError(f"Failed to update task: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating task: {str(e)}")
            raise DatabaseConnectionError(f"Unexpected error: {str(e)}")
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            bool: 是否删除成功
            
        Raises:
            TaskNotFoundError: 任务不存在
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 首先获取任务以获取 created_at（sort key）
            task = self.get_task(task_id)
            
            # 删除任务
            self.table.delete_item(
                Key={
                    "task_id": task_id,
                    "created_at": task.created_at.isoformat()
                }
            )
            
            logger.info(f"Deleted task: {task_id}")
            return True
            
        except TaskNotFoundError:
            raise
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to delete task: {error_code} - {str(e)}")
            raise DatabaseConnectionError(f"Failed to delete task: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deleting task: {str(e)}")
            raise DatabaseConnectionError(f"Unexpected error: {str(e)}")
    
    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ProcessingTask], Optional[Dict[str, Any]]]:
        """
        列出任务（带过滤和分页）
        
        Args:
            status: 按状态过滤（可选）
            limit: 返回数量限制
            last_evaluated_key: 分页键（上一页的最后一个键）
            
        Returns:
            Tuple[List[ProcessingTask], Optional[Dict]]: 任务列表和下一页的键
            
        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            if status:
                # 使用 GSI 按状态查询
                query_params = {
                    "IndexName": "StatusIndex",
                    "KeyConditionExpression": Key("status").eq(status),
                    "Limit": limit,
                    "ScanIndexForward": False  # 按创建时间降序
                }
                
                if last_evaluated_key:
                    query_params["ExclusiveStartKey"] = last_evaluated_key
                
                response = self.table.query(**query_params)
            else:
                # 扫描所有任务
                scan_params = {
                    "Limit": limit
                }
                
                if last_evaluated_key:
                    scan_params["ExclusiveStartKey"] = last_evaluated_key
                
                response = self.table.scan(**scan_params)
            
            # 转换为任务对象
            tasks = [self._dynamodb_to_task(item) for item in response.get("Items", [])]
            
            # 获取下一页的键
            next_key = response.get("LastEvaluatedKey")
            
            logger.debug(f"Listed {len(tasks)} tasks (status={status})")
            return tasks, next_key
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to list tasks: {error_code} - {str(e)}")
            raise DatabaseConnectionError(f"Failed to list tasks: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error listing tasks: {str(e)}")
            raise DatabaseConnectionError(f"Unexpected error: {str(e)}")
    
    def query_by_batch_job_id(self, batch_job_id: str) -> Optional[ProcessingTask]:
        """
        通过 Batch Job ID 查询任务
        
        Args:
            batch_job_id: AWS Batch Job ID
            
        Returns:
            Optional[ProcessingTask]: 任务对象，如果不存在返回 None
            
        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 使用 GSI 查询
            response = self.table.query(
                IndexName="BatchJobIndex",
                KeyConditionExpression=Key("batch_job_id").eq(batch_job_id),
                Limit=1
            )
            
            items = response.get("Items", [])
            if not items:
                logger.debug(f"No task found for batch job: {batch_job_id}")
                return None
            
            task = self._dynamodb_to_task(items[0])
            logger.debug(f"Found task {task.task_id} for batch job: {batch_job_id}")
            return task
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"Failed to query by batch job ID: {error_code} - {str(e)}")
            raise DatabaseConnectionError(f"Failed to query by batch job ID: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error querying by batch job ID: {str(e)}")
            raise DatabaseConnectionError(f"Unexpected error: {str(e)}")
    
    def _task_to_dynamodb(self, task: ProcessingTask) -> Dict[str, Any]:
        """
        将任务对象转换为 DynamoDB 格式
        
        Args:
            task: 任务对象
            
        Returns:
            Dict: DynamoDB 项
        """
        item = {
            "task_id": task.task_id,
            "created_at": task.created_at.isoformat(),
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "updated_at": task.updated_at.isoformat(),
            "parameters": task.parameters,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries
        }
        
        # 添加可选字段
        if task.batch_job_id:
            item["batch_job_id"] = task.batch_job_id
        
        if task.batch_job_status:
            item["batch_job_status"] = task.batch_job_status
        
        if task.started_at:
            item["started_at"] = task.started_at.isoformat()
        
        if task.completed_at:
            item["completed_at"] = task.completed_at.isoformat()
        
        if task.result:
            item["result"] = task.result.model_dump()
        
        if task.error:
            item["error"] = task.error
        
        return item
    
    def _dynamodb_to_task(self, item: Dict[str, Any]) -> ProcessingTask:
        """
        将 DynamoDB 项转换为任务对象
        
        Args:
            item: DynamoDB 项
            
        Returns:
            ProcessingTask: 任务对象
        """
        # 转换 Decimal 为 int/float
        item = self._convert_decimals(item)
        
        # 解析日期时间
        created_at = datetime.fromisoformat(item["created_at"])
        updated_at = datetime.fromisoformat(item["updated_at"])
        started_at = datetime.fromisoformat(item["started_at"]) if item.get("started_at") else None
        completed_at = datetime.fromisoformat(item["completed_at"]) if item.get("completed_at") else None
        
        # 解析结果
        result = ProcessingResult(**item["result"]) if item.get("result") else None
        
        return ProcessingTask(
            task_id=item["task_id"],
            task_type=item["task_type"],
            status=item["status"],
            progress=item["progress"],
            batch_job_id=item.get("batch_job_id"),
            batch_job_status=item.get("batch_job_status"),
            created_at=created_at,
            updated_at=updated_at,
            started_at=started_at,
            completed_at=completed_at,
            parameters=item["parameters"],
            result=result,
            error=item.get("error"),
            retry_count=item.get("retry_count", 0),
            max_retries=item.get("max_retries", 3)
        )
    
    def _convert_decimals(self, obj: Any) -> Any:
        """
        递归转换 DynamoDB Decimal 类型为 Python 原生类型
        
        Args:
            obj: 要转换的对象
            
        Returns:
            转换后的对象
        """
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            # 转换为 int 或 float
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        else:
            return obj
