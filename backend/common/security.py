"""
Security utilities for input validation and sanitization
"""
import os
import logging
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def get_cors_headers() -> Dict[str, str]:
    """
    Return CORS headers based on environment configuration
    
    Returns:
        Dict with CORS headers
    """
    # Read allowed origins from environment variable
    # In production, this should be set to your frontend domain
    allowed_origins = os.getenv('CORS_ORIGINS', '*')
    
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': allowed_origins,
        'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Credentials': 'true' if allowed_origins != '*' else 'false'
    }


def sanitize_log_data(data: Any) -> Any:
    """
    Remove sensitive information from log data
    
    Args:
        data: Data to sanitize (dict, list, or other)
        
    Returns:
        Sanitized data with sensitive fields redacted
    """
    if not isinstance(data, dict):
        return data
    
    sensitive_keys = ['password', 'token', 'key', 'secret', 'api_key', 'access_key', 'credentials']
    sanitized = {}
    
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized


def safe_error_response(error: Exception, status_code: int = 500) -> Dict[str, Any]:
    """
    Return safe error response based on environment
    
    Args:
        error: Exception that occurred
        status_code: HTTP status code
        
    Returns:
        Dict with statusCode, headers, and body
    """
    environment = os.getenv('ENVIRONMENT', 'dev')
    
    if environment == 'prod':
        # In production, return generic error
        error_msg = 'Internal server error'
        logger.error(f"Error occurred: {str(error)}", exc_info=True)
    else:
        # In development, return detailed error
        error_msg = str(error)
        logger.error(f"Error occurred: {error_msg}", exc_info=True)
    
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': __import__('json').dumps({'error': error_msg})
    }
