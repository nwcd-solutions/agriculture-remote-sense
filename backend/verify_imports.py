#!/usr/bin/env python3
"""
Verification script to test all module imports
Run this to ensure all Lambda handlers and common modules can be imported correctly
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports"""
    results = []
    
    # Test Lambda handlers
    try:
        from lambda_handlers.query_handler import handler as query_handler
        results.append(("✅", "lambda_handlers.query_handler", "OK"))
    except Exception as e:
        results.append(("❌", "lambda_handlers.query_handler", str(e)))
    
    try:
        from lambda_handlers.process_handler import handler as process_handler
        results.append(("✅", "lambda_handlers.process_handler", "OK"))
    except Exception as e:
        results.append(("❌", "lambda_handlers.process_handler", str(e)))
    
    try:
        from lambda_handlers.aoi_handler import handler as aoi_handler
        results.append(("✅", "lambda_handlers.aoi_handler", "OK"))
    except Exception as e:
        results.append(("❌", "lambda_handlers.aoi_handler", str(e)))
    
    # Test common modules
    try:
        from common.security import get_cors_headers, sanitize_log_data, safe_error_response
        results.append(("✅", "common.security", "OK"))
    except Exception as e:
        results.append(("❌", "common.security", str(e)))
    
    try:
        from common.validators import (
            validate_date_range,
            validate_bbox,
            validate_limit,
            validate_file_size,
            validate_aoi_area
        )
        results.append(("✅", "common.validators", "OK"))
    except Exception as e:
        results.append(("❌", "common.validators", str(e)))
    
    # Test batch processor
    try:
        import batch_processor
        results.append(("✅", "batch_processor", "OK"))
    except Exception as e:
        results.append(("❌", "batch_processor", str(e)))
    
    # Print results
    print("\n" + "="*70)
    print("🔍 Import Verification Results")
    print("="*70 + "\n")
    
    for status, module, message in results:
        print(f"{status} {module:40s} {message}")
    
    # Summary
    success_count = sum(1 for r in results if r[0] == "✅")
    total_count = len(results)
    
    print("\n" + "="*70)
    print(f"📊 Summary: {success_count}/{total_count} imports successful")
    print("="*70 + "\n")
    
    if success_count == total_count:
        print("🎉 All imports successful! Backend is ready for deployment.")
        return 0
    else:
        print("⚠️  Some imports failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(test_imports())
