"""
Lambda handler for processing tasks (submit/query/cancel)
Standalone version with all dependencies inlined - no app module imports
"""
import json
import os
import logging
import base64
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


def convert_floats_to_decimal(obj: Any) -> Any:
    """Convert all float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


def convert_decimal_to_float(obj: Any) -> Any:
    """Convert all Decimal values to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))


# Security: Log sanitization
def sanitize_log_data(data):
    """Remove sensitive information from log data"""
    if not isinstance(data, dict):
        return data
    
    sensitive_keys = ['password', 'token', 'key', 'secret', 'api_key', 'access_key', 'credentials']
    sanitized = {}
    
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized


def safe_error_response(error: Exception, status_code: int = 500):
    """Return safe error response based on environment"""
    environment = os.getenv('ENVIRONMENT', 'dev')
    
    if environment == 'prod':
        # In production, return generic error
        error_msg = 'Internal server error'
        logger.error(f"Error occurred: {str(error)}", exc_info=True)
    else:
        # In development, return detailed error
        error_msg = str(error)
        logger.error(f"Error occurred: {error_msg}", exc_info=True)
    
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps({'error': error_msg})
    }


# ============================================================================
# Inlined Models (minimal Pydantic-free versions)
# ============================================================================

class ProcessingTask:
    """Processing task model (Pydantic-free)"""
    def __init__(
        self,
        task_id: str,
        task_type: str,
        status: str,
        progress: int,
        created_at: datetime,
        updated_at: datetime,
        parameters: Dict[str, Any],
        batch_job_id: Optional[str] = None,
        batch_job_status: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 3
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.status = status
        self.progress = progress
        self.batch_job_id = batch_job_id
        self.batch_job_status = batch_job_status
        self.created_at = created_at
        self.updated_at = updated_at
        self.started_at = started_at
        self.completed_at = completed_at
        self.parameters = parameters
        self.result = result
        self.error = error
        self.retry_count = retry_count
        self.max_retries = max_retries
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'status': self.status,
            'progress': self.progress,
            'batch_job_id': self.batch_job_id,
            'batch_job_status': self.batch_job_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'parameters': self.parameters,
            'result': self.result,
            'error': self.error,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }


# ============================================================================
# Inlined Services
# ============================================================================

