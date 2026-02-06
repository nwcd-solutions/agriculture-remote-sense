"""
Lambda handler for satellite data query
Implements all query functionality from the original ECS API
Standalone version - no external dependencies
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))


def handler(event, context):
    """
    Handle satellite data query requests
    
    Routes:
    - POST /api/query - Query satellite data from STAC API
    - GET / - Health check
    - GET /health - Health check
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method'))
        path = event.get('path', event.get('rawPath', ''))
        
        # Health check endpoints
        if path in ['/', '/health'] and http_method == 'GET':
            return health_check()
        
        # Query endpoint
        if http_method == 'POST' and '/query' in path:
            return query_satellite_data(event)
        
        # OPTIONS for CORS
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': ''
            }
        
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


def cors_headers():
    """Return CORS headers"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }


def health_check():
    """Health check endpoint"""
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({
            'status': 'healthy',
            'service': 'satellite-gis-query-lambda',
            'version': '2.0.0-standalone'
        })
    }


def query_satellite_data(event):
    """
    Query satellite data from STAC API
    
    Supports:
    - Sentinel-2 (L1C, L2A)
    - Sentinel-1 (GRD, RTC)
    - Landsat-8 (L1, L2)
    - MODIS
    """
    import urllib.request
    import urllib.error
    
    body = json.loads(event.get('body', '{}'))
    
    # Extract parameters - support both old and new format
    satellite = body.get('satellite', 'sentinel-2')
    
    # Handle AOI - can be GeoJSON or bbox
    aoi = body.get('aoi')
    bbox = body.get('bbox')
    
    if aoi and not bbox:
        # Convert GeoJSON to bbox
        bbox = geojson_to_bbox(aoi)
    
    # Handle date range - support both formats
    date_range = body.get('date_range', {})
    start_date = body.get('start_date') or date_range.get('start')
    end_date = body.get('end_date') or date_range.get('end')
    
    # Other parameters
    cloud_cover_max = body.get('cloud_cover_max') or body.get('cloud_cover', 100)
    product_level = body.get('product_level')
    limit = body.get('limit', 100)
    
    logger.info(f"Query params: satellite={satellite}, bbox={bbox}, dates={start_date} to {end_date}, cloud={cloud_cover_max}")
    
    # Validate parameters
    if not bbox or len(bbox) != 4:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid bbox or aoi parameter. Expected bbox [west, south, east, north] or GeoJSON aoi'})
        }
    
    if not start_date or not end_date:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'start_date/end_date or date_range is required'})
        }
    
    # Determine collection based on satellite type
    collection, query_params = get_collection_config(satellite, product_level, cloud_cover_max)
    
    if not collection:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Unsupported satellite type: {satellite}'})
        }
    
    # Query STAC API
    stac_url = "https://earth-search.aws.element84.com/v1/search"
    
    # Format dates
    start_dt = format_date(start_date)
    end_dt = format_date(end_date)
    
    search_body = {
        "collections": [collection],
        "bbox": bbox,
        "datetime": f"{start_dt}/{end_dt}",
        "limit": min(limit, 100),
        "sortby": [
            {"field": "properties.datetime", "direction": "desc"}
        ]
    }
    
    # Add query parameters (cloud cover, etc.)
    if query_params:
        search_body["query"] = query_params
    
    try:
        # Make request to STAC API
        req = urllib.request.Request(
            stac_url,
            data=json.dumps(search_body).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            stac_response = json.loads(response.read().decode('utf-8'))
        
        # Process results
        features = stac_response.get('features', [])
        results = []
        
        for feature in features:
            result = process_stac_item(feature, satellite)
            results.append(result)
        
        logger.info(f"Found {len(results)} results for {satellite}")
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'results': results,
                'count': len(results),
                'query': {
                    'satellite': satellite,
                    'bbox': bbox,
                    'start_date': start_date,
                    'end_date': end_date,
                    'cloud_cover_max': cloud_cover_max,
                    'product_level': product_level
                }
            })
        }
        
    except urllib.error.URLError as e:
        logger.error(f"STAC API error: {str(e)}")
        return {
            'statusCode': 502,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Failed to query STAC API: {str(e)}'})
        }
    except Exception as e:
        logger.error(f"Query error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def geojson_to_bbox(geojson: Dict[str, Any]) -> List[float]:
    """Convert GeoJSON geometry to bbox [west, south, east, north]"""
    try:
        coords = geojson.get('coordinates', [[]])[0]
        if not coords:
            return None
        
        lons = [coord[0] for coord in coords]
        lats = [coord[1] for coord in coords]
        return [min(lons), min(lats), max(lons), max(lats)]
    except Exception as e:
        logger.error(f"Error converting GeoJSON to bbox: {e}")
        return None


def format_date(date_str: str) -> str:
    """Format date string to ISO format"""
    if 'T' in date_str:
        return date_str
    return f"{date_str}T00:00:00Z"


def get_collection_config(satellite: str, product_level: Optional[str], cloud_cover_max: float) -> tuple:
    """Get STAC collection name and query parameters based on satellite type"""
    
    query_params = {}
    
    if satellite == 'sentinel-2':
        level = (product_level or 'L2A').lower()
        collection = f"sentinel-2-{level}"
        if cloud_cover_max < 100:
            query_params["eo:cloud_cover"] = {"lt": cloud_cover_max}
            
    elif satellite == 'sentinel-1':
        product_type = (product_level or 'GRD').upper()
        collection = "sentinel-1-grd" if product_type == "GRD" else "sentinel-1-rtc"
        
    elif satellite == 'landsat-8':
        level = (product_level or 'L2').lower()
        collection = f"landsat-c2-{level}"
        if cloud_cover_max < 100:
            query_params["eo:cloud_cover"] = {"lt": cloud_cover_max}
            
    elif satellite == 'modis':
        product = (product_level or 'MCD43A4').lower()
        collection = f"modis-{product}"
        
    else:
        return None, None
    
    return collection, query_params if query_params else None


def process_stac_item(feature: Dict[str, Any], satellite: str) -> Dict[str, Any]:
    """Process a STAC item into the response format"""
    
    props = feature.get('properties', {})
    assets = feature.get('assets', {})
    
    # Get cloud cover
    cloud_cover = props.get('eo:cloud_cover')
    
    # Get thumbnail URL
    thumbnail_url = None
    if 'thumbnail' in assets:
        thumbnail_url = assets['thumbnail'].get('href')
    elif 'visual' in assets:
        thumbnail_url = assets['visual'].get('href')
    elif 'rendered_preview' in assets:
        thumbnail_url = assets['rendered_preview'].get('href')
    
    # Get product level
    product_level = (
        props.get('s2:product_type') or
        props.get('processing:level') or
        props.get('landsat:collection_category')
    )
    
    # Process assets - include commonly used bands
    important_assets = ['visual', 'thumbnail', 'rendered_preview', 
                       'B02', 'B03', 'B04', 'B08', 'B8A', 'B11', 'B12',  # Sentinel-2
                       'SCL', 'AOT', 'WVP',  # Sentinel-2 auxiliary
                       'red', 'green', 'blue', 'nir08', 'swir16', 'swir22',  # Landsat
                       'qa_pixel', 'qa_radsat',  # Landsat QA
                       'vv', 'vh',  # Sentinel-1
                       ]
    
    processed_assets = {}
    for name, asset in assets.items():
        if name in important_assets or len(processed_assets) < 20:
            processed_assets[name] = {
                'href': asset.get('href'),
                'type': asset.get('type'),
                'title': asset.get('title'),
                'roles': asset.get('roles')
            }
    
    return {
        'id': feature.get('id'),
        'datetime': props.get('datetime'),
        'satellite': satellite,
        'product_level': product_level,
        'cloud_cover': cloud_cover,
        'thumbnail_url': thumbnail_url,
        'bbox': feature.get('bbox'),
        'geometry': feature.get('geometry'),
        'assets': processed_assets,
        'properties': {
            'platform': props.get('platform'),
            'constellation': props.get('constellation'),
            'instrument': props.get('instruments'),
            'gsd': props.get('gsd'),
            'view:sun_azimuth': props.get('view:sun_azimuth'),
            'view:sun_elevation': props.get('view:sun_elevation'),
            's2:tile_id': props.get('s2:tile_id'),
            's2:granule_id': props.get('s2:granule_id'),
            'landsat:wrs_path': props.get('landsat:wrs_path'),
            'landsat:wrs_row': props.get('landsat:wrs_row'),
        }
    }
