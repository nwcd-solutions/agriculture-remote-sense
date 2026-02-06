"""
Lambda handler for AOI (Area of Interest) operations
Implements AOI validation and file upload functionality
Standalone version - no external dependencies
"""
import json
import os
import logging
import base64
import math
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))


def handler(event, context):
    """
    Handle AOI requests
    
    Routes:
    - POST /api/aoi/validate - Validate AOI geometry
    - POST /api/aoi/upload - Upload and parse GeoJSON file
    - GET /health - Health check
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method'))
        path = event.get('path', event.get('rawPath', ''))
        
        # Health check
        if path in ['/', '/health'] and http_method == 'GET':
            return health_check()
        
        # AOI validate endpoint
        if http_method == 'POST' and '/validate' in path:
            return validate_aoi(event)
        
        # AOI upload endpoint
        if http_method == 'POST' and '/upload' in path:
            return upload_aoi(event)
        
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
            'service': 'satellite-gis-aoi-lambda',
            'version': '2.0.0-standalone'
        })
    }


def validate_aoi(event):
    """
    Validate AOI geometry and calculate area/centroid/bounds
    """
    try:
        body = json.loads(event.get('body', '{}'))
        aoi = body.get('aoi')
        
        if not aoi:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'AOI is required'})
            }
        
        # Validate geometry
        is_valid, error_msg = validate_geometry(aoi)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'invalid_geometry',
                    'message': error_msg
                })
            }
        
        # Calculate area
        area_km2 = calculate_area_km2(aoi)
        
        # Calculate centroid
        centroid = calculate_centroid(aoi)
        
        # Calculate bounds
        bounds = calculate_bounds(aoi)
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'valid': True,
                'area_km2': area_km2,
                'centroid': centroid,
                'bounds': bounds
            })
        }
        
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Invalid JSON: {str(e)}'})
        }
    except Exception as e:
        logger.error(f"Validate AOI error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def upload_aoi(event):
    """
    Upload and parse GeoJSON file
    Supports both base64 encoded body and multipart form data
    """
    try:
        content_type = event.get('headers', {}).get('content-type', '') or \
                       event.get('headers', {}).get('Content-Type', '')
        
        # Handle multipart form data or base64 encoded body
        if 'multipart/form-data' in content_type:
            file_content = parse_multipart_body(event)
        else:
            # Assume base64 encoded JSON body with file content
            body = event.get('body', '')
            is_base64 = event.get('isBase64Encoded', False)
            
            if is_base64:
                file_content = base64.b64decode(body)
            else:
                # Try to parse as JSON with file_content field
                try:
                    body_json = json.loads(body)
                    if 'file_content' in body_json:
                        file_content = base64.b64decode(body_json['file_content'])
                    elif 'geojson' in body_json:
                        # Direct GeoJSON input
                        aoi = body_json['geojson']
                        return process_geojson(aoi)
                    else:
                        file_content = body.encode('utf-8')
                except json.JSONDecodeError:
                    file_content = body.encode('utf-8')
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'No file content provided'})
            }
        
        # Parse GeoJSON
        try:
            geojson_data = json.loads(file_content.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'invalid_file_format',
                    'message': f'Failed to parse GeoJSON: {str(e)}'
                })
            }
        
        return process_geojson(geojson_data)
        
    except Exception as e:
        logger.error(f"Upload AOI error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def process_geojson(geojson_data: Dict[str, Any]):
    """Process and standardize GeoJSON data"""
    # Standardize GeoJSON
    aoi = standardize_geojson(geojson_data)
    
    if not aoi:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'invalid_file_format',
                'message': 'Could not extract valid geometry from GeoJSON'
            })
        }
    
    # Validate geometry
    is_valid, error_msg = validate_geometry(aoi)
    if not is_valid:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'invalid_geometry',
                'message': error_msg
            })
        }
    
    # Calculate area and bounds
    area_km2 = calculate_area_km2(aoi)
    bounds = calculate_bounds(aoi)
    
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({
            'aoi': aoi,
            'area_km2': area_km2,
            'bounds': bounds
        })
    }


def parse_multipart_body(event) -> Optional[bytes]:
    """Parse multipart form data to extract file content"""
    try:
        content_type = event.get('headers', {}).get('content-type', '') or \
                       event.get('headers', {}).get('Content-Type', '')
        
        # Extract boundary
        boundary = None
        for part in content_type.split(';'):
            part = part.strip()
            if part.startswith('boundary='):
                boundary = part[9:].strip('"')
                break
        
        if not boundary:
            return None
        
        body = event.get('body', '')
        is_base64 = event.get('isBase64Encoded', False)
        
        if is_base64:
            body = base64.b64decode(body)
        else:
            body = body.encode('utf-8')
        
        # Simple multipart parser
        boundary_bytes = f'--{boundary}'.encode('utf-8')
        parts = body.split(boundary_bytes)
        
        for part in parts:
            if b'filename=' in part and b'Content-Type' in part:
                # Find the content after headers
                header_end = part.find(b'\r\n\r\n')
                if header_end != -1:
                    content = part[header_end + 4:]
                    # Remove trailing boundary markers
                    if content.endswith(b'--\r\n'):
                        content = content[:-4]
                    elif content.endswith(b'\r\n'):
                        content = content[:-2]
                    return content
        
        return None
    except Exception as e:
        logger.error(f"Error parsing multipart body: {e}")
        return None


def validate_geometry(geojson: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate GeoJSON geometry"""
    try:
        geom_type = geojson.get('type')
        
        if geom_type not in ['Polygon', 'MultiPolygon']:
            return False, f"Unsupported geometry type: {geom_type}. Expected Polygon or MultiPolygon"
        
        coords = geojson.get('coordinates')
        if not coords:
            return False, "No coordinates found"
        
        if geom_type == 'Polygon':
            if not validate_polygon_coords(coords):
                return False, "Invalid polygon coordinates"
        elif geom_type == 'MultiPolygon':
            for polygon_coords in coords:
                if not validate_polygon_coords(polygon_coords):
                    return False, "Invalid multipolygon coordinates"
        
        return True, None
        
    except Exception as e:
        return False, str(e)


