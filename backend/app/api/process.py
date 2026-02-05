"""
数据处理 API 端点
"""
import os
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from app.models.processing import (
    IndicesProcessingRequest,
    IndicesProcessingResponse,
    ProcessingTask,
    TaskListResponse
)
from app.services.batch_job_manager import BatchJobManager
from app.services.task_repository import TaskRepository, TaskNotFoundError, DatabaseConnectionError
from app.services.s3_storage_service import S3StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/process", tags=["processing"])

# 初始化服务（从环境变量读取配置）
try:
    batch_manager = BatchJobManager(
        job_queue=os.getenv("AWS_BATCH_JOB_QUEUE", "satellite-gis-job-queue"),
        job_definition=os.getenv("AWS_BATCH_JOB_DEFINITION", "satellite-gis-job-definition"),
        s3_bucket=os.getenv("S3_RESULTS_BUCKET", "satellite-gis-results"),
        region=os.getenv("AWS_REGION", "us-west-2")
    )
    
    task_repository = TaskRepository(
        table_name=os.getenv("DYNAMODB_TABLE", "ProcessingTasks"),
        region=os.getenv("AWS_REGION", "us-west-2")
    )
    
    s3_service = S3StorageService(
        bucket_name=os.getenv("S3_RESULTS_BUCKET", "satellite-gis-results"),
        region=os.getenv("AWS_REGION", "us-west-2")
    )
    
    BATCH_AVAILABLE = True
    logger.info("AWS Batch integration initialized successfully")
    
except Exception as e:
    BATCH_AVAILABLE = False
    logger.warning(f"AWS Batch integration not available: {e}")
    batch_manager = None
    task_repository = None
    s3_service = None


@router.post("/indices", response_model=IndicesProcessingResponse)
async def process_vegetation_indices(request: IndicesProcessingRequest):
    """
    计算植被指数（提交到 AWS Batch）
    
    创建任务并提交到 AWS Batch 进行异步处理。
    
    Args:
        request: 植被指数计算请求
        
    Returns:
        IndicesProcessingResponse: 任务信息
        
    验证: 需求 5.1, 5.8, 5.9, 10.1
    """
    # 检查 AWS Batch 是否可用
    if not BATCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AWS Batch integration is not available. Please check configuration."
        )
    
    try:
        # 验证请求
        if not request.indices:
            raise HTTPException(
                status_code=400,
                detail="At least one vegetation index must be specified"
            )
        
        # 创建任务记录
        task = ProcessingTask(
            task_id="",  # 将由 repository 生成
            task_type="indices",
            status="queued",
            progress=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            parameters=request.model_dump()
        )
        
        # 保存到数据库
        task_id = task_repository.create_task(task)
        task.task_id = task_id
        
        # 提交到 AWS Batch
        try:
            batch_job_id = batch_manager.submit_job(
                task_id=task_id,
                parameters=request.model_dump(),
                job_name=f"indices-{task_id}",
                retry_attempts=3,
                timeout_seconds=3600  # 1 hour timeout
            )
            
            # 更新任务的 batch_job_id
            task_repository.update_task_status(
                task_id=task_id,
                status="queued",
                batch_job_id=batch_job_id,
                batch_job_status="SUBMITTED"
            )
            
            logger.info(f"Submitted task {task_id} to AWS Batch: {batch_job_id}")
            
        except Exception as e:
            # 如果提交失败，更新任务状态为失败
            task_repository.update_task_status(
                task_id=task_id,
                status="failed",
                error=f"Failed to submit to AWS Batch: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to submit job to AWS Batch: {str(e)}"
            )
        
        # 估算处理时间（简单估算：每个指数 30 秒）
        estimated_time = len(request.indices) * 30
        
        return IndicesProcessingResponse(
            task_id=task_id,
            status="queued",
            batch_job_id=batch_job_id,
            created_at=task.created_at,
            estimated_time=estimated_time
        )
        
    except HTTPException:
        raise
    except DatabaseConnectionError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create processing task: {str(e)}"
        )