class BatchJobManager:
    """Manages AWS Batch job lifecycle"""
    
    def __init__(self, job_queue: str, job_definition: str, s3_bucket: str, region: str):
        self.job_queue = job_queue
        self.job_definition = job_definition
        self.s3_bucket = s3_bucket
        self.region = region
        self.batch_client = boto3.client('batch', region_name=region)
    
    def submit_job(
        self,
        task_id: str,
        parameters: Dict,
        job_name: str,
        retry_attempts: int = 3,
        timeout_seconds: int = 3600
    ) -> str:
        """Submit a job to AWS Batch"""
        job_name = job_name.replace('_', '-')[:128]
        
        container_overrides = {
            'environment': [
                {'name': 'TASK_ID', 'value': task_id},
                {'name': 'S3_BUCKET', 'value': self.s3_bucket},
                {'name': 'AWS_REGION', 'value': self.region},
            ]
        }
        
        for key, value in parameters.items():
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            container_overrides['environment'].append({
                'name': key.upper(),
                'value': value_str
            })
        
        response = self.batch_client.submit_job(
            jobName=job_name,
            jobQueue=self.job_queue,
            jobDefinition=self.job_definition,
            containerOverrides=container_overrides,
            retryStrategy={'attempts': retry_attempts},
            timeout={'attemptDurationSeconds': timeout_seconds}
        )
        
        return response['jobId']
    
    def get_job_status(self, batch_job_id: str) -> Dict:
        """Get the status of an AWS Batch job"""
        response = self.batch_client.describe_jobs(jobs=[batch_job_id])
        
        if not response['jobs']:
            return {'job_id': batch_job_id, 'status': 'NOT_FOUND'}
        
        job = response['jobs'][0]
        return {
            'job_id': job['jobId'],
            'job_name': job['jobName'],
            'status': job['status'],
            'status_reason': job.get('statusReason', ''),
            'created_at': job.get('createdAt'),
            'started_at': job.get('startedAt'),
            'stopped_at': job.get('stoppedAt'),
        }
    
    def cancel_job(self, batch_job_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel a running AWS Batch job"""
        try:
            self.batch_client.terminate_job(jobId=batch_job_id, reason=reason)
            return True
        except ClientError:
            return False


class TaskRepository:
    """DynamoDB task repository"""
    
    def __init__(self, table_name: str, region: str):
        self.table_name = table_name
        self.region = region
        dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = dynamodb.Table(table_name)
    
    def create_task(self, task: ProcessingTask) -> str:
        """Create a new task"""
        if not task.task_id:
            task.task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        # Security: Reduced TTL from 30 days to 14 days for better data hygiene
        ttl = int((datetime.now(timezone.utc) + timedelta(days=14)).timestamp())
        
        item = self._task_to_dynamodb(task)
        item["ttl"] = ttl
        
        # Convert floats to Decimal for DynamoDB
        item = convert_floats_to_decimal(item)
        
        self.table.put_item(Item=item)
        return task.task_id
    
    def get_task(self, task_id: str) -> ProcessingTask:
        """Get a task by ID"""
        response = self.table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("task_id").eq(task_id),
            Limit=1
        )
        
        items = response.get("Items", [])
        if not items:
            raise ValueError(f"Task not found: {task_id}")
        
        return self._dynamodb_to_task(items[0])
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        batch_job_id: Optional[str] = None,
        batch_job_status: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        retry_count: Optional[int] = None
    ) -> bool:
        """Update task status"""
        task = self.get_task(task_id)
        
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
            expression_attribute_values[":result"] = result
        
        if error is not None:
            update_expression += ", #error = :error"
            expression_attribute_names["#error"] = "error"
            expression_attribute_values[":error"] = error
        
        if retry_count is not None:
            update_expression += ", retry_count = :retry_count"
            expression_attribute_values[":retry_count"] = retry_count
        
        self.table.update_item(
            Key={
                "task_id": task_id,
                "created_at": task.created_at.isoformat()
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        return True
    
    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ProcessingTask], Optional[Dict[str, Any]]]:
        """List tasks with optional filtering and pagination"""
        if status:
            query_params = {
                "IndexName": "StatusIndex",
                "KeyConditionExpression": boto3.dynamodb.conditions.Key("status").eq(status),
                "Limit": limit,
                "ScanIndexForward": False
            }
            
            if last_evaluated_key:
                query_params["ExclusiveStartKey"] = last_evaluated_key
            
            response = self.table.query(**query_params)
        else:
            scan_params = {"Limit": limit}
            
            if last_evaluated_key:
                scan_params["ExclusiveStartKey"] = last_evaluated_key
            
            response = self.table.scan(**scan_params)
        
        tasks = [self._dynamodb_to_task(item) for item in response.get("Items", [])]
        next_key = response.get("LastEvaluatedKey")
        
        return tasks, next_key
    
    def _task_to_dynamodb(self, task: ProcessingTask) -> Dict[str, Any]:
        """Convert task to DynamoDB format"""
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
        
        if task.batch_job_id:
            item["batch_job_id"] = task.batch_job_id
        if task.batch_job_status:
            item["batch_job_status"] = task.batch_job_status
        if task.started_at:
            item["started_at"] = task.started_at.isoformat()
        if task.completed_at:
            item["completed_at"] = task.completed_at.isoformat()
        if task.result:
            item["result"] = task.result
        if task.error:
            item["error"] = task.error
        
        return item
    
    def _dynamodb_to_task(self, item: Dict[str, Any]) -> ProcessingTask:
        """Convert DynamoDB item to task"""
        item = self._convert_decimals(item)
        
        return ProcessingTask(
            task_id=item["task_id"],
            task_type=item["task_type"],
            status=item["status"],
            progress=item["progress"],
            batch_job_id=item.get("batch_job_id"),
            batch_job_status=item.get("batch_job_status"),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            started_at=datetime.fromisoformat(item["started_at"]) if item.get("started_at") else None,
            completed_at=datetime.fromisoformat(item["completed_at"]) if item.get("completed_at") else None,
            parameters=item["parameters"],
            result=item.get("result"),
            error=item.get("error"),
            retry_count=item.get("retry_count", 0),
            max_retries=item.get("max_retries", 3)
        )
    
    def _convert_decimals(self, obj: Any) -> Any:
        """Convert DynamoDB Decimal types to Python native types"""
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        else:
            return obj


class S3StorageService:
    """S3 storage service"""
    
    def __init__(self, bucket_name: str, region: str):
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL"""
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get_file_size(self, s3_key: str) -> int:
        """Get file size in bytes"""
        response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
        return response['ContentLength']


# ============================================================================
# Service Instances (lazy initialization)
# ============================================================================

_batch_manager = None
_task_repository = None
_s3_service = None


def get_batch_manager():
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchJobManager(
            job_queue=os.getenv("BATCH_JOB_QUEUE", "satellite-gis-job-queue-dev"),
            job_definition=os.getenv("BATCH_JOB_DEFINITION", "satellite-gis-job-definition-dev"),
            s3_bucket=os.getenv("S3_BUCKET", "satellite-gis-results-dev"),
            region=os.getenv("AWS_REGION", "us-east-1")
        )
    return _batch_manager


def get_task_repository():
    global _task_repository
    if _task_repository is None:
        _task_repository = TaskRepository(
            table_name=os.getenv("DYNAMODB_TABLE", "ProcessingTasks-dev"),
            region=os.getenv("AWS_REGION", "us-east-1")
        )
    return _task_repository


def get_s3_service():
    global _s3_service
    if _s3_service is None:
        _s3_service = S3StorageService(
            bucket_name=os.getenv("S3_BUCKET", "satellite-gis-results-dev"),
            region=os.getenv("AWS_REGION", "us-east-1")
        )
    return _s3_service


# ============================================================================
# Lambda Handler
# ============================================================================

def cors_headers():
    """Return CORS headers"""
    # Read allowed origins from environment variable
    # In production, this should be set to your frontend domain
    allowed_origins = os.getenv('CORS_ORIGINS', '*')
    
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': allowed_origins,
        'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Credentials': 'true' if allowed_origins != '*' else 'false'
    }