def validate_polygon_coords(coords: List) -> bool:
    """Validate polygon coordinates"""
    if not coords or not isinstance(coords, list):
        return False
    
    # Check outer ring
    outer_ring = coords[0] if coords else []
    if len(outer_ring) < 4:
        return False
    
    # Check if ring is closed
    if outer_ring[0] != outer_ring[-1]:
        return False
    
    # Validate coordinate values
    for coord in outer_ring:
        if not isinstance(coord, (list, tuple)) or len(coord) < 2:
            return False
        lon, lat = coord[0], coord[1]
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return False
    
    return True


def standardize_geojson(geojson_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Standardize GeoJSON to a simple Polygon/MultiPolygon geometry"""
    geom_type = geojson_data.get('type')
    
    if geom_type in ['Polygon', 'MultiPolygon']:
        return geojson_data
    
    if geom_type == 'Feature':
        geometry = geojson_data.get('geometry')
        if geometry and geometry.get('type') in ['Polygon', 'MultiPolygon']:
            return geometry
    
    if geom_type == 'FeatureCollection':
        features = geojson_data.get('features', [])
        for feature in features:
            geometry = feature.get('geometry')
            if geometry and geometry.get('type') in ['Polygon', 'MultiPolygon']:
                return geometry
    
    return None


def calculate_area_km2(geojson: Dict[str, Any]) -> float:
    """Calculate area in square kilometers using spherical excess formula"""
    try:
        geom_type = geojson.get('type')
        coords = geojson.get('coordinates', [])
        
        if geom_type == 'Polygon':
            return abs(polygon_area(coords[0]))
        elif geom_type == 'MultiPolygon':
            total_area = 0
            for polygon_coords in coords:
                total_area += abs(polygon_area(polygon_coords[0]))
            return total_area
        
        return 0.0
    except Exception as e:
        logger.error(f"Error calculating area: {e}")
        return 0.0


def polygon_area(ring: List[List[float]]) -> float:
    """
    Calculate polygon area using the Shoelace formula with geodesic correction
    Returns area in square kilometers
    """
    if len(ring) < 4:
        return 0.0
    
    # Earth radius in km
    R = 6371.0
    
    # Convert to radians and calculate area using spherical excess
    total = 0.0
    n = len(ring) - 1  # Exclude closing point
    
    for i in range(n):
        j = (i + 1) % n
        
        lon1 = math.radians(ring[i][0])
        lat1 = math.radians(ring[i][1])
        lon2 = math.radians(ring[j][0])
        lat2 = math.radians(ring[j][1])
        
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    
    area = abs(total * R * R / 2.0)
    return round(area, 4)


def calculate_centroid(geojson: Dict[str, Any]) -> Dict[str, float]:
    """Calculate centroid of geometry"""
    try:
        coords = get_all_coordinates(geojson)
        
        if not coords:
            return {'lon': 0, 'lat': 0}
        
        sum_lon = sum(c[0] for c in coords)
        sum_lat = sum(c[1] for c in coords)
        n = len(coords)
        
        return {
            'lon': round(sum_lon / n, 6),
            'lat': round(sum_lat / n, 6)
        }
    except Exception as e:
        logger.error(f"Error calculating centroid: {e}")
        return {'lon': 0, 'lat': 0}


def calculate_bounds(geojson: Dict[str, Any]) -> List[float]:
    """Calculate bounding box [west, south, east, north]"""
    try:
        coords = get_all_coordinates(geojson)
        
        if not coords:
            return [0, 0, 0, 0]
        
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        return [
            round(min(lons), 6),
            round(min(lats), 6),
            round(max(lons), 6),
            round(max(lats), 6)
        ]
    except Exception as e:
        logger.error(f"Error calculating bounds: {e}")
        return [0, 0, 0, 0]


def get_all_coordinates(geojson: Dict[str, Any]) -> List[List[float]]:
    """Extract all coordinates from geometry"""
    geom_type = geojson.get('type')
    coords = geojson.get('coordinates', [])
    
    all_coords = []
    
    if geom_type == 'Polygon':
        for ring in coords:
            all_coords.extend(ring[:-1])  # Exclude closing point
    elif geom_type == 'MultiPolygon':
        for polygon in coords:
            for ring in polygon:
                all_coords.extend(ring[:-1])
    
    return all_coords
