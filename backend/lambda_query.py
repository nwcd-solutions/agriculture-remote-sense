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
    polarization = body.get('polarization')  # For Sentinel-1: ["VV", "VH"]
    limit = body.get('limit', 100)
    
    logger.info(f"Query params: satellite={satellite}, bbox={bbox}, dates={start_date} to {end_date}, cloud={cloud_cover_max}, polarization={polarization}")
    
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
    collection, query_params = get_collection_config(satellite, product_level, cloud_cover_max, polarization)
    
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
                    'product_level': product_level,
                    'polarization': polarization
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


def get_collection_config(satellite: str, product_level: Optional[str], cloud_cover_max: float, polarization: Optional[List[str]] = None) -> tuple:
    """
    Get STAC collection name and query parameters based on satellite type.
    
    Supported satellites and products:
    - sentinel-1: GRD (Ground Range Detected), RTC (Radiometric Terrain Corrected)
      - Polarizations: VV, VH, VV+VH
    - sentinel-2: L1C (Top-of-Atmosphere), L2A (Surface Reflectance)
    - landsat-8: L1 (Collection 2 Level-1), L2 (Collection 2 Level-2)
    - modis: Terra and Aqua products
      - MOD09A1 (Terra reflectance), MYD09A1 (Aqua reflectance)
      - MCD43A4 (Combined BRDF reflectance)
      - MOD13A1 (Terra vegetation), MYD13A1 (Aqua vegetation)
      - MOD11A1 (Terra LST), MYD11A1 (Aqua LST)
    """
    
    query_params = {}
    
    if satellite == 'sentinel-2':
        level = (product_level or 'L2A').lower()
        collection = f"sentinel-2-{level}"
        if cloud_cover_max < 100:
            query_params["eo:cloud_cover"] = {"lt": cloud_cover_max}
            
    elif satellite == 'sentinel-1':
        product_type = (product_level or 'GRD').upper()
        collection_map = {
            "GRD": "sentinel-1-grd",
            "RTC": "sentinel-1-rtc",
        }
        collection = collection_map.get(product_type, "sentinel-1-grd")
        # Sentinel-1 SAR 数据没有云量概念，不添加云量过滤
        # 添加极化过滤
        if polarization:
            query_params["sar:polarizations"] = {"eq": polarization}
        
    elif satellite == 'landsat-8':
        level = (product_level or 'L2').lower()
        collection = f"landsat-c2-{level}"
        if cloud_cover_max < 100:
            query_params["eo:cloud_cover"] = {"lt": cloud_cover_max}
            
    elif satellite == 'modis':
        product = (product_level or 'MCD43A4').upper()
        # MODIS 产品映射
        modis_collections = {
            "MOD09A1": "modis-mod09a1",     # Terra 反射率
            "MYD09A1": "modis-myd09a1",     # Aqua 反射率
            "MCD43A4": "modis-mcd43a4",     # Combined BRDF
            "MOD13A1": "modis-mod13a1",     # Terra 植被指数
            "MYD13A1": "modis-myd13a1",     # Aqua 植被指数
            "MOD11A1": "modis-mod11a1",     # Terra 地表温度
            "MYD11A1": "modis-myd11a1",     # Aqua 地表温度
        }
        collection = modis_collections.get(product, f"modis-{product.lower()}")
        # MODIS 没有标准的 eo:cloud_cover 字段
        
    else:
        return None, None
    
    return collection, query_params if query_params else None


