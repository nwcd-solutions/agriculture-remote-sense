"""
Input validation utilities
"""
import logging
from typing import List, Tuple, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def validate_date_range(start_date: str, end_date: str) -> Tuple[bool, Optional[str]]:
    """
    Validate date range to prevent excessive queries
    
    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Ensure timezone-aware
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        
        # Check if dates are in valid range
        if start > end:
            return False, "Start date must be before end date"
        
        # Limit to 5 years to prevent excessive queries
        if (end - start).days > 1825:
            return False, "Date range too large (maximum 5 years)"
        
        return True, None
    except (ValueError, AttributeError) as e:
        return False, f"Invalid date format: {str(e)}"


def validate_bbox(bbox: List[float]) -> Tuple[bool, Optional[str]]:
    """
    Validate bounding box coordinates
    
    Args:
        bbox: List of [west, south, east, north]
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not bbox or len(bbox) != 4:
        return False, "bbox must contain exactly 4 values [west, south, east, north]"
    
    west, south, east, north = bbox
    
    # Validate longitude range
    if not (-180 <= west <= 180) or not (-180 <= east <= 180):
        return False, "Longitude must be between -180 and 180"
    
    # Validate latitude range
    if not (-90 <= south <= 90) or not (-90 <= north <= 90):
        return False, "Latitude must be between -90 and 90"
    
    # Validate bbox is not inverted
    if west >= east:
        return False, "West must be less than east"
    
    if south >= north:
        return False, "South must be less than north"
    
    # Validate bbox is not too large (prevent abuse)
    # Maximum area: ~100,000 km² (roughly 10° x 10° at equator)
    if (east - west) > 10 or (north - south) > 10:
        return False, "Bounding box too large (maximum 10° x 10°)"
    
    return True, None


def validate_limit(limit: int) -> Tuple[bool, Optional[str]]:
    """
    Validate query limit parameter
    
    Args:
        limit: Query limit value
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(limit, int):
        return False, "limit must be an integer"
    
    if limit < 1:
        return False, "limit must be at least 1"
    
    if limit > 100:
        return False, "limit cannot exceed 100"
    
    return True, None


def validate_file_size(file_content: bytes, max_size_mb: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Validate file size
    
    Args:
        file_content: File content as bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if len(file_content) > max_size_bytes:
        return False, f'File size exceeds maximum allowed size of {max_size_mb}MB'
    
    return True, None


def validate_aoi_area(area_km2: float, max_area_km2: float = 100000) -> Tuple[bool, Optional[str]]:
    """
    Validate AOI area
    
    Args:
        area_km2: Area in square kilometers
        max_area_km2: Maximum allowed area
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if area_km2 > max_area_km2:
        return False, f'AOI area ({area_km2:.2f} km²) exceeds maximum allowed area of {max_area_km2:,} km²'
    
    return True, None