def health_check():
    """Health check endpoint"""
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({
            'status': 'healthy',
            'service': 'satellite-gis-process-lambda',
            'version': '2.0.0-standalone'
        })
    }


def handler(event, context):
    """
    Handle processing requests
    
    Routes:
    - POST /api/process/indices - Submit processing job
    - GET /api/process/tasks - List all tasks (with filtering/pagination)
    - GET /api/process/tasks/{task_id} - Get task status
    - DELETE /api/process/tasks/{task_id} - Cancel task
    - GET /health - Health check
    """
    try:
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method'))
        path = event.get('path', event.get('rawPath', ''))
        
        logger.info(f"Process handler: method={http_method}, path={path}")
        
        # Health check
        if path in ['/', '/health'] and http_method == 'GET':
            return health_check()
        
        # OPTIONS for CORS
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': ''
            }
        
        # Route to appropriate handler
        if http_method == 'POST' and '/indices' in path:
            return submit_indices_job(event)
        elif http_method == 'POST' and '/composite' in path:
            return submit_composite_job(event)
        elif http_method == 'GET' and '/tasks' in path:
            path_parts = path.rstrip('/').split('/')
            if path_parts[-1] == 'tasks':
                return list_tasks(event)
            else:
                return get_task_status(event)
        elif http_method == 'DELETE' and '/tasks/' in path:
            return cancel_task(event)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        logger.error(f'Handler error: {str(e)}', exc_info=True)
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def submit_indices_job(event):
    """Submit vegetation indices processing job to Batch"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Convert floats to Decimal for DynamoDB compatibility
        body = convert_floats_to_decimal(body)
        
        # Security: Sanitize log data
        logger.info(f"Submitting job with parameters: {json.dumps(sanitize_log_data(body), default=str)}")
        
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
        task_repository = get_task_repository()
        task_id = task_repository.create_task(task)
        task.task_id = task_id
        
        logger.info(f"Created task in DynamoDB: {task_id}")
        
        # Submit to Batch (convert Decimals back to floats for JSON serialization)
        batch_manager = get_batch_manager()
        batch_parameters = convert_decimal_to_float(body)
        batch_job_id = batch_manager.submit_job(
            task_id=task_id,
            parameters=batch_parameters,
            job_name=f"indices-{task_id}",
            retry_attempts=3,
            timeout_seconds=3600
        )
        
        logger.info(f"Submitted Batch job: {batch_job_id} for task: {task_id}")
        
        # Update task with batch job ID
        task_repository.update_task_status(
            task_id=task_id,
            status="queued",
            batch_job_id=batch_job_id,
            batch_job_status="SUBMITTED"
        )
        
        logger.info(f"Updated task {task_id} with batch_job_id: {batch_job_id}")
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'task_id': task_id,
                'status': 'queued',
                'batch_job_id': batch_job_id,
                'created_at': task.created_at.isoformat(),
                'estimated_time': len(body.get('indices', [])) * 30
            })
        }
    except Exception as e:
        logger.error(f"Submit job error: {str(e)}", exc_info=True)
        return safe_error_response(e)


def submit_composite_job(event):
    """
    Submit temporal composite job to Batch.

    Expected body:
    {
        "satellite": "sentinel-2",
        "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
        "aoi": { GeoJSON },
        "composite_mode": "monthly",
        "apply_cloud_mask": true,
        "indices": ["NDVI"],           // optional: compute indices on composites
        "image_urls": ["https://..."],  // band URLs for each image
        "image_timestamps": ["2024-01-05T00:00:00Z", ...],
        "qa_band_urls": ["https://...", ...]  // optional: QA band per image
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        body = convert_floats_to_decimal(body)

        logger.info(f"Submitting composite job: {json.dumps(body, default=str)}")

        # Validate required fields
        if not body.get('image_urls'):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'image_urls is required'})
            }
        if not body.get('image_timestamps'):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'image_timestamps is required'})
            }
        if not body.get('aoi'):
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'aoi is required'})
            }

        # Add task_type for the batch processor
        body['task_type'] = 'composite'

        task = ProcessingTask(
            task_id="",
            task_type="composite",
            status="queued",
            progress=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            parameters=body
        )

        task_repository = get_task_repository()
        task_id = task_repository.create_task(task)
        task.task_id = task_id

        logger.info(f"Created composite task in DynamoDB: {task_id}")

        # Composite jobs may take longer — give 2 hours
        batch_manager = get_batch_manager()
        batch_parameters = convert_decimal_to_float(body)
        batch_job_id = batch_manager.submit_job(
            task_id=task_id,
            parameters=batch_parameters,
            job_name=f"composite-{task_id}",
            retry_attempts=2,
            timeout_seconds=7200
        )

        logger.info(f"Submitted Batch composite job: {batch_job_id}")

        task_repository.update_task_status(
            task_id=task_id,
            status="queued",
            batch_job_id=batch_job_id,
            batch_job_status="SUBMITTED"
        )

        num_images = len(body.get('image_urls', []))
        estimated_time = max(60, num_images * 20)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'task_id': task_id,
                'task_type': 'composite',
                'status': 'queued',
                'batch_job_id': batch_job_id,
                'created_at': task.created_at.isoformat(),
                'composite_mode': body.get('composite_mode', 'monthly'),
                'num_images': num_images,
                'estimated_time': estimated_time
            })
        }
    except Exception as e:
        logger.error(f"Submit composite job error: {str(e)}", exc_info=True)
        return safe_error_response(e)


