"""
AOI API 路由
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.models.aoi import (
    AOIValidateRequest,
    AOIValidateResponse,
    AOIUploadResponse
)
from app.services.aoi_service import AOIService

router = APIRouter(prefix="/api/aoi", tags=["AOI"])

# 创建 AOI 服务实例
aoi_service = AOIService()


@router.post("/validate", response_model=AOIValidateResponse)
async def validate_aoi(request: AOIValidateRequest):
    """
    验证 AOI 几何有效性并计算面积和质心
    
    Args:
        request: AOI 验证请求
        
    Returns:
        AOIValidateResponse: 验证结果，包含面积和质心
        
    Raises:
        HTTPException: 如果几何无效
    """
    try:
        # 验证几何
        is_valid = aoi_service.validate_geometry(request.aoi)
        
        # 计算面积
        area_km2 = aoi_service.calculate_area_km2(request.aoi)
        
        # 计算质心
        centroid = aoi_service.calculate_centroid(request.aoi)
        
        # 计算边界
        bounds = aoi_service.calculate_bounds(request.aoi)
        
        return AOIValidateResponse(
            valid=is_valid,
            area_km2=area_km2,
            centroid=centroid,
            bounds=bounds
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_geometry",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "processing_error",
                "message": f"Failed to validate AOI: {str(e)}"
            }
        )


@router.post("/upload", response_model=AOIUploadResponse)
async def upload_aoi(file: UploadFile = File(...)):
    """
    上传 GeoJSON 文件并返回标准化的 AOI
    
    Args:
        file: 上传的 GeoJSON 文件
        
    Returns:
        AOIUploadResponse: 标准化的 GeoJSON、面积和边界
        
    Raises:
        HTTPException: 如果文件格式无效或解析失败
    """
    try:
        # 验证文件类型
        if not file.filename:
            raise ValueError("No filename provided")
        
        if not (file.filename.endswith('.json') or 
                file.filename.endswith('.geojson')):
            raise ValueError(
                "Invalid file format. Only .json and .geojson files are supported"
            )
        
        # 读取文件内容
        content = await file.read()
        
        if not content:
            raise ValueError("File is empty")
        
        # 解析 GeoJSON
        aoi = aoi_service.parse_geojson_file(content)
        
        # 验证几何
        aoi_service.validate_geometry(aoi)
        
        # 标准化 GeoJSON
        standardized_aoi = aoi_service.standardize_geojson(aoi)
        
        # 计算面积
        area_km2 = aoi_service.calculate_area_km2(standardized_aoi)
        
        # 计算边界
        bounds = aoi_service.calculate_bounds(standardized_aoi)
        
        return AOIUploadResponse(
            aoi=standardized_aoi,
            area_km2=area_km2,
            bounds=bounds
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_file_format",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "processing_error",
                "message": f"Failed to process uploaded file: {str(e)}"
            }
        )
