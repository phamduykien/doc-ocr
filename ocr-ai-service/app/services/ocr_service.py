import pytesseract
from PIL import Image
import pdf2image
import io
import logging
from typing import List, Dict, Optional, Tuple
import time
import numpy as np
from pathlib import Path

from app.models.schemas import OCRResult, DocumentType
from config.settings import settings

logger = logging.getLogger(__name__)

class OCRService:
    """Dịch vụ OCR để nhận dạng ký tự từ PDF"""
    
    def __init__(self):
        """Khởi tạo OCR service"""
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        self.dpi = settings.OCR_DPI
        self.lang = settings.OCR_LANG
        
    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Chuyển đổi PDF thành danh sách hình ảnh"""
        try:
            logger.info(f"Chuyển đổi PDF sang hình ảnh: {pdf_path}")
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt='PNG'
            )
            logger.info(f"Chuyển đổi thành công {len(images)} trang")
            return images
        except Exception as e:
            logger.error(f"Lỗi chuyển đổi PDF: {str(e)}")
            raise
    
    def pdf_bytes_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """Chuyển đổi PDF bytes thành danh sách hình ảnh"""
        try:
            logger.info("Chuyển đổi PDF bytes sang hình ảnh")
            images = pdf2image.convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                fmt='PNG'
            )
            logger.info(f"Chuyển đổi thành công {len(images)} trang")
            return images
        except Exception as e:
            logger.error(f"Lỗi chuyển đổi PDF bytes: {str(e)}")
            raise
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Tiền xử lý hình ảnh để cải thiện OCR"""
        try:
            # Chuyển sang grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Tăng contrast
            image_array = np.array(image)
            
            # Áp dụng threshold để tăng độ tương phản
            threshold = 127
            image_array = np.where(image_array > threshold, 255, 0).astype(np.uint8)
            
            # Chuyển về PIL Image
            processed_image = Image.fromarray(image_array)
            
            return processed_image
        except Exception as e:
            logger.error(f"Lỗi tiền xử lý hình ảnh: {str(e)}")
            return image
    
    def extract_text_from_image(self, image: Image.Image, page_num: int = 1) -> OCRResult:
        """Trích xuất văn bản từ hình ảnh"""
        try:
            start_time = time.time()
            
            # Tiền xử lý hình ảnh
            processed_image = self.preprocess_image(image)
            
            # Cấu hình OCR
            config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỴỵỶỷỸỹ .,!?;:()[]{}"\'-/@#$%^&*+=<>|\\~`'
            
            # Nhận dạng văn bản
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.lang,
                config=config
            )
            
            # Lấy thông tin chi tiết với confidence score
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.lang,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Tính confidence score trung bình
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            logger.info(f"OCR trang {page_num}: {len(text)} ký tự, confidence: {avg_confidence:.2f}%, thời gian: {processing_time:.2f}s")
            
            return OCRResult(
                text=text.strip(),
                confidence_score=avg_confidence / 100.0,  # Chuyển về scale 0-1
                page_number=page_num,
                bounding_box=None  # Có thể mở rộng để lấy bounding box
            )
            
        except Exception as e:
            logger.error(f"Lỗi OCR trang {page_num}: {str(e)}")
            return OCRResult(
                text="",
                confidence_score=0.0,
                page_number=page_num,
                bounding_box=None
            )
    
    def process_pdf_file(self, pdf_path: str) -> List[OCRResult]:
        """Xử lý file PDF và trả về kết quả OCR cho tất cả các trang"""
        try:
            logger.info(f"Bắt đầu xử lý OCR file: {pdf_path}")
            
            # Chuyển PDF sang hình ảnh
            images = self.pdf_to_images(pdf_path)
            
            # Xử lý OCR cho từng trang
            results = []
            for i, image in enumerate(images, 1):
                result = self.extract_text_from_image(image, i)
                results.append(result)
            
            logger.info(f"Hoàn thành OCR {len(results)} trang")
            return results
            
        except Exception as e:
            logger.error(f"Lỗi xử lý PDF: {str(e)}")
            raise
    
    def process_pdf_bytes(self, pdf_bytes: bytes) -> List[OCRResult]:
        """Xử lý PDF bytes và trả về kết quả OCR cho tất cả các trang"""
        try:
            logger.info("Bắt đầu xử lý OCR PDF bytes")
            
            # Chuyển PDF bytes sang hình ảnh
            images = self.pdf_bytes_to_images(pdf_bytes)
            
            # Xử lý OCR cho từng trang
            results = []
            for i, image in enumerate(images, 1):
                result = self.extract_text_from_image(image, i)
                results.append(result)
            
            logger.info(f"Hoàn thành OCR {len(results)} trang")
            return results
            
        except Exception as e:
            logger.error(f"Lỗi xử lý PDF bytes: {str(e)}")
            raise
    
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
