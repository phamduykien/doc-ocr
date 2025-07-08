import logging
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from app.models.schemas import OCRResult, DocumentType
from config.settings import settings

logger = logging.getLogger(__name__)

class OCRServiceMock:
    """Mock OCR service để demo khi không có dependencies"""
    
    def __init__(self):
        """Khởi tạo Mock OCR service"""
        self.dpi = settings.OCR_DPI
        self.lang = settings.OCR_LANG
        
    def process_pdf_bytes(self, pdf_bytes: bytes) -> List[OCRResult]:
        """Mock xử lý PDF bytes và trả về kết quả OCR giả lập"""
        try:
            logger.info("Mock OCR: Đang xử lý PDF bytes")
            time.sleep(1)  # Giả lập thời gian xử lý
            
            # Tạo kết quả OCR giả lập
            mock_text = """
            HỒ SƠ SỐ: 12345/2025
            TIÊU ĐỀ HỒ SƠ: Hồ sơ quản lý tài liệu hành chính
            ĐƠN VỊ LẬP HỒ SƠ: Phòng Văn thư - Lưu trữ
            THỜI HẠN BẢO QUẢN: Vĩnh viễn
            NGÀY BẮT ĐẦU: 01/01/2025
            NGÀY KẾT THÚC: 31/12/2025
            TỔNG SỐ TRANG: 150
            GHI CHÚ: Hồ sơ đã được số hóa và lưu trữ
            """
            
            result = OCRResult(
                text=mock_text.strip(),
                confidence_score=0.92,
                page_number=1,
                bounding_box=None
            )
            
            logger.info("Mock OCR: Hoàn thành xử lý 1 trang")
            return [result]
            
        except Exception as e:
            logger.error(f"Mock OCR error: {str(e)}")
            return []
    
    def detect_document_type(self, filename: str) -> DocumentType:
        """Nhận diện loại tài liệu từ tên file"""
        filename_upper = filename.upper()
        
        if filename_upper.startswith("BIA"):
            return DocumentType.THONG_TIN_HO_SO
        elif filename_upper.startswith("MUCLUC"):
            return DocumentType.MUC_LUC_TAI_LIEU
        else:
            return DocumentType.THONG_TIN_VAN_BAN
    
    def get_combined_text(self, ocr_results: List[OCRResult]) -> str:
        """Kết hợp văn bản từ tất cả các trang"""
        return "\n\n".join([result.text for result in ocr_results if result.text])
    
    def get_average_confidence(self, ocr_results: List[OCRResult]) -> float:
        """Tính confidence score trung bình"""
        if not ocr_results:
            return 0.0
        
        total_confidence = sum([result.confidence_score for result in ocr_results])
        return total_confidence / len(ocr_results)
