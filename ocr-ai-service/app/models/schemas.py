from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    """Loại tài liệu"""
    THONG_TIN_HO_SO = "THONG_TIN_HO_SO"  # Bìa
    MUC_LUC_TAI_LIEU = "MUC_LUC_TAI_LIEU"  # Mục lục
    THONG_TIN_VAN_BAN = "THONG_TIN_VAN_BAN"  # Văn bản thường

class ProcessingStatus(str, Enum):
    """Trạng thái xử lý"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class FieldType(str, Enum):
    """Loại trường dữ liệu"""
    TEXT = "TEXT"
    NUMERIC = "NUMERIC"
    DATE = "DATE"
    DROPDOWN = "DROPDOWN"

class DocumentField(BaseModel):
    """Trường dữ liệu của tài liệu"""
    name: str = Field(..., description="Tên trường")
    value: Optional[str] = Field(None, description="Giá trị")
    field_type: FieldType = Field(..., description="Loại trường")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Điểm tin cậy")
    is_required: bool = Field(False, description="Bắt buộc nhập")
    is_verified: bool = Field(False, description="Đã được xác thực")
    original_text: Optional[str] = Field(None, description="Text gốc từ OCR")
    
class OCRResult(BaseModel):
    """Kết quả OCR"""
    text: str = Field(..., description="Văn bản được nhận dạng")
    confidence_score: float = Field(..., ge=0, le=1, description="Điểm tin cậy")
    bounding_box: Optional[Dict[str, int]] = Field(None, description="Vị trí vùng text")
    page_number: int = Field(..., description="Số trang")

class AIExtractionResult(BaseModel):
    """Kết quả trích xuất AI"""
    fields: List[DocumentField] = Field(..., description="Danh sách trường dữ liệu")
    confidence_score: float = Field(..., ge=0, le=1, description="Điểm tin cậy tổng thể")
    processing_time: float = Field(..., description="Thời gian xử lý (giây)")
    
class DocumentProcessingRequest(BaseModel):
    """Request xử lý tài liệu"""
    document_type: Optional[DocumentType] = Field(None, description="Loại tài liệu")
    custom_fields: Optional[List[str]] = Field(None, description="Danh sách trường tùy chỉnh")
    ocr_language: Optional[str] = Field("vie+eng", description="Ngôn ngữ OCR")
    ai_model: Optional[str] = Field(None, description="Model AI sử dụng")
    
class DocumentProcessingResponse(BaseModel):
    """Response xử lý tài liệu"""
    document_id: str = Field(..., description="ID tài liệu")
    filename: str = Field(..., description="Tên file")
    document_type: DocumentType = Field(..., description="Loại tài liệu")
    status: ProcessingStatus = Field(..., description="Trạng thái xử lý")
    ocr_results: List[OCRResult] = Field(..., description="Kết quả OCR")
    ai_extraction: AIExtractionResult = Field(..., description="Kết quả trích xuất AI")
    total_pages: int = Field(..., description="Tổng số trang")
    processing_time: float = Field(..., description="Thời gian xử lý tổng (giây)")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: Optional[datetime] = Field(None, description="Thời gian cập nhật")
    
class DocumentListResponse(BaseModel):
    """Response danh sách tài liệu"""
    documents: List[DocumentProcessingResponse] = Field(..., description="Danh sách tài liệu")
    total: int = Field(..., description="Tổng số tài liệu")
    page: int = Field(..., description="Trang hiện tại")
    page_size: int = Field(..., description="Kích thước trang")
    
class ErrorResponse(BaseModel):
    """Response lỗi"""
    error: str = Field(..., description="Mã lỗi")
    message: str = Field(..., description="Thông báo lỗi")
    details: Optional[Dict[str, Any]] = Field(None, description="Chi tiết lỗi")
    
class HealthResponse(BaseModel):
    """Response kiểm tra sức khỏe"""
    status: str = Field(..., description="Trạng thái")
    version: str = Field(..., description="Phiên bản")
    timestamp: datetime = Field(..., description="Thời gian")
    services: Dict[str, str] = Field(..., description="Trạng thái các dịch vụ")

class ConfigurationResponse(BaseModel):
    """Response cấu hình hệ thống"""
    document_types: List[DocumentType] = Field(..., description="Danh sách loại tài liệu")
    field_types: List[FieldType] = Field(..., description="Danh sách loại trường")
    supported_languages: List[str] = Field(..., description="Ngôn ngữ hỗ trợ")
    max_file_size: int = Field(..., description="Kích thước file tối đa")
    allowed_extensions: List[str] = Field(..., description="Phần mở rộng cho phép")
