"""
Unit tests for S3 Storage Service.
Tests file upload, download, presigned URL generation, and error handling.
"""
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from app.services.s3_storage_service import S3StorageService


@pytest.fixture
def s3_service():
    """Create S3StorageService instance for testing."""
    return S3StorageService(
        bucket_name='test-bucket',
        region='us-west-2'
    )


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    with patch('boto3.client') as mock_client:
        yield mock_client.return_value


class TestS3StorageService:
    """Test suite for S3StorageService."""
    
    def test_initialization(self, s3_service):
        """Test S3StorageService initialization."""
        assert s3_service.bucket_name == 'test-bucket'
        assert s3_service.region == 'us-west-2'
        assert s3_service.s3_client is not None
    
    def test_upload_file_success(self, s3_service, mock_s3_client):
        """Test successful file upload."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('test content')
            temp_file = f.name
        
        try:
            # Mock S3 client
            s3_service.s3_client = mock_s3_client
            mock_s3_client.upload_file = Mock()
            
            # Upload file
            s3_url = s3_service.upload_file(temp_file, 'test/file.txt')
            
            # Verify
            assert s3_url == 's3://test-bucket/test/file.txt'
            mock_s3_client.upload_file.assert_called_once()
            
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_upload_file_with_metadata(self, s3_service, mock_s3_client):
        """Test file upload with metadata."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('test content')
            temp_file = f.name
        
        try:
            # Mock S3 client
            s3_service.s3_client = mock_s3_client
            mock_s3_client.upload_file = Mock()
            
            # Upload file with metadata
            metadata = {'task_id': 'task_123', 'index': 'NDVI'}
            s3_url = s3_service.upload_file(
                temp_file,
                'test/file.txt',
                metadata=metadata
            )
            
            # Verify
            assert s3_url == 's3://test-bucket/test/file.txt'
            call_args = mock_s3_client.upload_file.call_args
            assert call_args[1]['ExtraArgs']['Metadata'] == metadata
            
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_upload_file_not_found(self, s3_service):
        """Test upload with non-existent file."""
        with pytest.raises(FileNotFoundError):
            s3_service.upload_file('/nonexistent/file.txt', 'test/file.txt')
    
    def test_upload_file_s3_error(self, s3_service, mock_s3_client):
        """Test upload with S3 error."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('test content')
            temp_file = f.name
        
        try:
            # Mock S3 client to raise error
            s3_service.s3_client = mock_s3_client
            mock_s3_client.upload_file = Mock(
                side_effect=ClientError(
                    {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
                    'upload_file'
                )
            )
            
            # Verify error is raised
            with pytest.raises(ClientError):
                s3_service.upload_file(temp_file, 'test/file.txt')
                
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_download_file_success(self, s3_service, mock_s3_client):
        """Test successful file download."""
        # Mock S3 client
        s3_service.s3_client = mock_s3_client
        mock_s3_client.download_file = Mock()
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = os.path.join(temp_dir, 'downloaded.txt')
            
            # Download file
            result = s3_service.download_file('test/file.txt', local_path)
            
            # Verify
            assert result == local_path
            mock_s3_client.download_file.assert_called_once_with(
                'test-bucket',
                'test/file.txt',
                local_path
            )
    
    def test_download_file_s3_error(self, s3_service, mock_s3_client):
        """Test download with S3 error."""
        # Mock S3 client to raise error
        s3_service.s3_client = mock_s3_client
        mock_s3_client.download_file = Mock(
            side_effect=ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}},
                'download_file'
            )
        )
        
        # Verify error is raised
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = os.path.join(temp_dir, 'downloaded.txt')
            with pytest.raises(ClientError):
                s3_service.download_file('test/file.txt', local_path)
    
    def test_generate_presigned_url_success(self, s3_service, mock_s3_client):
        """Test presigned URL generation."""
        # Mock S3 client
        s3_service.s3_client = mock_s3_client
        mock_s3_client.generate_presigned_url = Mock(
            return_value='https://test-bucket.s3.amazonaws.com/test/file.txt?signature=xyz'
        )
        
        # Generate presigned URL
        url = s3_service.generate_presigned_url('test/file.txt', expiration=3600)
        
        # Verify
        assert url.startswith('https://test-bucket.s3.amazonaws.com')
        assert 'signature=' in url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': 'test-bucket', 'Key': 'test/file.txt'},
            ExpiresIn=3600
        )
    
    def test_generate_presigned_url_custom_expiration(self, s3_service, mock_s3_client):
        """Test presigned URL with custom expiration."""
        # Mock S3 client
        s3_service.s3_client = mock_s3_client
        mock_s3_client.generate_presigned_url = Mock(
            return_value='https://test-bucket.s3.amazonaws.com/test/file.txt?signature=xyz'
        )
        
        # Generate presigned URL with custom expiration
        url = s3_service.generate_presigned_url('test/file.txt', expiration=7200)
        
        # Verify expiration parameter
        call_args = mock_s3_client.generate_presigned_url.call_args
        assert call_args[1]['ExpiresIn'] == 7200
    
    def test_generate_presigned_url_error(self, s3_service, mock_s3_client):
        """Test presigned URL generation with error."""
        # Mock S3 client to raise error
        s3_service.s3_client = mock_s3_client
        mock_s3_client.generate_presigned_url = Mock(
            side_effect=ClientError(
                {'Error': {'Code': 'InvalidRequest', 'Message': 'Invalid request'}},
                'generate_presigned_url'
            )
        )
        
        # Verify error is raised
        with pytest.raises(ClientError):
            s3_service.generate_presigned_url('test/file.txt')
    
    def test_delete_file_success(self, s3_service, mock_s3_client):
        """Test successful file deletion."""
        # Mock S3 client
        s3_service.s3_client = mock_s3_client
        mock_s3_client.delete_object = Mock()
        
        # Delete file
        result = s3_service.delete_file('test/file.txt')
        
        # Verify
        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test/file.txt'
        )
    
    def test_delete_file_error(self, s3_service, mock_s3_client):
        """Test file deletion with error."""
        # Mock S3 client to raise error
        s3_service.s3_client = mock_s3_client
        mock_s3_client.delete_object = Mock(
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
                'delete_object'
            )
        )
        
        # Verify error is raised
        with pytest.raises(ClientError):
            s3_service.delete_file('test/file.txt')
    
    def test_list_files_success(self, s3_service, mock_s3_client):
        """Test listing files."""
        # Mock S3 client
        s3_service.s3_client = mock_s3_client
        mock_s3_client.list_objects_v2 = Mock(
            return_value={
                'Contents': [
                    {'Key': 'test/file1.txt'},
                    {'Key': 'test/file2.txt'},
                    {'Key': 'test/file3.txt'},
                ]
            }
        )
        
        # List files
        files = s3_service.list_files(prefix='test/')
        
        # Verify
        assert len(files) == 3
        assert 'test/file1.txt' in files
        assert 'test/file2.txt' in files
        assert 'test/file3.txt' in files
        mock_s3_client.list_objects_v2.assert_called_once()
    
    def test_list_files_empty(self, s3_service, mock_s3_client):
        """Test listing files with no results."""
        # Mock S3 client
        s3_service.s3_client = mock_s3_client
        mock_s3_client.list_objects_v2 = Mock(return_value={})
        
        # List files
        files = s3_service.list_files(prefix='nonexistent/')
        
        # Verify
        assert len(files) == 0
    
    def test_list_files_error(self, s3_service, mock_s3_client):
        """Test listing files with error."""
        # Mock S3 client to raise error
        s3_service.s3_client = mock_s3_client
        mock_s3_client.list_objects_v2 = Mock(
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
                'list_objects_v2'
            )
        )
        
        # Verify error is raised
        with pytest.raises(ClientError):
            s3_service.list_files()
    
    def test_file_exists_true(self, s3_service, mock_s3_client):
        """Test file exists check when file exists."""
        # Mock S3 client
        s3_service.s3_client = mock_s3_client
        mock_s3_client.head_object = Mock(return_value={'ContentLength': 1024})
        
        # Check if file exists
        exists = s3_service.file_exists('test/file.txt')
        
        # Verify
        assert exists is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test/file.txt'
        )
    
    def test_file_exists_false(self, s3_service, mock_s3_client):
        """Test file exists check when file doesn't exist."""
        # Mock S3 client to raise 404 error
        s3_service.s3_client = mock_s3_client
        mock_s3_client.head_object = Mock(
            side_effect=ClientError(
                {'Error': {'Code': '404', 'Message': 'Not Found'}},
                'head_object'
            )
        )
        
        # Check if file exists
        exists = s3_service.file_exists('test/nonexistent.txt')
        
        # Verify
        assert exists is False
    
    def test_get_file_size_success(self, s3_service, mock_s3_client):
        """Test getting file size."""
        # Mock S3 client
        s3_service.s3_client = mock_s3_client
        mock_s3_client.head_object = Mock(
            return_value={'ContentLength': 2048}
        )
        
        # Get file size
        size = s3_service.get_file_size('test/file.txt')
        
        # Verify
        assert size == 2048
        mock_s3_client.head_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test/file.txt'
        )
    
    def test_get_file_size_error(self, s3_service, mock_s3_client):
        """Test getting file size with error."""
        # Mock S3 client to raise error
        s3_service.s3_client = mock_s3_client
        mock_s3_client.head_object = Mock(
            side_effect=ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}},
                'head_object'
            )
        )
        
        # Verify error is raised
        with pytest.raises(ClientError):
            s3_service.get_file_size('test/nonexistent.txt')