@router.get("/tasks/{task_id}", response_model=ProcessingTask)
async def get_task_status(task_id: str):
    """
    查询任务状态（包含 AWS Batch 状态）
    
    获取指定任务的当前状态、进度和结果。同时查询 AWS Batch 的最新状态。
    
    Args:
        task_id: 任务 ID
        
    Returns:
        ProcessingTask: 任务信息
        
    验证: 需求 4.5, 10.4, 10.5
    """
    if not BATCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AWS Batch integration is not available"
        )
    
    try:
        # 从数据库获取任务
        task = task_repository.get_task(task_id)
        
        # 如果任务有 batch_job_id，查询 Batch 状态
        if task.batch_job_id:
            try:
                batch_status = batch_manager.get_job_status(task.batch_job_id)
                
                # 更新任务的 batch_job_status
                if batch_status['status'] != task.batch_job_status:
                    # Batch 状态已变化，更新数据库
                    update_kwargs = {
                        'batch_job_status': batch_status['status']
                    }
                    
                    # 映射 Batch 状态到任务状态
                    if batch_status['status'] in ['SUBMITTED', 'PENDING', 'RUNNABLE']:
                        update_kwargs['status'] = 'queued'
                    elif batch_status['status'] in ['STARTING', 'RUNNING']:
                        update_kwargs['status'] = 'running'
                        if not task.started_at and batch_status.get('started_at'):
                            update_kwargs['started_at'] = datetime.fromtimestamp(
                                batch_status['started_at'] / 1000, tz=timezone.utc
                            )
                    elif batch_status['status'] == 'SUCCEEDED':
                        update_kwargs['status'] = 'completed'
                        update_kwargs['progress'] = 100
                        if batch_status.get('stopped_at'):
                            update_kwargs['completed_at'] = datetime.fromtimestamp(
                                batch_status['stopped_at'] / 1000, tz=timezone.utc
                            )
                        
                        # 生成结果文件的预签名 URL
                        if not task.result:
                            output_files = []
                            for index in task.parameters.get('indices', []):
                                s3_key = f"tasks/{task_id}/{index}.tif"
                                if s3_service.file_exists(s3_key):
                                    presigned_url = s3_service.generate_presigned_url(
                                        s3_key, expiration=3600
                                    )
                                    file_size = s3_service.get_file_size(s3_key)
                                    output_files.append({
                                        'name': f"{index}.tif",
                                        's3_key': s3_key,
                                        's3_url': f"s3://{s3_service.bucket_name}/{s3_key}",
                                        'download_url': presigned_url,
                                        'size_mb': round(file_size / (1024 * 1024), 2),
                                        'index': index
                                    })
                            
                            if output_files:
                                from app.models.processing import ProcessingResult
                                update_kwargs['result'] = ProcessingResult(
                                    output_files=output_files,
                                    metadata={'batch_job_id': task.batch_job_id}
                                )
                    
                    elif batch_status['status'] == 'FAILED':
                        update_kwargs['status'] = 'failed'
                        error_msg = batch_status.get('status_reason', 'Job failed')
                        if 'container' in batch_status:
                            error_msg += f" - {batch_status['container'].get('reason', '')}"
                        update_kwargs['error'] = error_msg
                    
                    # 更新数据库
                    task_repository.update_task_status(task_id=task_id, **update_kwargs)
                    
                    # 重新获取更新后的任务
                    task = task_repository.get_task(task_id)
                
            except Exception as e:
                logger.warning(f"Failed to query Batch status for task {task_id}: {e}")
                # 继续返回数据库中的任务状态
        
        return task
        
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    except DatabaseConnectionError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )



@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status (queued, running, completed, failed)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of tasks to return"),
    offset: Optional[str] = Query(None, description="Pagination offset key")
):
    """
    列出所有任务（带过滤和分页）
    
    Args:
        status: 按状态过滤（可选）
        limit: 返回的最大任务数（1-100）
        offset: 分页偏移键（上一页的 last_evaluated_key）
        
    Returns:
        TaskListResponse: 任务列表和分页信息
        
    验证: 需求 10.4, 10.5
    """
    if not BATCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AWS Batch integration is not available"
        )
    
    try:
        # 验证状态参数
        if status and status not in ['queued', 'running', 'completed', 'failed']:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be one of: queued, running, completed, failed"
            )
        
        # 解析分页键
        last_evaluated_key = None
        if offset:
            try:
                import json
                import base64
                last_evaluated_key = json.loads(base64.b64decode(offset))
            except Exception as e:
                logger.warning(f"Invalid offset key: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid offset key"
                )
        
        # 查询任务
        tasks, next_key = task_repository.list_tasks(
            status=status,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        # 编码下一页的键
        next_offset = None
        if next_key:
            import json
            import base64
            next_offset = base64.b64encode(json.dumps(next_key).encode()).decode()
        
        return TaskListResponse(
            tasks=tasks,
            total=len(tasks),
            limit=limit,
            offset=offset,
            next_offset=next_offset
        )
        
    except HTTPException:
        raise
    except DatabaseConnectionError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tasks: {str(e)}"
        )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    取消任务
    
    取消正在运行或排队的任务。如果任务已提交到 AWS Batch，
    将同时取消 Batch 作业。
    
    Args:
        task_id: 任务 ID
        
    Returns:
        dict: 取消结果
        
    验证: 需求 10.1, 10.5
    """
    if not BATCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AWS Batch integration is not available"
        )
    
    try:
        # 获取任务
        task = task_repository.get_task(task_id)
        
        # 检查任务状态
        if task.status in ['completed', 'failed']:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in status: {task.status}"
            )
        
        # 如果有 batch_job_id，取消 Batch 作业
        if task.batch_job_id:
            try:
                cancelled = batch_manager.cancel_job(
                    batch_job_id=task.batch_job_id,
                    reason=f"Cancelled by user via API"
                )
                
                if cancelled:
                    logger.info(f"Cancelled Batch job {task.batch_job_id} for task {task_id}")
                else:
                    logger.warning(f"Failed to cancel Batch job {task.batch_job_id}")
                    
            except Exception as e:
                logger.error(f"Error cancelling Batch job: {e}")
                # 继续更新任务状态，即使 Batch 取消失败
        
        # 更新任务状态为失败（取消视为失败）
        task_repository.update_task_status(
            task_id=task_id,
            status='failed',
            error='Cancelled by user',
            completed_at=datetime.now(timezone.utc)
        )
        
        return {
            'task_id': task_id,
            'status': 'cancelled',
            'message': 'Task cancelled successfully'
        }
        
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    except HTTPException:
        raise
    except DatabaseConnectionError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error cancelling task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )

