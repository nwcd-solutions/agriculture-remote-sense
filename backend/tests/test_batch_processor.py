"""
Tests for the AWS Batch Processor

These tests validate the batch processor logic without requiring actual AWS services.
"""
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import xarray as xr


class TestBatchProcessorInitialization:
    """Test batch processor initialization and configuration."""
    
    @patch.dict(os.environ, {
        'TASK_ID': 'test_task_123',
        'S3_BUCKET': 'test-bucket',
        'AWS_REGION': 'us-west-2',
        'DYNAMODB_TABLE': 'TestTasks'
    })
    @patch('batch_processor.RasterProcessor')
    @patch('batch_processor.VegetationIndexCalculator')
    @patch('batch_processor.S3StorageService')
    @patch('batch_processor.TaskRepository')
    def test_initialization_with_valid_env_vars(
        self,
        mock_task_repo,
        mock_s3,
        mock_calc,
        mock_raster
    ):
        """Test that BatchProcessor initializes correctly with valid environment variables."""
        from batch_processor import BatchProcessor
        
        processor = BatchProcessor()
        
        assert processor.task_id == 'test_task_123'
        assert processor.s3_bucket == 'test-bucket'
        assert processor.aws_region == 'us-west-2'
        assert processor.dynamodb_table == 'TestTasks'
        
        # Verify services were initialized
        mock_raster.assert_called_once()
        mock_calc.assert_called_once()
        mock_s3.assert_called_once_with(
            bucket_name='test-bucket',
            region='us-west-2'
        )
        mock_task_repo.assert_called_once_with(
            table_name='TestTasks',
            region='us-west-2'
        )
    
    @patch.dict(os.environ, {}, clear=True)
    def test_initialization_without_task_id_raises_error(self):
        """Test that missing TASK_ID raises ValueError."""
        from batch_processor import BatchProcessor
        
        with pytest.raises(ValueError, match="TASK_ID environment variable is required"):
            BatchProcessor()
    
    @patch.dict(os.environ, {'TASK_ID': 'test_123'}, clear=True)
    def test_initialization_without_s3_bucket_raises_error(self):
        """Test that missing S3_BUCKET raises ValueError."""
        from batch_processor import BatchProcessor
        
        with pytest.raises(ValueError, match="S3_BUCKET environment variable is required"):
            BatchProcessor()


class TestParameterReading:
    """Test reading task parameters from environment variables."""
    
    @patch.dict(os.environ, {
        'TASK_ID': 'test_task',
        'S3_BUCKET': 'test-bucket',
        'TASK_TYPE': 'indices',
        'INDICES': '["NDVI", "SAVI"]',
        'AOI': '{"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}',
        'BAND_URLS': '{"red": "https://example.com/red.tif", "nir": "https://example.com/nir.tif"}',
        'IMAGE_ID': 'S2A_TEST',
        'OUTPUT_FORMAT': 'COG'
    })
    @patch('batch_processor.RasterProcessor')
    @patch('batch_processor.VegetationIndexCalculator')
    @patch('batch_processor.S3StorageService')
    @patch('batch_processor.TaskRepository')
    def test_read_task_parameters(
        self,
        mock_task_repo,
        mock_s3,
        mock_calc,
        mock_raster
    ):
        """Test reading all task parameters from environment variables."""
        from batch_processor import BatchProcessor
        
        processor = BatchProcessor()
        params = processor.read_task_parameters()
        
        assert params['task_type'] == 'indices'
        assert params['indices'] == ['NDVI', 'SAVI']
        assert params['aoi']['type'] == 'Polygon'
        assert params['band_urls']['red'] == 'https://example.com/red.tif'
        assert params['image_id'] == 'S2A_TEST'
        assert params['output_format'] == 'COG'