def process_stac_item(feature: Dict[str, Any], satellite: str) -> Dict[str, Any]:
    """Process a STAC item into the response format, with satellite-specific metadata"""
    
    props = feature.get('properties', {})
    assets = feature.get('assets', {})
    
    # Get cloud cover (optical sensors only)
    cloud_cover = props.get('eo:cloud_cover')
    
    # Get thumbnail URL
    thumbnail_url = None
    for thumb_key in ['thumbnail', 'visual', 'rendered_preview']:
        if thumb_key in assets:
            thumbnail_url = assets[thumb_key].get('href')
            break
    
    # Get product level - satellite-specific extraction
    product_level = None
    if satellite == 'sentinel-2':
        product_level = props.get('s2:product_type') or props.get('processing:level')
    elif satellite == 'sentinel-1':
        product_level = props.get('sar:product_type') or props.get('s1:product_timeliness')
    elif satellite == 'landsat-8':
        product_level = props.get('landsat:collection_category') or props.get('processing:level')
    elif satellite == 'modis':
        product_level = props.get('processing:level')
    
    if not product_level:
        product_level = (
            props.get('s2:product_type') or
            props.get('processing:level') or
            props.get('landsat:collection_category')
        )
    
    # Satellite-specific important assets
    important_assets_by_satellite = {
        'sentinel-2': [
            'visual', 'thumbnail', 'rendered_preview',
            'B02', 'B03', 'B04', 'B08', 'B8A', 'B11', 'B12',
            'blue', 'green', 'red', 'nir', 'nir08',
            'SCL', 'AOT', 'WVP',
        ],
        'sentinel-1': [
            'thumbnail', 'rendered_preview',
            'vv', 'vh', 'hh', 'hv',
        ],
        'landsat-8': [
            'visual', 'thumbnail', 'rendered_preview',
            'red', 'green', 'blue', 'nir08', 'swir16', 'swir22',
            'coastal', 'lwir11',
            'qa_pixel', 'qa_radsat', 'qa_aerosol',
        ],
        'modis': [
            'thumbnail', 'rendered_preview',
            'B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07',
            'Nadir_Reflectance_Band1', 'Nadir_Reflectance_Band2',
            'Nadir_Reflectance_Band3', 'Nadir_Reflectance_Band4',
        ],
    }
    
    important_assets = important_assets_by_satellite.get(satellite, [])
    
    processed_assets = {}
    for name, asset in assets.items():
        if name in important_assets or len(processed_assets) < 20:
            processed_assets[name] = {
                'href': asset.get('href'),
                'type': asset.get('type'),
                'title': asset.get('title'),
                'roles': asset.get('roles')
            }
    
    # Build satellite-specific properties
    extra_props = {
        'platform': props.get('platform'),
        'constellation': props.get('constellation'),
        'instrument': props.get('instruments'),
        'gsd': props.get('gsd'),
    }
    
    if satellite == 'sentinel-2':
        extra_props.update({
            'view:sun_azimuth': props.get('view:sun_azimuth'),
            'view:sun_elevation': props.get('view:sun_elevation'),
            's2:tile_id': props.get('s2:tile_id'),
            's2:granule_id': props.get('s2:granule_id'),
        })
    elif satellite == 'sentinel-1':
        extra_props.update({
            'sar:polarizations': props.get('sar:polarizations'),
            'sar:frequency_band': props.get('sar:frequency_band'),
            'sar:instrument_mode': props.get('sar:instrument_mode'),
            'sar:product_type': props.get('sar:product_type'),
            'sat:orbit_state': props.get('sat:orbit_state'),
            'sat:relative_orbit': props.get('sat:relative_orbit'),
        })
    elif satellite == 'landsat-8':
        extra_props.update({
            'view:sun_azimuth': props.get('view:sun_azimuth'),
            'view:sun_elevation': props.get('view:sun_elevation'),
            'landsat:wrs_path': props.get('landsat:wrs_path'),
            'landsat:wrs_row': props.get('landsat:wrs_row'),
            'landsat:scene_id': props.get('landsat:scene_id'),
            'landsat:collection_number': props.get('landsat:collection_number'),
        })
    elif satellite == 'modis':
        extra_props.update({
            'modis:horizontal_tile': props.get('modis:horizontal-tile'),
            'modis:vertical_tile': props.get('modis:vertical-tile'),
        })
    
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
        'properties': extra_props
    }
