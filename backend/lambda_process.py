"""
Lambda handler for processing tasks (submit/query/cancel)
"""
import json
import os
import logging
from datetime import datetime, timezone
from app.services.batch_job_manager import BatchJobManager
from app.services.task_repository import TaskRepository
from app.services.s3_storage_service import S3StorageService
from app.models.processing import ProcessingTask

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

# Initialize services
batch_manager = BatchJobManager(
    job_queue=os.getenv("BATCH_JOB_QUEUE", "satellite-gis-job-queue-dev"),
    job_definition=os.getenv("BATCH_JOB_DEFINITION", "satellite-gis-job-definition-dev"),
    s3_bucket=os.getenv("S3_BUCKET", "satellite-gis-results-dev"),
    region=os.getenv("AWS_REGION", "us-east-1")
)

task_repository = TaskRepository(
    table_name=os.getenv("DYNAMODB_TABLE", "ProcessingTasks-dev"),
    region=os.getenv("AWS_REGION", "us-east-1")
)

s3_service = S3StorageService(
    bucket_name=os.getenv("S3_BUCKET", "satellite-gis-results-dev"),
    region=os.getenv("AWS_REGION", "us-east-1")
)


def handler(event, context):
    """
    Handle processing requests
    
    Routes:
    - POST /api/process/indices - Submit processing job
    - GET /api/process/tasks/{task_id} - Get task status
    - DELETE /api/process/tasks/{task_id} - Cancel task
    """
    try:
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method'))
        path = event.get('path', event.get('rawPath', ''))
        
        # Route to appropriate handler
        if http_method == 'POST' and '/indices' in path:
            return submit_job(event)
        elif http_method == 'GET' and '/tasks/' in path:
            return get_task_status(event)
        elif http_method == 'DELETE' and '/tasks/' in path:
            return cancel_task(event)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        logger.error(f'Handler error: {str(e)}', exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def submit_job(event):
    """Submit processing job to Batch"""
    body = json.loads(event.get('body', '{}'))
    
    # Create task
    task = ProcessingTask(
        task_id="",
        task_type="indices",
        status="queued",
        progress=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        parameters=body
    )
    
    # Save to DynamoDB
    task_id = task_repository.create_task(task)
    task.task_id = task_id
    
    # Submit to Batch
    batch_job_id = batch_manager.submit_job(
        task_id=task_id,
        parameters=body,
        job_name=f"indices-{task_id}",
        retry_attempts=3,
        timeout_seconds=3600
    )
    
    # Update task with batch job ID
    task_repository.update_task_status(
        task_id=task_id,
        status="queued",
        batch_job_id=batch_job_id,
        batch_job_status="SUBMITTED"
    )
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'task_id': task_id,
            'status': 'queued',
            'batch_job_id': batch_job_id,
            'created_at': task.created_at.isoformat(),
            'estimated_time': len(body.get('indices', [])) * 30
        })
    }


def get_task_status(event):
    """Get task status"""
    # Extract task_id from path
    path = event.get('path', event.get('rawPath', ''))
    task_id = path.split('/')[-1]
    
    # Get task from DynamoDB
    task = task_repository.get_task(task_id)
    
    # Query Batch status if available
    if task.batch_job_id:
        batch_status = batch_manager.get_job_status(task.batch_job_id)
        
        # Update task status based on Batch status
        if batch_status['status'] == 'SUCCEEDED' and task.status != 'completed':
            # Generate presigned URLs for results
            output_files = []
            for index in task.parameters.get('indices', []):
                s3_key = f"tasks/{task_id}/{index}.tif"
                if s3_service.file_exists(s3_key):
                    presigned_url = s3_service.generate_presigned_url(s3_key, expiration=3600)
                    file_size = s3_service.get_file_size(s3_key)
                    output_files.append({
                        'name': f"{index}.tif",
                        's3_key': s3_key,
                        'download_url': presigned_url,
                        'size_mb': round(file_size / (1024 * 1024), 2),
                        'index': index
                    })
            
            task_repository.update_task_status(
                task_id=task_id,
                status='completed',
                progress=100,
                result={'output_files': output_files}
            )
            task = task_repository.get_task(task_id)
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(task.model_dump(), default=str)
    }


def cancel_task(event):
    """Cancel task"""
    path = event.get('path', event.get('rawPath', ''))
    task_id = path.split('/')[-1]
    
    task = task_repository.get_task(task_id)
    
    if task.batch_job_id:
        batch_manager.cancel_job(task.batch_job_id, reason="Cancelled by user")
    
    task_repository.update_task_status(
        task_id=task_id,
        status='failed',
        error='Cancelled by user'
    )
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'task_id': task_id, 'status': 'cancelled'})
    }