def get_task_status(event):
    """Get task status"""
    try:
        path = event.get('path', event.get('rawPath', ''))
        task_id = path.split('/')[-1]
        
        logger.info(f"Getting task status for: {task_id}")
        
        task_repository = get_task_repository()
        task = task_repository.get_task(task_id)
        
        # Query Batch status if available
        if task.batch_job_id:
            batch_manager = get_batch_manager()
            batch_status = batch_manager.get_job_status(task.batch_job_id)
            
            logger.info(f"Batch status for {task.batch_job_id}: {batch_status['status']}")
            
            # Update batch_job_status in task
            if batch_status['status'] != task.batch_job_status:
                task_repository.update_task_status(
                    task_id=task_id,
                    status=task.status,
                    batch_job_status=batch_status['status']
                )
            
            # Map Batch status to task status
            batch_to_task_status = {
                'SUBMITTED': 'queued',
                'PENDING': 'queued',
                'RUNNABLE': 'queued',
                'STARTING': 'running',
                'RUNNING': 'running',
                'SUCCEEDED': 'completed',
                'FAILED': 'failed'
            }
            
            new_task_status = batch_to_task_status.get(batch_status['status'], task.status)
            
            # Update task status based on Batch status
            if new_task_status == 'completed' and task.status != 'completed':
                s3_service = get_s3_service()
                output_files = []
                for index in task.parameters.get('indices', []):
                    s3_key = f"tasks/{task_id}/{index}.tif"
                    if s3_service.file_exists(s3_key):
                        presigned_url = s3_service.generate_presigned_url(s3_key, expiration=14400)  # 4 hours
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
                    batch_job_status=batch_status['status'],
                    completed_at=datetime.now(timezone.utc),
                    result={'output_files': output_files}
                )
                task = task_repository.get_task(task_id)
            elif new_task_status == 'failed' and task.status != 'failed':
                task_repository.update_task_status(
                    task_id=task_id,
                    status='failed',
                    batch_job_status=batch_status['status'],
                    completed_at=datetime.now(timezone.utc),
                    error=batch_status.get('status_reason', 'Batch job failed')
                )
                task = task_repository.get_task(task_id)
            elif new_task_status == 'running' and task.status == 'queued':
                task_repository.update_task_status(
                    task_id=task_id,
                    status='running',
                    progress=50,
                    batch_job_status=batch_status['status'],
                    started_at=datetime.now(timezone.utc)
                )
                task = task_repository.get_task(task_id)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(task.to_dict(), default=str)
        }
    except ValueError as e:
        logger.error(f"Task not found: {str(e)}")
        return {
            'statusCode': 404,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Task not found', 'task_id': task_id})
        }
    except Exception as e:
        logger.error(f"Get task status error: {str(e)}", exc_info=True)
        return safe_error_response(e)


