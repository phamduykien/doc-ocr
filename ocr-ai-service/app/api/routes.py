from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
import logging
from datetime import datetime

from app.models.schemas import (
    DocumentProcessingRequest, DocumentProcessingResponse, 
    DocumentListResponse, ErrorResponse, HealthResponse,
    ConfigurationResponse, DocumentType, FieldType, ProcessingStatus
)
from app.services.document_service import DocumentService
from config.settings import settings

logger = logging.getLogger(__name__)

# Tạo router
router = APIRouter()

# Khởi tạo document service
document_service = DocumentService()

def get_document_service():
    """Dependency để lấy document service"""
    return document_service

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Kiểm tra sức khỏe của service"""
    try:
        # Kiểm tra các dịch vụ
        services_status = {
            "ocr_service": "healthy",
            "ai_service": "healthy" if settings.OPENAI_API_KEY else "limited",
            "document_service": "healthy"
        }
        
        return HealthResponse(
            status="healthy",
            version=settings.VERSION,
            timestamp=datetime.now(),
            services=services_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            version=settings.VERSION,
            timestamp=datetime.now(),
            services={"error": str(e)}
        )

@router.get("/config", response_model=ConfigurationResponse, tags=["System"])
async def get_configuration():
    """Lấy cấu hình hệ thống"""
    return ConfigurationResponse(
        document_types=list(DocumentType),
        field_types=list(FieldType),
        supported_languages=["vie", "eng", "vie+eng"],
        max_file_size=settings.MAX_FILE_SIZE,
        allowed_extensions=list(settings.ALLOWED_EXTENSIONS)
    )

@router.post("/documents/process", response_model=DocumentProcessingResponse, tags=["Document Processing"])
async def process_document(
    file: UploadFile = File(..., description="File PDF cần xử lý"),
    document_type: Optional[DocumentType] = Form(None, description="Loại tài liệu (tự động nhận diện nếu không chỉ định)"),
    custom_fields: Optional[str] = Form(None, description="Danh sách trường tùy chỉnh (cách nhau bởi dấu phẩy)"),
    ocr_language: Optional[str] = Form("vie+eng", description="Ngôn ngữ OCR"),
    ai_model: Optional[str] = Form(None, description="Model AI sử dụng"),
    service: DocumentService = Depends(get_document_service)
):
    """
    Xử lý tài liệu PDF với OCR và AI
    
    - **file**: File PDF cần xử lý
    - **document_type**: Loại tài liệu (tự động nhận diện từ tên file nếu không chỉ định)
    - **custom_fields**: Danh sách trường tùy chỉnh
    - **ocr_language**: Ngôn ngữ OCR (mặc định: vie+eng)
    - **ai_model**: Model AI sử dụng
    
    Trả về kết quả xử lý bao gồm:
    - Kết quả OCR cho từng trang
    - Dữ liệu được trích xuất bởi AI
    - Confidence score và thời gian xử lý
    """
    try:
        # Đọc nội dung file
        file_content = await file.read()
        
        # Xử lý custom_fields
        custom_fields_list = None
        if custom_fields:
            custom_fields_list = [field.strip() for field in custom_fields.split(",")]
        
        # Tạo request
        request = DocumentProcessingRequest(
            document_type=document_type,
            custom_fields=custom_fields_list,
            ocr_language=ocr_language,
            ai_model=ai_model
        )
        
        # Xử lý tài liệu
        result = service.process_document(file_content, file.filename, request)
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi xử lý tài liệu: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý tài liệu: {str(e)}")

@router.get("/documents/{document_id}", response_model=DocumentProcessingResponse, tags=["Document Management"])
async def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service)
):
    """
    Lấy thông tin tài liệu đã xử lý
    
    - **document_id**: ID của tài liệu
    """
    result = service.get_document(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    
    return result

@router.get("/documents", response_model=DocumentListResponse, tags=["Document Management"])
async def list_documents(
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(10, ge=1, le=100, description="Kích thước trang"),
    service: DocumentService = Depends(get_document_service)
):
    """
    Lấy danh sách tài liệu đã xử lý
    
    - **page**: Số trang (bắt đầu từ 1)
    - **page_size**: Kích thước trang (tối đa 100)
    """
    result = service.list_documents(page, page_size)
    
    return DocumentListResponse(
        documents=result["documents"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"]
    )

@router.delete("/documents/{document_id}", tags=["Document Management"])
async def delete_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service)
):
    """
    Xóa tài liệu đã xử lý
    
    - **document_id**: ID của tài liệu
    """
    success = service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    
    return {"message": "Đã xóa tài liệu thành công"}

@router.post("/documents/{document_id}/reprocess", response_model=DocumentProcessingResponse, tags=["Document Processing"])
async def reprocess_document(
    document_id: str,
    document_type: Optional[DocumentType] = Form(None, description="Loại tài liệu mới"),
    custom_fields: Optional[str] = Form(None, description="Danh sách trường tùy chỉnh mới"),
    service: DocumentService = Depends(get_document_service)
):
    """
    Xử lý lại tài liệu với cấu hình mới
    
    - **document_id**: ID của tài liệu
    - **document_type**: Loại tài liệu mới
    - **custom_fields**: Danh sách trường tùy chỉnh mới
    """
    try:
        # Xử lý custom_fields
        custom_fields_list = None
        if custom_fields:
            custom_fields_list = [field.strip() for field in custom_fields.split(",")]
        
        # Tạo request
        request = DocumentProcessingRequest(
            document_type=document_type,
            custom_fields=custom_fields_list
        )
        
        # Xử lý lại tài liệu
        result = service.reprocess_document(document_id, request)
        
        if not result:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
        
        return result
        
    except Exception as e:
        logger.error(f"Lỗi xử lý lại tài liệu: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý lại tài liệu: {str(e)}")

@router.get("/statistics", tags=["Analytics"])
async def get_statistics(
    service: DocumentService = Depends(get_document_service)
):
    """
    Lấy thống kê xử lý tài liệu
    
    Trả về:
    - Tổng số tài liệu đã xử lý
    - Thống kê theo trạng thái
    - Thống kê theo loại tài liệu
    - Thời gian xử lý trung bình
    - Confidence score trung bình
    """
    return service.get_statistics()

@router.post("/maintenance/cleanup", tags=["System"])
async def cleanup_old_documents(
    max_age_hours: int = Query(24, ge=1, description="Tuổi tối đa (giờ)"),
    service: DocumentService = Depends(get_document_service)
):
    """
    Dọn dẹp các tài liệu cũ
    
    - **max_age_hours**: Tuổi tối đa của tài liệu (giờ)
    """
    cleaned_count = service.cleanup_old_documents(max_age_hours)
    return {"message": f"Đã dọn dẹp {cleaned_count} tài liệu cũ"}

@router.get("/documents/{document_id}/ocr", tags=["Document Details"])
async def get_document_ocr(
    document_id: str,
    page: Optional[int] = Query(None, ge=1, description="Số trang cụ thể"),
    service: DocumentService = Depends(get_document_service)
):
    """
    Lấy kết quả OCR chi tiết của tài liệu
    
    - **document_id**: ID của tài liệu
    - **page**: Số trang cụ thể (nếu không chỉ định sẽ trả về tất cả)
    """
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    
    ocr_results = document.ocr_results
    
    # Lọc theo trang nếu được chỉ định
    if page is not None:
        ocr_results = [result for result in ocr_results if result.page_number == page]
        if not ocr_results:
            raise HTTPException(status_code=404, detail="Không tìm thấy trang")
    
    return {
        "document_id": document_id,
        "total_pages": document.total_pages,
        "ocr_results": ocr_results
    }

@router.get("/documents/{document_id}/fields", tags=["Document Details"])
async def get_document_fields(
    document_id: str,
    service: DocumentService = Depends(get_document_service)
):
    """
    Lấy danh sách trường dữ liệu của tài liệu
    
    - **document_id**: ID của tài liệu
    """
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    
    return {
        "document_id": document_id,
        "document_type": document.document_type,
        "fields": document.ai_extraction.fields,
        "confidence_score": document.ai_extraction.confidence_score
    }

# Note: Exception handlers sẽ được thêm vào main.py
