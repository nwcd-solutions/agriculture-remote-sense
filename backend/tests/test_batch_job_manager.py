"""
Unit tests for BatchJobManager

Tests the AWS Batch job management functionality including job submission,
status querying, and cancellation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
import json

from app.services.batch_job_manager import BatchJobManager


@pytest.fixture
def batch_manager():
    """Create a BatchJobManager instance for testing."""
    with patch('app.services.batch_job_manager.boto3.client') as mock_boto3:
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        
        manager = BatchJobManager(
            job_queue='test-queue',
            job_definition='test-definition',
            s3_bucket='test-bucket',
            region='us-west-2'
        )
        manager.batch_client = mock_client
        
        return manager


class TestBatchJobManagerInit:
    """Test BatchJobManager initialization."""
    
    def test_init_with_all_parameters(self):
        """Test initialization with all parameters."""
        with patch('app.services.batch_job_manager.boto3.client') as mock_boto3:
            manager = BatchJobManager(
                job_queue='my-queue',
                job_definition='my-definition',
                s3_bucket='my-bucket',
                region='us-east-1'
            )
            
            assert manager.job_queue == 'my-queue'
            assert manager.job_definition == 'my-definition'
            assert manager.s3_bucket == 'my-bucket'
            assert manager.region == 'us-east-1'
            mock_boto3.assert_called_once_with('batch', region_name='us-east-1')
    
    def test_init_default_region(self):
        """Test initialization with default region."""
        with patch('app.services.batch_job_manager.boto3.client') as mock_boto3:
            with patch.dict('os.environ', {}, clear=True):
                manager = BatchJobManager(
                    job_queue='my-queue',
                    job_definition='my-definition',
                    s3_bucket='my-bucket'
                )
                
                assert manager.region == 'us-west-2'


class TestSubmitJob:
    """Test job submission functionality."""
    
    def test_submit_job_success(self, batch_manager):
        """Test successful job submission."""
        # Mock the submit_job response
        batch_manager.batch_client.submit_job.return_value = {
            'jobId': 'test-job-123',
            'jobName': 'task-test-task-1'
        }
        
        task_id = 'test-task-1'
        parameters = {
            'image_id': 'S2A_MSIL2A_20240101',
            'indices': ['NDVI', 'SAVI'],
            'aoi': {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        }
        
        batch_job_id = batch_manager.submit_job(task_id, parameters)
        
        assert batch_job_id == 'test-job-123'
        
        # Verify the submit_job was called with correct parameters
        call_args = batch_manager.batch_client.submit_job.call_args
        assert call_args[1]['jobName'] == 'task-test-task-1'
        assert call_args[1]['jobQueue'] == 'test-queue'
        assert call_args[1]['jobDefinition'] == 'test-definition'
        
        # Check environment variables
        env_vars = call_args[1]['containerOverrides']['environment']
        env_dict = {item['name']: item['value'] for item in env_vars}
        assert env_dict['TASK_ID'] == task_id
        assert env_dict['S3_BUCKET'] == 'test-bucket'
        assert env_dict['IMAGE_ID'] == 'S2A_MSIL2A_20240101'
        assert 'NDVI' in env_dict['INDICES']
    
    def test_submit_job_with_custom_name(self, batch_manager):
        """Test job submission with custom job name."""
        batch_manager.batch_client.submit_job.return_value = {
            'jobId': 'test-job-456',
            'jobName': 'custom-job-name'
        }
        
        batch_job_id = batch_manager.submit_job(
            task_id='test-task-2',
            parameters={'test': 'value'},
            job_name='custom_job_name'
        )
        
        assert batch_job_id == 'test-job-456'
        
        # Verify job name was sanitized (underscore to hyphen)
        call_args = batch_manager.batch_client.submit_job.call_args
        assert call_args[1]['jobName'] == 'custom-job-name'
    
    def test_submit_job_with_retry_and_timeout(self, batch_manager):
        """Test job submission with custom retry and timeout settings."""
        batch_manager.batch_client.submit_job.return_value = {
            'jobId': 'test-job-789',
            'jobName': 'task-test-task-3'
        }
        
        batch_manager.submit_job(
            task_id='test-task-3',
            parameters={'test': 'value'},
            retry_attempts=5,
            timeout_seconds=7200
        )
        
        call_args = batch_manager.batch_client.submit_job.call_args
        assert call_args[1]['retryStrategy']['attempts'] == 5
        assert call_args[1]['timeout']['attemptDurationSeconds'] == 7200
    
    def test_submit_job_missing_task_id(self, batch_manager):
        """Test job submission fails with missing task_id."""
        with pytest.raises(ValueError, match="task_id is required"):
            batch_manager.submit_job('', {'test': 'value'})
    
    def test_submit_job_missing_parameters(self, batch_manager):
        """Test job submission fails with missing parameters."""
        with pytest.raises(ValueError, match="parameters dictionary is required"):
            batch_manager.submit_job('test-task', {})
    
    def test_submit_job_client_error(self, batch_manager):
        """Test job submission handles AWS ClientError."""
        error_response = {
            'Error': {
                'Code': 'InvalidParameterException',
                'Message': 'Invalid job definition'
            }
        }
        batch_manager.batch_client.submit_job.side_effect = ClientError(
            error_response, 'SubmitJob'
        )
        
        with pytest.raises(ClientError):
            batch_manager.submit_job('test-task', {'test': 'value'})


class TestGetJobStatus:
    """Test job status querying functionality."""
    
    def test_get_job_status_running(self, batch_manager):
        """Test getting status of a running job."""
        batch_manager.batch_client.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-123',
                'jobName': 'task-test-task-1',
                'status': 'RUNNING',
                'statusReason': '',
                'createdAt': 1704067200000,
                'startedAt': 1704067260000,
                'container': {
                    'logStreamName': 'test-log-stream'
                }
            }]
        }
        
        status = batch_manager.get_job_status('test-job-123')
        
        assert status['job_id'] == 'test-job-123'
        assert status['job_name'] == 'task-test-task-1'
        assert status['status'] == 'RUNNING'
        assert status['created_at'] == 1704067200000
        assert status['started_at'] == 1704067260000
        assert 'container' in status
        assert status['container']['log_stream_name'] == 'test-log-stream'
    
    def test_get_job_status_succeeded(self, batch_manager):
        """Test getting status of a succeeded job."""
        batch_manager.batch_client.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-456',
                'jobName': 'task-test-task-2',
                'status': 'SUCCEEDED',
                'createdAt': 1704067200000,
                'startedAt': 1704067260000,
                'stoppedAt': 1704067500000,
                'container': {
                    'exitCode': 0,
                    'reason': 'Essential container exited',
                    'logStreamName': 'test-log-stream'
                }
            }]
        }
        
        status = batch_manager.get_job_status('test-job-456')
        
        assert status['status'] == 'SUCCEEDED'
        assert status['stopped_at'] == 1704067500000
        assert status['container']['exit_code'] == 0
    
    def test_get_job_status_failed(self, batch_manager):
        """Test getting status of a failed job."""
        batch_manager.batch_client.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-789',
                'jobName': 'task-test-task-3',
                'status': 'FAILED',
                'statusReason': 'Task failed to start',
                'createdAt': 1704067200000,
                'startedAt': 1704067260000,
                'stoppedAt': 1704067300000,
                'container': {
                    'exitCode': 1,
                    'reason': 'Error in processing',
                    'logStreamName': 'test-log-stream'
                },
                'attempts': [
                    {
                        'container': {
                            'exitCode': 1,
                            'reason': 'Error in processing'
                        }
                    }
                ]
            }]
        }
        
        status = batch_manager.get_job_status('test-job-789')
        
        assert status['status'] == 'FAILED'
        assert status['status_reason'] == 'Task failed to start'
        assert status['container']['exit_code'] == 1
        assert status['attempts'] == 1
        assert status['last_attempt_exit_code'] == 1
    
    def test_get_job_status_not_found(self, batch_manager):
        """Test getting status of a non-existent job."""
        batch_manager.batch_client.describe_jobs.return_value = {
            'jobs': []
        }
        
        status = batch_manager.get_job_status('non-existent-job')
        
        assert status['job_id'] == 'non-existent-job'
        assert status['status'] == 'NOT_FOUND'
        assert 'not found' in status['status_reason'].lower()
    
    def test_get_job_status_missing_job_id(self, batch_manager):
        """Test getting status fails with missing job_id."""
        with pytest.raises(ValueError, match="batch_job_id is required"):
            batch_manager.get_job_status('')


class TestCancelJob:
    """Test job cancellation functionality."""
    
    def test_cancel_job_success(self, batch_manager):
        """Test successful job cancellation."""
        # Mock get_job_status to return a running job
        batch_manager.batch_client.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-123',
                'jobName': 'task-test-task-1',
                'status': 'RUNNING',
                'createdAt': 1704067200000
            }]
        }
        
        batch_manager.batch_client.terminate_job.return_value = {}
        
        result = batch_manager.cancel_job('test-job-123', 'User requested cancellation')
        
        assert result is True
        batch_manager.batch_client.terminate_job.assert_called_once_with(
            jobId='test-job-123',
            reason='User requested cancellation'
        )
    
    def test_cancel_job_not_found(self, batch_manager):
        """Test cancelling a non-existent job."""
        batch_manager.batch_client.describe_jobs.return_value = {
            'jobs': []
        }
        
        result = batch_manager.cancel_job('non-existent-job')
        
        assert result is False
        batch_manager.batch_client.terminate_job.assert_not_called()
    
    def test_cancel_job_already_completed(self, batch_manager):
        """Test cancelling an already completed job."""
        batch_manager.batch_client.describe_jobs.return_value = {
            'jobs': [{
                'jobId': 'test-job-456',
                'jobName': 'task-test-task-2',
                'status': 'SUCCEEDED',
                'createdAt': 1704067200000
            }]
        }
        
        result = batch_manager.cancel_job('test-job-456')
        
        assert result is False
        batch_manager.batch_client.terminate_job.assert_not_called()
    
    def test_cancel_job_missing_job_id(self, batch_manager):
        """Test cancelling job fails with missing job_id."""
        with pytest.raises(ValueError, match="batch_job_id is required"):
            batch_manager.cancel_job('')


class TestListJobs:
    """Test job listing functionality."""
    
    def test_list_jobs_all(self, batch_manager):
        """Test listing all jobs."""
        batch_manager.batch_client.list_jobs.return_value = {
            'jobSummaryList': [
                {
                    'jobId': 'job-1',
                    'jobName': 'task-1',
                    'status': 'RUNNING',
                    'createdAt': 1704067200000,
                    'startedAt': 1704067260000
                },
                {
                    'jobId': 'job-2',
                    'jobName': 'task-2',
                    'status': 'PENDING',
                    'createdAt': 1704067300000
                }
            ]
        }
        
        jobs = batch_manager.list_jobs()
        
        assert len(jobs) == 2
        assert jobs[0]['job_id'] == 'job-1'
        assert jobs[0]['status'] == 'RUNNING'
        assert jobs[1]['job_id'] == 'job-2'
        assert jobs[1]['status'] == 'PENDING'
    
    def test_list_jobs_by_status(self, batch_manager):
        """Test listing jobs filtered by status."""
        batch_manager.batch_client.list_jobs.return_value = {
            'jobSummaryList': [
                {
                    'jobId': 'job-1',
                    'jobName': 'task-1',
                    'status': 'SUCCEEDED',
                    'createdAt': 1704067200000,
                    'startedAt': 1704067260000,
                    'stoppedAt': 1704067500000
                }
            ]
        }
        
        jobs = batch_manager.list_jobs(status='SUCCEEDED')
        
        assert len(jobs) == 1
        assert jobs[0]['status'] == 'SUCCEEDED'
        
        # Verify the API was called with the correct status filter
        call_args = batch_manager.batch_client.list_jobs.call_args
        assert call_args[1]['jobStatus'] == 'SUCCEEDED'
    
    def test_list_jobs_invalid_status(self, batch_manager):
        """Test listing jobs with invalid status."""
        with pytest.raises(ValueError, match="Invalid status"):
            batch_manager.list_jobs(status='INVALID_STATUS')
    
    def test_list_jobs_empty(self, batch_manager):
        """Test listing jobs when no jobs exist."""
        batch_manager.batch_client.list_jobs.return_value = {
            'jobSummaryList': []
        }
        
        jobs = batch_manager.list_jobs()
        
        assert len(jobs) == 0
