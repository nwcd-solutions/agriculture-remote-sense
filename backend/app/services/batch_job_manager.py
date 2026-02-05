"""
AWS Batch Job Manager

This module provides the BatchJobManager class for managing AWS Batch jobs,
including job submission, status querying, and cancellation.

Requirements: 10.1, 10.2, 10.6, 10.7
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class BatchJobManager:
    """
    Manages AWS Batch job lifecycle including submission, status tracking, and cancellation.
    
    This class provides methods to interact with AWS Batch service for submitting
    processing jobs, querying their status, and canceling running jobs.
    """
    
    def __init__(
        self,
        job_queue: str,
        job_definition: str,
        s3_bucket: str,
        region: str = None
    ):
        """
        Initialize the BatchJobManager.
        
        Args:
            job_queue: Name or ARN of the AWS Batch job queue
            job_definition: Name or ARN of the AWS Batch job definition
            s3_bucket: S3 bucket name for storing results
            region: AWS region (defaults to AWS_REGION env var or us-west-2)
        """
        self.job_queue = job_queue
        self.job_definition = job_definition
        self.s3_bucket = s3_bucket
        self.region = region or os.getenv('AWS_REGION', 'us-west-2')
        
        # Initialize AWS Batch client
        try:
            self.batch_client = boto3.client('batch', region_name=self.region)
            logger.info(f"Initialized BatchJobManager with queue={job_queue}, region={self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Batch client: {e}")
            raise
    
    def submit_job(
        self,
        task_id: str,
        parameters: Dict,
        job_name: Optional[str] = None,
        retry_attempts: int = 3,
        timeout_seconds: int = 3600
    ) -> str:
        """
        Submit a job to AWS Batch.
        
        Args:
            task_id: Unique task identifier
            parameters: Job parameters to pass to the container
            job_name: Optional custom job name (defaults to task_id)
            retry_attempts: Number of retry attempts on failure (default: 3)
            timeout_seconds: Job timeout in seconds (default: 3600 = 1 hour)
        
        Returns:
            str: AWS Batch job ID
        
        Raises:
            ClientError: If AWS Batch API call fails
            ValueError: If parameters are invalid
        
        Requirements: 10.1, 10.2, 10.6
        """
        if not task_id:
            raise ValueError("task_id is required")
        
        if not parameters:
            raise ValueError("parameters dictionary is required")
        
        # Use task_id as job name if not provided
        if not job_name:
            job_name = f"task-{task_id}"
        
        # Sanitize job name (AWS Batch allows alphanumeric, hyphens, underscores)
        job_name = job_name.replace('_', '-')[:128]
        
        # Prepare container overrides with environment variables
        container_overrides = {
            'environment': [
                {'name': 'TASK_ID', 'value': task_id},
                {'name': 'S3_BUCKET', 'value': self.s3_bucket},
                {'name': 'AWS_REGION', 'value': self.region},
            ]
        }
        
        # Add all parameters as environment variables
        for key, value in parameters.items():
            # Convert value to string for environment variable
            if isinstance(value, (dict, list)):
                import json
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            container_overrides['environment'].append({
                'name': key.upper(),
                'value': value_str
            })
        
        # Configure retry strategy
        retry_strategy = {
            'attempts': retry_attempts
        }
        
        # Configure timeout
        timeout = {
            'attemptDurationSeconds': timeout_seconds
        }
        
        try:
            logger.info(f"Submitting job to AWS Batch: task_id={task_id}, job_name={job_name}")
            
            response = self.batch_client.submit_job(
                jobName=job_name,
                jobQueue=self.job_queue,
                jobDefinition=self.job_definition,
                containerOverrides=container_overrides,
                retryStrategy=retry_strategy,
                timeout=timeout
            )
            
            batch_job_id = response['jobId']
            logger.info(f"Successfully submitted job: batch_job_id={batch_job_id}, task_id={task_id}")
            
            return batch_job_id
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS Batch ClientError: {error_code} - {error_message}")
            raise
        except BotoCoreError as e:
            logger.error(f"AWS Batch BotoCoreError: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error submitting job: {e}")
            raise
    
    def get_job_status(self, batch_job_id: str) -> Dict:
        """
        Get the status of an AWS Batch job.
        
        Args:
            batch_job_id: AWS Batch job ID
        
        Returns:
            dict: Job status information containing:
                - job_id: AWS Batch job ID
                - job_name: Job name
                - status: Job status (SUBMITTED, PENDING, RUNNABLE, STARTING, RUNNING, SUCCEEDED, FAILED)
                - status_reason: Reason for current status (if available)
                - created_at: Job creation timestamp
                - started_at: Job start timestamp (if started)
                - stopped_at: Job stop timestamp (if stopped)
                - container: Container information (exit code, reason, log stream)
        
        Raises:
            ClientError: If AWS Batch API call fails
            ValueError: If batch_job_id is invalid
        
        Requirements: 10.1, 10.5, 10.7
        """
        if not batch_job_id:
            raise ValueError("batch_job_id is required")
        
        try:
            logger.debug(f"Querying job status: batch_job_id={batch_job_id}")
            
            response = self.batch_client.describe_jobs(jobs=[batch_job_id])
            
            if not response['jobs']:
                logger.warning(f"Job not found: batch_job_id={batch_job_id}")
                return {
                    'job_id': batch_job_id,
                    'status': 'NOT_FOUND',
                    'status_reason': 'Job not found in AWS Batch'
                }
            
            job = response['jobs'][0]
            
            # Extract job information
            job_status = {
                'job_id': job['jobId'],
                'job_name': job['jobName'],
                'status': job['status'],
                'status_reason': job.get('statusReason', ''),
                'created_at': job.get('createdAt'),
                'started_at': job.get('startedAt'),
                'stopped_at': job.get('stoppedAt'),
            }
            
            # Add container information if available
            if 'container' in job:
                container = job['container']
                job_status['container'] = {
                    'exit_code': container.get('exitCode'),
                    'reason': container.get('reason', ''),
                    'log_stream_name': container.get('logStreamName', '')
                }
            
            # Add attempts information
            if 'attempts' in job:
                job_status['attempts'] = len(job['attempts'])
                if job['attempts']:
                    last_attempt = job['attempts'][-1]
                    if 'container' in last_attempt:
                        job_status['last_attempt_exit_code'] = last_attempt['container'].get('exitCode')
                        job_status['last_attempt_reason'] = last_attempt['container'].get('reason', '')
            
            logger.debug(f"Job status retrieved: {job_status['status']}")
            
            return job_status
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS Batch ClientError: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting job status: {e}")
            raise
    
    def cancel_job(self, batch_job_id: str, reason: str = "Cancelled by user") -> bool:
        """
        Cancel a running AWS Batch job.
        
        Args:
            batch_job_id: AWS Batch job ID
            reason: Reason for cancellation
        
        Returns:
            bool: True if cancellation was successful, False otherwise
        
        Raises:
            ClientError: If AWS Batch API call fails
            ValueError: If batch_job_id is invalid
        
        Requirements: 10.1
        """
        if not batch_job_id:
            raise ValueError("batch_job_id is required")
        
        try:
            logger.info(f"Cancelling job: batch_job_id={batch_job_id}, reason={reason}")
            
            # First check if job exists and is in a cancellable state
            job_status = self.get_job_status(batch_job_id)
            
            if job_status['status'] == 'NOT_FOUND':
                logger.warning(f"Cannot cancel job - not found: {batch_job_id}")
                return False
            
            # Jobs can only be cancelled if they are in certain states
            cancellable_states = ['SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING', 'RUNNING']
            if job_status['status'] not in cancellable_states:
                logger.warning(
                    f"Cannot cancel job in state {job_status['status']}: {batch_job_id}"
                )
                return False
            
            # Terminate the job
            self.batch_client.terminate_job(
                jobId=batch_job_id,
                reason=reason
            )
            
            logger.info(f"Successfully cancelled job: {batch_job_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS Batch ClientError: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error cancelling job: {e}")
            raise
    
    def list_jobs(
        self,
        status: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        List AWS Batch jobs in the configured queue.
        
        Args:
            status: Filter by job status (SUBMITTED, PENDING, RUNNABLE, STARTING, 
                   RUNNING, SUCCEEDED, FAILED). If None, returns jobs in all states.
            max_results: Maximum number of results to return (default: 100)
        
        Returns:
            list: List of job summary dictionaries containing:
                - job_id: AWS Batch job ID
                - job_name: Job name
                - status: Job status
                - created_at: Job creation timestamp
                - started_at: Job start timestamp (if started)
                - stopped_at: Job stop timestamp (if stopped)
        
        Raises:
            ClientError: If AWS Batch API call fails
        
        Requirements: 10.5
        """
        try:
            # If status is provided, query that specific status
            if status:
                valid_statuses = [
                    'SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING',
                    'RUNNING', 'SUCCEEDED', 'FAILED'
                ]
                if status not in valid_statuses:
                    raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
                
                logger.debug(f"Listing jobs with status={status}")
                
                response = self.batch_client.list_jobs(
                    jobQueue=self.job_queue,
                    jobStatus=status,
                    maxResults=max_results
                )
            else:
                # Query all active jobs (not SUCCEEDED or FAILED)
                logger.debug("Listing all active jobs")
                
                response = self.batch_client.list_jobs(
                    jobQueue=self.job_queue,
                    maxResults=max_results
                )
            
            jobs = []
            for job_summary in response.get('jobSummaryList', []):
                jobs.append({
                    'job_id': job_summary['jobId'],
                    'job_name': job_summary['jobName'],
                    'status': job_summary['status'],
                    'created_at': job_summary.get('createdAt'),
                    'started_at': job_summary.get('startedAt'),
                    'stopped_at': job_summary.get('stoppedAt'),
                })
            
            logger.debug(f"Found {len(jobs)} jobs")
            
            return jobs
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS Batch ClientError: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing jobs: {e}")
            raise
