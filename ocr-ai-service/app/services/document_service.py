import uuid
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import os

from app.models.schemas import (
    DocumentProcessingRequest, DocumentProcessingResponse, 
    DocumentType, ProcessingStatus, OCRResult, AIExtractionResult
)
from config.settings import settings

logger = logging.getLogger(__name__)

# Import OCR services với fallback
try:
    from app.services.ocr_service_advanced import OCRServiceAdvanced as OCRService
    logger.info("Sử dụng OCR Service nâng cao")
except ImportError:
    try:
        from app.services.ocr_service import OCRService
        logger.info("Sử dụng OCR Service cơ bản")
    except ImportError:
        from app.services.ocr_service_mock import OCRServiceMock as OCRService
        logger.info("Sử dụng OCR Service mock")

# Import AI services với fallback
try:
    from app.services.ai_service_local import AIServiceLocal as AIService
    logger.info("Sử dụng AI Service local")
except ImportError:
    from app.services.ai_service import AIService
    logger.info("Sử dụng AI Service cơ bản")

class DocumentService:
    """Dịch vụ chính để xử lý tài liệu (OCR + AI)"""
    
    def __init__(self):
        """Khởi tạo Document service"""
        self.ocr_service = OCRService()
        self.ai_service = AIService()
        self.processed_documents: Dict[str, DocumentProcessingResponse] = {}
        
        # Tạo thư mục upload nếu chưa tồn tại
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
    
    def validate_file(self, filename: str, file_size: int) -> Dict[str, Any]:
        """Validate file upload"""
        validation_result = {
            "is_valid": True,
            "errors": []
        }
        
        # Kiểm tra phần mở rộng
        file_ext = Path(filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Phần mở rộng {file_ext} không được hỗ trợ")
        
        # Kiểm tra kích thước file
        if file_size > settings.MAX_FILE_SIZE:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Kích thước file {file_size} vượt quá giới hạn {settings.MAX_FILE_SIZE}")
        
        return validation_result
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """Lưu file đã upload"""
        try:
            # Tạo tên file unique
            file_id = str(uuid.uuid4())
            file_ext = Path(filename).suffix
            saved_filename = f"{file_id}_{filename}"
            file_path = self.upload_dir / saved_filename
            
            # Lưu file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Đã lưu file: {saved_filename}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Lỗi lưu file: {str(e)}")
            raise
    
    def process_document(self, 
                        file_content: bytes, 
                        filename: str, 
                        request: DocumentProcessingRequest) -> DocumentProcessingResponse:
        """Xử lý tài liệu hoàn chỉnh (OCR + AI)"""
        
        start_time = time.time()
        document_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Bắt đầu xử lý tài liệu: {filename} (ID: {document_id})")
            
            # Validate file
            validation = self.validate_file(filename, len(file_content))
            if not validation["is_valid"]:
                raise ValueError(f"File không hợp lệ: {', '.join(validation['errors'])}")
            
            # Nhận diện loại tài liệu từ tên file nếu chưa được chỉ định
            document_type = request.document_type
            if not document_type:
                document_type = self.ocr_service.detect_document_type(filename)
            
            # Tạo response ban đầu
            response = DocumentProcessingResponse(
                document_id=document_id,
                filename=filename,
                document_type=document_type,
                status=ProcessingStatus.PROCESSING,
                ocr_results=[],
                ai_extraction=AIExtractionResult(
                    fields=[],
                    confidence_score=0.0,
                    processing_time=0.0
                ),
                total_pages=0,
                processing_time=0.0,
                created_at=datetime.now(),
                updated_at=None
            )
            
            # Lưu vào bộ nhớ tạm
            self.processed_documents[document_id] = response
            
            # Bước 1: OCR
            logger.info(f"Bước 1: Thực hiện OCR cho tài liệu {document_id}")
            ocr_results = self.ocr_service.process_pdf_bytes(file_content)
            
            # Cập nhật kết quả OCR
            response.ocr_results = ocr_results
            response.total_pages = len(ocr_results)
            
            # Bước 2: AI Extraction
            logger.info(f"Bước 2: Thực hiện AI extraction cho tài liệu {document_id}")
            combined_text = self.ocr_service.get_combined_text(ocr_results)
            
            ai_extraction = self.ai_service.process_document(
                text=combined_text,
                document_type=document_type,
                custom_fields=request.custom_fields
            )
            
            # Cập nhật kết quả AI
            response.ai_extraction = ai_extraction
            
            # Bước 3: Validation
            logger.info(f"Bước 3: Validate dữ liệu cho tài liệu {document_id}")
            validation_results = self.ai_service.validate_extracted_data(ai_extraction.fields)
            
            # Cập nhật trạng thái
            response.status = ProcessingStatus.COMPLETED
            response.processing_time = time.time() - start_time
            response.updated_at = datetime.now()
            
            # Lưu thông tin validation vào metadata (có thể mở rộng schema)
            logger.info(f"Validation results: {validation_results}")
            
            logger.info(f"Hoàn thành xử lý tài liệu {document_id}: "
                       f"OCR {len(ocr_results)} trang, "
                       f"AI {len(ai_extraction.fields)} trường, "
                       f"thời gian: {response.processing_time:.2f}s")
            
            return response
            
        except Exception as e:
            logger.error(f"Lỗi xử lý tài liệu {document_id}: {str(e)}")
            
            # Cập nhật trạng thái lỗi
            response.status = ProcessingStatus.FAILED
            response.processing_time = time.time() - start_time
            response.updated_at = datetime.now()
            
            self.processed_documents[document_id] = response
            raise
    
    def get_document(self, document_id: str) -> Optional[DocumentProcessingResponse]:
        """Lấy thông tin tài liệu đã xử lý"""
        return self.processed_documents.get(document_id)
    
    def list_documents(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """Lấy danh sách tài liệu đã xử lý"""
        documents = list(self.processed_documents.values())
        
        # Sắp xếp theo thời gian tạo (mới nhất trước)
        documents.sort(key=lambda x: x.created_at, reverse=True)
        
        # Phân trang
        total = len(documents)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_documents = documents[start_idx:end_idx]
        
        return {
            "documents": page_documents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    def delete_document(self, document_id: str) -> bool:
        """Xóa tài liệu đã xử lý"""
        if document_id in self.processed_documents:
            del self.processed_documents[document_id]
            logger.info(f"Đã xóa tài liệu {document_id}")
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê xử lý"""
        documents = list(self.processed_documents.values())
        
        stats = {
            "total_documents": len(documents),
            "by_status": {},
            "by_document_type": {},
            "average_processing_time": 0.0,
            "total_pages_processed": 0,
            "average_confidence": 0.0
        }
        
        if not documents:
            return stats
        
        # Thống kê theo trạng thái
        for doc in documents:
            status = doc.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Thống kê theo loại tài liệu
            doc_type = doc.document_type.value
            stats["by_document_type"][doc_type] = stats["by_document_type"].get(doc_type, 0) + 1
            
            # Tính tổng
            stats["total_pages_processed"] += doc.total_pages
        
        # Tính trung bình
        completed_docs = [doc for doc in documents if doc.status == ProcessingStatus.COMPLETED]
        if completed_docs:
            stats["average_processing_time"] = sum(doc.processing_time for doc in completed_docs) / len(completed_docs)
            stats["average_confidence"] = sum(doc.ai_extraction.confidence_score for doc in completed_docs) / len(completed_docs)
        
        return stats
    
    def reprocess_document(self, document_id: str, request: DocumentProcessingRequest) -> Optional[DocumentProcessingResponse]:
        """Xử lý lại tài liệu với cấu hình mới"""
        # Lấy tài liệu cũ
        old_doc = self.processed_documents.get(document_id)
        if not old_doc:
            return None
        
        try:
            # Lấy lại văn bản từ OCR results
            combined_text = self.ocr_service.get_combined_text(old_doc.ocr_results)
            
            # Xử lý lại AI với cấu hình mới
            document_type = request.document_type or old_doc.document_type
            ai_extraction = self.ai_service.process_document(
                text=combined_text,
                document_type=document_type,
                custom_fields=request.custom_fields
            )
            
            # Cập nhật kết quả
            old_doc.ai_extraction = ai_extraction
            old_doc.document_type = document_type
            old_doc.updated_at = datetime.now()
            
            logger.info(f"Đã xử lý lại tài liệu {document_id}")
            return old_doc
            
        except Exception as e:
            logger.error(f"Lỗi xử lý lại tài liệu {document_id}: {str(e)}")
            return None
    
    def cleanup_old_documents(self, max_age_hours: int = 24) -> int:
        """Dọn dẹp các tài liệu cũ"""
        current_time = datetime.now()
        expired_docs = []
        
        for doc_id, doc in self.processed_documents.items():
            age_hours = (current_time - doc.created_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                expired_docs.append(doc_id)
        
        # Xóa các tài liệu hết hạn
        for doc_id in expired_docs:
            del self.processed_documents[doc_id]
        
        logger.info(f"Đã dọn dẹp {len(expired_docs)} tài liệu cũ")
        return len(expired_docs)
