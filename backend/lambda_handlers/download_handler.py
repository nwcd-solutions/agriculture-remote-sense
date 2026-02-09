"""
Lambda handler for downloading satellite images to S3
Downloads images from AWS Open Data to user's S3 bucket organized by date
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))


def get_cors_headers():
    """Return CORS headers"""
    allowed_origins = os.getenv('CORS_ORIGINS', '*')
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': allowed_origins,
        'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Credentials': 'true' if allowed_origins != '*' else 'false'
    }


def handler(event, context):
    """
    Handle download requests
    
    Routes:
    - POST /api/download/batch - Download multiple images to S3
    - GET /health - Health check
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method'))
        path = event.get('path', event.get('rawPath', ''))
        
        # Health check
        if path in ['/', '/health'] and http_method == 'GET':
            return health_check()
        
        # OPTIONS for CORS
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # Batch download endpoint
        if http_method == 'POST' and '/batch' in path:
            return download_batch(event)
        
        return {
            'statusCode': 404,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Not found'})
        }
            
    except Exception as e:
        logger.error(f'Handler error: {str(e)}', exc_info=True)
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def health_check():
    """Health check endpoint"""
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'status': 'healthy',
            'service': 'satellite-gis-download-lambda',
            'version': '1.0.0'
        })
    }


