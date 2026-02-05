"""
任务管理服务

管理异步处理任务的状态和结果
"""
import uuid
from datetime import datetime
from typing import Dict, Optional
from app.models.processing import ProcessingTask, ProcessingResult


class TaskManager:
    """
    任务管理器类
    
    使用内存存储管理任务状态（生产环境应使用数据库或 Redis）
    """
    
    def __init__(self):
        """初始化任务管理器"""
        self._tasks: Dict[str, ProcessingTask] = {}
    
    def create_task(
        self,
        task_type: str,
        parameters: Dict
    ) -> ProcessingTask:
        """
        创建新任务
        
        Args:
            task_type: 任务类型（indices, composite, download）
            parameters: 任务参数
            
        Returns:
            ProcessingTask: 创建的任务对象
        """
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        task = ProcessingTask(
            task_id=task_id,
            task_type=task_type,
            status="queued",
            progress=0,
            created_at=now,
            updated_at=now,
            parameters=parameters
        )
        
        self._tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """
        获取任务信息
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Optional[ProcessingTask]: 任务对象，如果不存在则返回 None
        """
        return self._tasks.get(task_id)
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        result: Optional[ProcessingResult] = None,
        error: Optional[str] = None
    ) -> Optional[ProcessingTask]:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            status: 新状态
            progress: 进度（0-100）
            result: 处理结果
            error: 错误信息
            
        Returns:
            Optional[ProcessingTask]: 更新后的任务对象
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None
        
        task.status = status
        task.updated_at = datetime.utcnow()
        
        if progress is not None:
            task.progress = progress
        
        if result is not None:
            task.result = result
        
        if error is not None:
            task.error = error
        
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            bool: 是否成功删除
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
    
    def list_tasks(self, limit: int = 100) -> list[ProcessingTask]:
        """
        列出所有任务
        
        Args:
            limit: 返回的最大任务数
            
        Returns:
            list[ProcessingTask]: 任务列表
        """
        tasks = list(self._tasks.values())
        # 按创建时间倒序排序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]


# 全局任务管理器实例
task_manager = TaskManager()