class TestStatusUpdates:
    """Test task status update functionality."""
    
    @patch.dict(os.environ, {
        'TASK_ID': 'test_task',
        'S3_BUCKET': 'test-bucket'
    })
    @patch('batch_processor.RasterProcessor')
    @patch('batch_processor.VegetationIndexCalculator')
    @patch('batch_processor.S3StorageService')
    @patch('batch_processor.TaskRepository')
    def test_update_task_status_running(
        self,
        mock_task_repo,
        mock_s3,
        mock_calc,
        mock_raster
    ):
        """Test updating task status to running."""
        from batch_processor import BatchProcessor
        
        processor = BatchProcessor()
        processor.update_task_status('running', progress=50)
        
        # Verify update_task_status was called
        mock_task_repo.return_value.update_task_status.assert_called()
        call_kwargs = mock_task_repo.return_value.update_task_status.call_args[1]
        
        assert call_kwargs['task_id'] == 'test_task'
        assert call_kwargs['status'] == 'running'
        assert call_kwargs['progress'] == 50
    
    @patch.dict(os.environ, {
        'TASK_ID': 'test_task',
        'S3_BUCKET': 'test-bucket'
    })
    @patch('batch_processor.RasterProcessor')
    @patch('batch_processor.VegetationIndexCalculator')
    @patch('batch_processor.S3StorageService')
    @patch('batch_processor.TaskRepository')
    def test_update_task_status_completed_with_result(
        self,
        mock_task_repo,
        mock_s3,
        mock_calc,
        mock_raster
    ):
        """Test updating task status to completed with result."""
        from batch_processor import BatchProcessor
        from app.models.processing import ProcessingResult
        
        processor = BatchProcessor()
        
        result = ProcessingResult(
            output_files=[
                {
                    'name': 'test_NDVI.tif',
                    's3_key': 'results/test_task/test_NDVI.tif',
                    'size_mb': 10.5
                }
            ]
        )
        
        processor.update_task_status('completed', progress=100, result=result)
        
        # Verify update was called with result
        mock_task_repo.return_value.update_task_status.assert_called()
        call_kwargs = mock_task_repo.return_value.update_task_status.call_args[1]
        
        assert call_kwargs['status'] == 'completed'
        assert call_kwargs['progress'] == 100
        assert call_kwargs['result'] == result