def download_batch(event):
    """
    Download multiple satellite images to S3
    
    Request body:
    {
        "images": [
            {
                "id": "image_id",
                "datetime": "2024-01-15T10:30:00Z",
                "satellite": "sentinel-2",
                "assets": { ... }
            }
        ]
    }
    
    Images are organized in S3 as:
    raw/{satellite}/{YYYY}/{MM}/{DD}/{image_id}/{asset_name}.tif
    """
    try:
        body = json.loads(event.get('body', '{}'))
        images = body.get('images', [])
        
        if not images:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'No images provided'})
            }
        
        # Get S3 bucket from environment
        s3_bucket = os.getenv('S3_BUCKET')
        if not s3_bucket:
            raise ValueError('S3_BUCKET environment variable not set')
        
        s3_client = boto3.client('s3')
        
        # Process each image
        results = []
        for image in images:
            try:
                result = download_image_to_s3(s3_client, s3_bucket, image)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to download image {image.get('id')}: {e}")
                results.append({
                    'image_id': image.get('id'),
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Count successes and failures
        success_count = sum(1 for r in results if r.get('status') == 'success')
        failed_count = len(results) - success_count
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': f'Downloaded {success_count} images, {failed_count} failed',
                'total': len(results),
                'success': success_count,
                'failed': failed_count,
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Batch download error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def download_image_to_s3(s3_client, bucket: str, image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Download a single image's assets to S3
    
    Args:
        s3_client: Boto3 S3 client
        bucket: Target S3 bucket name
        image: Image metadata with assets
        
    Returns:
        Dict with download result
    """
    image_id = image.get('id', 'unknown')
    datetime_str = image.get('datetime', '')
    satellite = image.get('satellite', 'unknown')
    assets = image.get('assets', {})
    
    # Parse datetime to organize by date
    try:
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        year = dt.strftime('%Y')
        month = dt.strftime('%m')
        day = dt.strftime('%d')
    except:
        year = 'unknown'
        month = 'unknown'
        day = 'unknown'
    
    # Base path: raw/{satellite}/{YYYY}/{MM}/{DD}/{image_id}/
    base_path = f"raw/{satellite}/{year}/{month}/{day}/{image_id}"
    
    downloaded_assets = []
    
    # Download important assets (bands, QA, etc.)
    important_asset_keys = get_important_assets(satellite)
    
    for asset_key in important_asset_keys:
        if asset_key not in assets:
            continue
            
        asset = assets[asset_key]
        asset_href = asset.get('href')
        
        if not asset_href:
            continue
        
        try:
            # Determine file extension
            file_ext = get_file_extension(asset_href, asset.get('type'))
            s3_key = f"{base_path}/{asset_key}{file_ext}"
            
            # Copy from source to destination
            # Convert HTTPS S3 URLs to s3:// format
            if asset_href.startswith('https://') and '.s3.' in asset_href and '.amazonaws.com/' in asset_href:
                # Parse HTTPS S3 URL: https://bucket.s3.region.amazonaws.com/key
                # or https://bucket.s3.amazonaws.com/key
                try:
                    # Extract bucket and key from HTTPS URL
                    parts = asset_href.replace('https://', '').split('/', 1)
                    if len(parts) == 2:
                        host = parts[0]
                        key = parts[1]
                        
                        # Extract bucket name from host
                        # Format: bucket.s3.region.amazonaws.com or bucket.s3.amazonaws.com
                        bucket_parts = host.split('.s3.')
                        if len(bucket_parts) == 2:
                            source_bucket = bucket_parts[0]
                            source_key = key
                            
                            # Copy object from source S3 to destination S3
                            copy_source = {'Bucket': source_bucket, 'Key': source_key}
                            s3_client.copy_object(
                                CopySource=copy_source,
                                Bucket=bucket,
                                Key=s3_key,
                                MetadataDirective='COPY'
                            )
                            
                            downloaded_assets.append({
                                'asset_key': asset_key,
                                's3_key': s3_key,
                                'source': asset_href,
                                'method': 'copy_https'
                            })
                            
                            logger.info(f"Copied {asset_key} from {asset_href} to s3://{bucket}/{s3_key}")
                            continue
                except Exception as e:
                    logger.error(f"Failed to copy HTTPS S3 asset {asset_key}: {e}")
                    continue
                    
            # Handle s3:// URLs
            if asset_href.startswith('s3://'):
                # Parse S3 URL
                source_bucket, source_key = parse_s3_url(asset_href)
                
                # Copy object
                copy_source = {'Bucket': source_bucket, 'Key': source_key}
                s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=bucket,
                    Key=s3_key,
                    MetadataDirective='COPY'
                )
                
                downloaded_assets.append({
                    'asset_key': asset_key,
                    's3_key': s3_key,
                    'source': asset_href,
                    'method': 'copy'
                })
                
                logger.info(f"Copied {asset_key} from {asset_href} to s3://{bucket}/{s3_key}")
                
            elif asset_href.startswith('http://') or asset_href.startswith('https://'):
                # For HTTP URLs, we would need to download and upload
                # This is more complex and may timeout in Lambda
                # For now, we'll skip HTTP downloads and only handle S3 copies
                logger.warning(f"Skipping HTTP asset {asset_key}: {asset_href}")
                continue
                
        except Exception as e:
            logger.error(f"Failed to download asset {asset_key}: {e}")
            continue
    
    return {
        'image_id': image_id,
        'status': 'success' if downloaded_assets else 'partial',
        'base_path': base_path,
        'downloaded_assets': downloaded_assets,
        'total_assets': len(downloaded_assets)
    }


def get_important_assets(satellite: str) -> List[str]:
    """Get list of important asset keys to download for each satellite"""
    asset_map = {
        'sentinel-2': [
            'B02', 'B03', 'B04', 'B08', 'B8A', 'B11', 'B12',  # Bands
            'blue', 'green', 'red', 'nir', 'nir08', 'swir16', 'swir22',  # Named bands
            'SCL', 'AOT', 'WVP',  # QA bands
        ],
        'sentinel-1': [
            'vv', 'vh', 'hh', 'hv',  # Polarizations
        ],
        'landsat-8': [
            'red', 'green', 'blue', 'nir08', 'swir16', 'swir22',
            'coastal', 'lwir11',
            'qa_pixel', 'qa_radsat', 'qa_aerosol',
        ],
        'modis': [
            'B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07',
            'Nadir_Reflectance_Band1', 'Nadir_Reflectance_Band2',
            'Nadir_Reflectance_Band3', 'Nadir_Reflectance_Band4',
        ],
    }
    
    return asset_map.get(satellite, [])


def get_file_extension(href: str, mime_type: str = None) -> str:
    """Determine file extension from URL or MIME type"""
    if href.endswith('.tif') or href.endswith('.tiff'):
        return '.tif'
    elif href.endswith('.jp2'):
        return '.jp2'
    elif href.endswith('.hdf'):
        return '.hdf'
    elif mime_type:
        if 'tiff' in mime_type.lower():
            return '.tif'
        elif 'jp2' in mime_type.lower() or 'jpeg2000' in mime_type.lower():
            return '.jp2'
    
    return '.tif'  # Default


def parse_s3_url(s3_url: str) -> tuple:
    """
    Parse S3 URL to bucket and key
    
    Args:
        s3_url: S3 URL like s3://bucket/key/path
        
    Returns:
        Tuple of (bucket, key)
    """
    if not s3_url.startswith('s3://'):
        raise ValueError(f'Invalid S3 URL: {s3_url}')
    
    parts = s3_url[5:].split('/', 1)
    if len(parts) != 2:
        raise ValueError(f'Invalid S3 URL format: {s3_url}')
    
    return parts[0], parts[1]