def cancel_task(event):
    """Cancel task"""
    try:
        path = event.get('path', event.get('rawPath', ''))
        task_id = path.split('/')[-1]
        
        logger.info(f"Cancelling task: {task_id}")
        
        task_repository = get_task_repository()
        task = task_repository.get_task(task_id)
        
        if task.batch_job_id:
            batch_manager = get_batch_manager()
            success = batch_manager.cancel_job(task.batch_job_id, reason="Cancelled by user")
            if not success:
                logger.warning(f"Failed to cancel batch job {task.batch_job_id}")
        
        task_repository.update_task_status(
            task_id=task_id,
            status='failed',
            error='Cancelled by user',
            completed_at=datetime.now(timezone.utc)
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'task_id': task_id, 'status': 'cancelled'})
        }
    except ValueError as e:
        logger.error(f"Task not found: {str(e)}")
        return {
            'statusCode': 404,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Task not found', 'task_id': task_id})
        }
    except Exception as e:
        logger.error(f"Cancel task error: {str(e)}", exc_info=True)
        return safe_error_response(e)


def list_tasks(event):
    """List all tasks with optional filtering and pagination"""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        status_filter = query_params.get('status')
        limit = int(query_params.get('limit', 20))
        offset = query_params.get('offset')
        
        if limit < 1 or limit > 100:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'limit must be between 1 and 100'})
            }
        
        if status_filter and status_filter not in ['queued', 'running', 'completed', 'failed']:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Invalid status. Must be one of: queued, running, completed, failed'
                })
            }
        
        last_evaluated_key = None
        if offset:
            try:
                last_evaluated_key = json.loads(base64.b64decode(offset))
            except Exception as e:
                logger.warning(f"Invalid offset key: {e}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'Invalid offset key'})
                }
        
        task_repository = get_task_repository()
        tasks, next_key = task_repository.list_tasks(
            status=status_filter,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        next_offset = None
        if next_key:
            next_offset = base64.b64encode(json.dumps(next_key).encode()).decode()
        
        tasks_data = [task.to_dict() for task in tasks]
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'tasks': tasks_data,
                'total': len(tasks_data),
                'limit': limit,
                'offset': offset,
                'next_offset': next_offset
            }, default=str)
        }
        
    except Exception as e:
        logger.error(f'List tasks error: {str(e)}', exc_info=True)
        return safe_error_response(e)