class TestVegetationIndicesProcessing:
    """Test vegetation indices processing logic."""
    
    @patch('os.path.getsize', return_value=10485760)  # 10 MB
    @patch.dict(os.environ, {
        'TASK_ID': 'test_task',
        'S3_BUCKET': 'test-bucket'
    })
    @patch('batch_processor.RasterProcessor')
    @patch('batch_processor.VegetationIndexCalculator')
    @patch('batch_processor.S3StorageService')
    @patch('batch_processor.TaskRepository')
    def test_process_ndvi_with_valid_data(
        self,
        mock_task_repo,
        mock_s3,
        mock_calc,
        mock_raster,
        mock_getsize
    ):
        """Test NDVI processing with valid input data."""
        from batch_processor import BatchProcessor
        from app.models.aoi import GeoJSON
        
        # Setup mocks
        processor = BatchProcessor()
        
        # Mock raster data
        mock_data = MagicMock()
        mock_data.values = np.random.rand(100, 100)
        mock_data.rio.crs = 'EPSG:4326'
        mock_data.rio.transform.return_value = [1, 0, 0, 0, -1, 0]
        mock_data.rio.bounds.return_value = (0, 0, 1, 1)
        mock_data.shape = (100, 100)
        
        processor.raster_processor.read_cog_from_url.return_value = mock_data
        processor.raster_processor.clip_to_aoi.return_value = mock_data
        
        # Mock index calculation
        mock_ndvi = np.random.rand(100, 100)
        processor.index_calculator.calculate_ndvi.return_value = mock_ndvi
        
        # Mock to_cog to avoid actual file operations
        processor.raster_processor.to_cog.return_value = '/tmp/test_NDVI.tif'
        
        # Mock S3 upload
        processor.s3_service.upload_file.return_value = 's3://test-bucket/results/test_task/test_NDVI.tif'
        processor.s3_service.generate_presigned_url.return_value = 'https://presigned-url.com/test_NDVI.tif'
        
        # Test parameters
        params = {
            'indices': ['NDVI'],
            'aoi': {
                'type': 'Polygon',
                'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            },
            'band_urls': {
                'red': 'https://example.com/red.tif',
                'nir': 'https://example.com/nir.tif'
            },
            'image_id': 'test_image'
        }
        
        # Process
        result = processor.process_vegetation_indices(params)
        
        # Verify
        assert len(result.output_files) == 1
        assert result.output_files[0]['index'] == 'NDVI'
        assert 'NDVI.tif' in result.output_files[0]['name']
        
        # Verify calculator was called
        processor.index_calculator.calculate_ndvi.assert_called_once()
    
    @patch('os.path.getsize', return_value=10485760)  # 10 MB
    @patch.dict(os.environ, {
        'TASK_ID': 'test_task',
        'S3_BUCKET': 'test-bucket'
    })
    @patch('batch_processor.RasterProcessor')
    @patch('batch_processor.VegetationIndexCalculator')
    @patch('batch_processor.S3StorageService')
    @patch('batch_processor.TaskRepository')
    def test_process_multiple_indices(
        self,
        mock_task_repo,
        mock_s3,
        mock_calc,
        mock_raster,
        mock_getsize
    ):
        """Test processing multiple vegetation indices."""
        from batch_processor import BatchProcessor
        
        processor = BatchProcessor()
        
        # Mock raster data
        mock_data = MagicMock()
        mock_data.values = np.random.rand(100, 100)
        mock_data.rio.crs = 'EPSG:4326'
        mock_data.rio.transform.return_value = [1, 0, 0, 0, -1, 0]
        mock_data.rio.bounds.return_value = (0, 0, 1, 1)
        mock_data.shape = (100, 100)
        
        processor.raster_processor.read_cog_from_url.return_value = mock_data
        processor.raster_processor.clip_to_aoi.return_value = mock_data
        
        # Mock calculations
        processor.index_calculator.calculate_ndvi.return_value = np.random.rand(100, 100)
        processor.index_calculator.calculate_savi.return_value = np.random.rand(100, 100)
        
        # Mock to_cog to avoid actual file operations
        processor.raster_processor.to_cog.return_value = '/tmp/test_file.tif'
        
        # Mock S3
        processor.s3_service.upload_file.return_value = 's3://test-bucket/results/test_task/file.tif'
        processor.s3_service.generate_presigned_url.return_value = 'https://presigned-url.com/file.tif'
        
        params = {
            'indices': ['NDVI', 'SAVI'],
            'aoi': {
                'type': 'Polygon',
                'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            },
            'band_urls': {
                'red': 'https://example.com/red.tif',
                'nir': 'https://example.com/nir.tif'
            },
            'image_id': 'test_image'
        }
        
        result = processor.process_vegetation_indices(params)
        
        # Verify both indices were processed
        assert len(result.output_files) == 2
        indices = [f['index'] for f in result.output_files]
        assert 'NDVI' in indices
        assert 'SAVI' in indices


class TestErrorHandling:
    """Test error handling in batch processor."""
    
    @patch.dict(os.environ, {
        'TASK_ID': 'test_task',
        'S3_BUCKET': 'test-bucket'
    })
    @patch('batch_processor.RasterProcessor')
    @patch('batch_processor.VegetationIndexCalculator')
    @patch('batch_processor.S3StorageService')
    @patch('batch_processor.TaskRepository')
    def test_missing_required_bands_raises_error(
        self,
        mock_task_repo,
        mock_s3,
        mock_calc,
        mock_raster
    ):
        """Test that missing required bands raises appropriate error."""
        from batch_processor import BatchProcessor
        
        processor = BatchProcessor()
        
        params = {
            'indices': ['NDVI'],
            'aoi': {
                'type': 'Polygon',
                'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            },
            'band_urls': {
                'red': 'https://example.com/red.tif'
                # Missing NIR band
            },
            'image_id': 'test_image'
        }
        
        # Mock raster reading
        mock_data = MagicMock()
        mock_data.values = np.random.rand(100, 100)
        processor.raster_processor.read_cog_from_url.return_value = mock_data
        processor.raster_processor.clip_to_aoi.return_value = mock_data
        
        with pytest.raises(ValueError, match="NDVI requires NIR and Red bands"):
            processor.process_vegetation_indices(params)
    
    @patch.dict(os.environ, {
        'TASK_ID': 'test_task',
        'S3_BUCKET': 'test-bucket'
    })
    @patch('batch_processor.RasterProcessor')
    @patch('batch_processor.VegetationIndexCalculator')
    @patch('batch_processor.S3StorageService')
    @patch('batch_processor.TaskRepository')
    def test_invalid_index_name_raises_error(
        self,
        mock_task_repo,
        mock_s3,
        mock_calc,
        mock_raster
    ):
        """Test that invalid index name raises appropriate error."""
        from batch_processor import BatchProcessor
        
        processor = BatchProcessor()
        
        # Mock raster data
        mock_data = MagicMock()
        mock_data.values = np.random.rand(100, 100)
        mock_data.rio.crs = 'EPSG:4326'
        mock_data.rio.transform.return_value = [1, 0, 0, 0, -1, 0]
        mock_data.rio.bounds.return_value = (0, 0, 1, 1)
        mock_data.shape = (100, 100)
        
        processor.raster_processor.read_cog_from_url.return_value = mock_data
        processor.raster_processor.clip_to_aoi.return_value = mock_data
        
        params = {
            'indices': ['INVALID_INDEX'],
            'aoi': {
                'type': 'Polygon',
                'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            },
            'band_urls': {
                'red': 'https://example.com/red.tif',
                'nir': 'https://example.com/nir.tif'
            },
            'image_id': 'test_image'
        }
        
        with pytest.raises(ValueError, match="Unknown index"):
            processor.process_vegetation_indices(params)
