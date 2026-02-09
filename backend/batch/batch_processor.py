#!/usr/bin/env python3
"""
AWS Batch Processing Container Entry Point

This script is the main entry point for AWS Batch processing jobs.
It reads task parameters from environment variables, processes satellite data,
uploads results to S3, and updates task status in DynamoDB.

Requirements: 10.2, 10.3
"""

import os
import sys
import json
import logging
import tempfile
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Any
from decimal import Decimal
import numpy as np

# Import application services
from app.services.raster_processor import RasterProcessor
from app.services.vegetation_index_calculator import VegetationIndexCalculator
from app.services.temporal_compositor import TemporalCompositor
from app.services.s3_storage_service import S3StorageService
from app.services.task_repository import TaskRepository
from app.models.aoi import GeoJSON
from app.models.processing import ProcessingResult


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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    AWS Batch processing job handler.
    
    Processes satellite data tasks including vegetation index calculation,
    time series compositing, and data downloads.
    """
    
    def __init__(self):
        """Initialize the batch processor with required services."""
        # Read configuration from environment variables
        self.task_id = os.getenv('TASK_ID')
        self.s3_bucket = os.getenv('S3_BUCKET')
        self.aws_region = os.getenv('AWS_REGION', 'us-west-2')
        self.dynamodb_table = os.getenv('DYNAMODB_TABLE', 'ProcessingTasks')
        
        # Validate required environment variables
        if not self.task_id:
            raise ValueError("TASK_ID environment variable is required")
        if not self.s3_bucket:
            raise ValueError("S3_BUCKET environment variable is required")
        
        logger.info(f"Initializing BatchProcessor for task: {self.task_id}")
        logger.info(f"S3 Bucket: {self.s3_bucket}")
        logger.info(f"AWS Region: {self.aws_region}")
        logger.info(f"DynamoDB Table: {self.dynamodb_table}")
        
        # Initialize services
        self.raster_processor = RasterProcessor()
        self.index_calculator = VegetationIndexCalculator()
        self.temporal_compositor = TemporalCompositor()
        self.s3_service = S3StorageService(
            bucket_name=self.s3_bucket,
            region=self.aws_region
        )
        self.task_repository = TaskRepository(
            table_name=self.dynamodb_table,
            region=self.aws_region
        )
        
        # Create temporary directory for processing
        self.temp_dir = tempfile.mkdtemp(prefix=f"batch_{self.task_id}_")
        logger.info(f"Created temporary directory: {self.temp_dir}")
    
    def read_task_parameters(self) -> Dict[str, Any]:
        """
        Read task parameters from environment variables.
        
        Returns:
            Dict containing task parameters
        """
        logger.info("Reading task parameters from environment variables")
        
        # Read all environment variables that are task parameters
        params = {}
        
        # Common parameters
        task_type = os.getenv('TASK_TYPE')
        if task_type:
            params['task_type'] = task_type
        
        # Vegetation indices parameters
        indices_str = os.getenv('INDICES')
        if indices_str:
            params['indices'] = json.loads(indices_str)
        
        # AOI parameter
        aoi_str = os.getenv('AOI')
        if aoi_str:
            params['aoi'] = json.loads(aoi_str)
        
        # Band URLs parameter
        band_urls_str = os.getenv('BAND_URLS')
        if band_urls_str:
            params['band_urls'] = json.loads(band_urls_str)
        
        # Image ID
        image_id = os.getenv('IMAGE_ID')
        if image_id:
            params['image_id'] = image_id
        
        # Output format
        output_format = os.getenv('OUTPUT_FORMAT', 'COG')
        params['output_format'] = output_format
        
        # Composite parameters
        satellite = os.getenv('SATELLITE')
        if satellite:
            params['satellite'] = satellite
        
        composite_mode = os.getenv('COMPOSITE_MODE')
        if composite_mode:
            params['composite_mode'] = composite_mode
        
        apply_cloud_mask = os.getenv('APPLY_CLOUD_MASK')
        if apply_cloud_mask:
            params['apply_cloud_mask'] = apply_cloud_mask.lower() in ('true', '1', 'yes')
        
        date_range_str = os.getenv('DATE_RANGE')
        if date_range_str:
            params['date_range'] = json.loads(date_range_str)
        
        image_urls_str = os.getenv('IMAGE_URLS')
        if image_urls_str:
            params['image_urls'] = json.loads(image_urls_str)
        
        image_timestamps_str = os.getenv('IMAGE_TIMESTAMPS')
        if image_timestamps_str:
            params['image_timestamps'] = json.loads(image_timestamps_str)
        
        qa_band_urls_str = os.getenv('QA_BAND_URLS')
        if qa_band_urls_str:
            params['qa_band_urls'] = json.loads(qa_band_urls_str)
        
        logger.info(f"Task parameters: {json.dumps(params, indent=2)}")
        
        return params
    
    def update_task_status(
        self,
        status: str,
        progress: int = None,
        result: ProcessingResult = None,
        error: str = None
    ):
        """
        Update task status in DynamoDB.
        
        Args:
            status: Task status (running, completed, failed)
            progress: Progress percentage (0-100)
            result: Processing result object
            error: Error message if failed
        """
        try:
            logger.info(f"Updating task status: {status} (progress: {progress}%)")
            
            update_kwargs = {
                'task_id': self.task_id,
                'status': status
            }
            
            if progress is not None:
                update_kwargs['progress'] = progress
            
            if status == 'running' and not hasattr(self, '_started_at_set'):
                update_kwargs['started_at'] = datetime.now(timezone.utc)
                self._started_at_set = True
            
            if status in ['completed', 'failed']:
                update_kwargs['completed_at'] = datetime.now(timezone.utc)
            
            if result:
                # Convert result to dict and then convert floats to Decimal
                result_dict = result.model_dump()
                result_dict = convert_floats_to_decimal(result_dict)
                update_kwargs['result'] = result_dict
            
            if error:
                update_kwargs['error'] = error
            
            self.task_repository.update_task_status(**update_kwargs)
            logger.info("Task status updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            # Don't raise - we want to continue processing even if status update fails
    
    def process_vegetation_indices(self, params: Dict[str, Any]) -> ProcessingResult:
        """
        Process vegetation indices calculation.
        
        Args:
            params: Task parameters containing indices, aoi, band_urls, etc.
            
        Returns:
            ProcessingResult with output files
        """
        logger.info("Starting vegetation indices processing")
        
        # Extract parameters
        indices = params.get('indices', [])
        aoi_dict = params.get('aoi')
        band_urls = params.get('band_urls', {})
        image_id = params.get('image_id', 'unknown')
        
        if not indices:
            raise ValueError("No indices specified")
        if not aoi_dict:
            raise ValueError("AOI not specified")
        if not band_urls:
            raise ValueError("Band URLs not specified")
        
        # Parse AOI
        aoi = GeoJSON(**aoi_dict)
        logger.info(f"Processing {len(indices)} indices for image {image_id}")
        
        # Update progress
        self.update_task_status('running', progress=10)
        
        # Read and clip bands
        logger.info("Reading and clipping bands")
        bands_data = {}
        band_names = ['red', 'nir', 'green', 'blue']
        
        for band_name in band_names:
            if band_name in band_urls:
                try:
                    logger.info(f"Reading {band_name} band from {band_urls[band_name]}")
                    band_data = self.raster_processor.read_cog_from_url(band_urls[band_name])
                    
                    # Clip to AOI
                    logger.info(f"Clipping {band_name} band to AOI")
                    clipped_data = self.raster_processor.clip_to_aoi(band_data, aoi)
                    
                    # Convert to numpy array
                    bands_data[band_name] = clipped_data.values
                    
                    # Store metadata from first band
                    if 'metadata' not in bands_data:
                        bands_data['metadata'] = {
                            'crs': str(clipped_data.rio.crs),
                            'transform': clipped_data.rio.transform(),
                            'shape': clipped_data.shape,
                            'bounds': clipped_data.rio.bounds()
                        }
                    
                except Exception as e:
                    logger.error(f"Failed to read {band_name} band: {e}")
                    raise
        
        # Update progress
        self.update_task_status('running', progress=40)
        
        # Calculate indices
        logger.info("Calculating vegetation indices")
        output_files = []
        
        for i, index_name in enumerate(indices):
            try:
                logger.info(f"Calculating {index_name}")
                
                # Calculate index based on type
                if index_name == 'NDVI':
                    if 'nir' not in bands_data or 'red' not in bands_data:
                        raise ValueError("NDVI requires NIR and Red bands")
                    index_data = self.index_calculator.calculate_ndvi(
                        bands_data['nir'],
                        bands_data['red']
                    )
                
                elif index_name == 'SAVI':
                    if 'nir' not in bands_data or 'red' not in bands_data:
                        raise ValueError("SAVI requires NIR and Red bands")
                    index_data = self.index_calculator.calculate_savi(
                        bands_data['nir'],
                        bands_data['red']
                    )
                
                elif index_name == 'EVI':
                    if 'nir' not in bands_data or 'red' not in bands_data or 'blue' not in bands_data:
                        raise ValueError("EVI requires NIR, Red, and Blue bands")
                    index_data = self.index_calculator.calculate_evi(
                        bands_data['nir'],
                        bands_data['red'],
                        bands_data['blue']
                    )
                
                elif index_name == 'VGI':
                    if 'green' not in bands_data or 'red' not in bands_data:
                        raise ValueError("VGI requires Green and Red bands")
                    index_data = self.index_calculator.calculate_vgi(
                        bands_data['green'],
                        bands_data['red']
                    )
                
                else:
                    raise ValueError(f"Unknown index: {index_name}")
                
                # Save to temporary file
                output_filename = f"{image_id}_{index_name}.tif"
                temp_output_path = os.path.join(self.temp_dir, output_filename)
                
                logger.info(f"Saving {index_name} to {temp_output_path}")
                
                # Convert back to xarray DataArray for saving
                import xarray as xr
                import rioxarray
                from rasterio.transform import Affine
                
                # Get reference data for spatial metadata
                ref_band = list(bands_data.values())[0]
                
                # Create DataArray with spatial metadata
                index_xr = xr.DataArray(
                    index_data,
                    dims=['band', 'y', 'x'] if len(index_data.shape) == 3 else ['y', 'x']
                )
                
                # Copy spatial metadata from reference band
                index_xr.rio.write_crs(bands_data['metadata']['crs'], inplace=True)
                
                # Convert transform to Affine if it's not already
                transform = bands_data['metadata']['transform']
                if not isinstance(transform, Affine):
                    # If it's a tuple or list, convert to Affine
                    if isinstance(transform, (tuple, list)) and len(transform) >= 6:
                        transform = Affine(transform[0], transform[1], transform[2],
                                         transform[3], transform[4], transform[5])
                
                index_xr.rio.write_transform(transform, inplace=True)
                
                # Save as COG
                self.raster_processor.to_cog(
                    index_xr,
                    temp_output_path,
                    compress='DEFLATE',
                    nodata=-9999
                )
                
                # Upload to S3
                s3_key = f"results/{self.task_id}/{output_filename}"
                logger.info(f"Uploading {output_filename} to S3: {s3_key}")
                
                s3_url = self.s3_service.upload_file(
                    temp_output_path,
                    s3_key,
                    metadata={
                        'task_id': self.task_id,
                        'index': index_name,
                        'image_id': image_id
                    }
                )
                
                # Generate presigned download URL (reduced from 24h to 4h for security)
                download_url = self.s3_service.generate_presigned_url(
                    s3_key,
                    expiration=14400  # 4 hours
                )
                
                # Get file size
                file_size_bytes = os.path.getsize(temp_output_path)
                file_size_mb = file_size_bytes / (1024 * 1024)
                
                # Add to output files
                output_files.append({
                    'name': output_filename,
                    's3_key': s3_key,
                    's3_url': s3_url,
                    'download_url': download_url,
                    'size_mb': round(file_size_mb, 2),
                    'index': index_name
                })
                
                logger.info(f"Successfully processed {index_name} ({file_size_mb:.2f} MB)")
                
                # Update progress
                progress = 40 + int((i + 1) / len(indices) * 50)
                self.update_task_status('running', progress=progress)
                
            except Exception as e:
                logger.error(f"Failed to calculate {index_name}: {e}")
                raise
        
        # Create result
        result = ProcessingResult(
            output_files=output_files,
            metadata={
                'image_id': image_id,
                'indices': indices,
                'processing_time_seconds': None  # Will be calculated by caller
            }
        )
        
        logger.info(f"Vegetation indices processing completed. Generated {len(output_files)} files.")
        
        return result
    
    def process_temporal_composite(self, params: Dict[str, Any]) -> ProcessingResult:
        """
        处理时间合成任务。

        流程:
        1. 读取每张影像并裁剪到 AOI
        2. 可选：应用云掩膜
        3. 按月度分组并计算均值合成
        4. 保存结果为 COG 并上传到 S3

        Args:
            params: 任务参数，包含:
                - image_urls: 影像 URL 列表
                - image_timestamps: ISO 格式时间戳列表
                - aoi: GeoJSON AOI
                - satellite: 卫星类型
                - composite_mode: 合成模式 (目前支持 "monthly")
                - apply_cloud_mask: 是否应用云掩膜
                - qa_band_urls: 质量波段 URL 列表（与 image_urls 对应）
                - indices: 可选，合成后计算的植被指数

        Returns:
            ProcessingResult
        """
        logger.info("Starting temporal composite processing")

        image_urls = params.get('image_urls', [])
        timestamp_strs = params.get('image_timestamps', [])
        aoi_dict = params.get('aoi')
        satellite = params.get('satellite', 'sentinel-2')
        apply_mask = params.get('apply_cloud_mask', False)
        qa_band_urls = params.get('qa_band_urls', [])
        indices = params.get('indices', [])

        if not image_urls:
            raise ValueError("image_urls is required for composite task")
        if not timestamp_strs:
            raise ValueError("image_timestamps is required for composite task")
        if not aoi_dict:
            raise ValueError("AOI is required for composite task")
        if len(image_urls) != len(timestamp_strs):
            raise ValueError("image_urls and image_timestamps must have the same length")

        aoi = GeoJSON(**aoi_dict)
        timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in timestamp_strs]

        self.update_task_status('running', progress=5)

        # Step 1: Read and clip all images
        logger.info(f"Reading {len(image_urls)} images")
        clipped_images: list = []
        total_images = len(image_urls)

        for i, url in enumerate(image_urls):
            try:
                logger.info(f"Reading image {i+1}/{total_images}: {url[-60:]}")
                raw = self.raster_processor.read_cog_from_url(url)
                clipped = self.raster_processor.clip_to_aoi(raw, aoi)

                # Step 2: Apply cloud mask if requested
                if apply_mask and i < len(qa_band_urls) and qa_band_urls[i]:
                    logger.info(f"Applying cloud mask for image {i+1}")
                    qa_raw = self.raster_processor.read_cog_from_url(qa_band_urls[i])
                    qa_clipped = self.raster_processor.clip_to_aoi(qa_raw, aoi)
                    clipped = self.raster_processor.apply_cloud_mask(clipped, qa_clipped, satellite)

                clipped_images.append(clipped)
            except Exception as e:
                logger.warning(f"Failed to read image {i+1}, skipping: {e}")
                continue

            progress = 5 + int((i + 1) / total_images * 40)
            self.update_task_status('running', progress=progress)

        if not clipped_images:
            raise ValueError("No images could be read successfully")

        logger.info(f"Successfully read {len(clipped_images)} of {total_images} images")

        # Step 3: Composite
        self.update_task_status('running', progress=50)
        composites = self.temporal_compositor.composite_monthly(clipped_images, timestamps[:len(clipped_images)])

        logger.info(f"Generated {len(composites)} monthly composites")

        # Step 4: Save results
        self.update_task_status('running', progress=70)
        output_files = []

        for idx, (period_label, composite_data) in enumerate(composites):
            # Save composite band
            output_filename = f"composite_{period_label}.tif"
            temp_path = os.path.join(self.temp_dir, output_filename)

            logger.info(f"Saving composite {period_label} to {temp_path}")
            self.raster_processor.to_cog(composite_data, temp_path, compress='DEFLATE', nodata=np.nan)

            s3_key = f"results/{self.task_id}/{output_filename}"
            self.s3_service.upload_file(temp_path, s3_key, metadata={
                'task_id': self.task_id,
                'period': period_label,
                'type': 'composite'
            })
            download_url = self.s3_service.generate_presigned_url(s3_key, expiration=14400)  # 4 hours
            file_size_mb = round(os.path.getsize(temp_path) / (1024 * 1024), 2)

            output_files.append({
                'name': output_filename,
                's3_key': s3_key,
                'download_url': download_url,
                'size_mb': file_size_mb,
                'index': f"composite_{period_label}"
            })

            # Optionally compute vegetation indices on the composite
            if indices:
                # This requires the composite to have the right bands — skip for now
                # as composite is typically single-band per input
                pass

            progress = 70 + int((idx + 1) / len(composites) * 25)
            self.update_task_status('running', progress=progress)

        result = ProcessingResult(
            output_files=output_files,
            metadata={
                'composite_mode': 'monthly',
                'satellite': satellite,
                'total_input_images': total_images,
                'successful_images': len(clipped_images),
                'periods': [p for p, _ in composites],
                'cloud_mask_applied': apply_mask,
            }
        )

        logger.info(f"Temporal composite processing completed. Generated {len(output_files)} files.")
        return result

    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory: {e}")
    
    def run(self):
        """
        Main execution method.
        
        Reads parameters, processes the task, uploads results, and updates status.
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Update status to running
            self.update_task_status('running', progress=0)
            
            # Read task parameters
            params = self.read_task_parameters()
            task_type = params.get('task_type', 'indices')
            
            logger.info(f"Processing task type: {task_type}")
            
            # Process based on task type
            if task_type == 'indices':
                result = self.process_vegetation_indices(params)
            elif task_type == 'composite':
                result = self.process_temporal_composite(params)
            else:
                raise ValueError(f"Unsupported task type: {task_type}")
            
            # Calculate processing time
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            
            if result.metadata is None:
                result.metadata = {}
            result.metadata['processing_time_seconds'] = round(processing_time, 2)
            
            # Update status to completed
            self.update_task_status('completed', progress=100, result=result)
            
            logger.info(f"Task completed successfully in {processing_time:.2f} seconds")
            
            return 0
            
        except Exception as e:
            # Log error
            error_msg = f"Task failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Update status to failed
            self.update_task_status('failed', error=error_msg)
            
            return 1
        
        finally:
            # Clean up temporary files
            self.cleanup()


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("AWS Batch Processor Starting")
    logger.info("=" * 80)
    
    try:
        processor = BatchProcessor()
        exit_code = processor.run()
        
        logger.info("=" * 80)
        logger.info(f"AWS Batch Processor Finished (exit code: {exit_code})")
        logger.info("=" * 80)
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == '__main__':
    main()
