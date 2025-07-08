import pytesseract
from PIL import Image
import pdf2image
import cv2
import numpy as np
import logging
import time
from typing import List, Dict, Optional, Tuple, Union
from pathlib import Path
import io

from app.models.schemas import OCRResult, DocumentType
from config.settings import settings

logger = logging.getLogger(__name__)

# Import OCR engines với fallback
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR không khả dụng")

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR không khả dụng")

class OCRServiceAdvanced:
    """OCR Service nâng cao hỗ trợ chữ viết tay tiếng Việt"""
    
    def __init__(self):
        """Khởi tạo OCR service với nhiều engines"""
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        
        self.dpi = settings.OCR_DPI
        self.lang = settings.OCR_LANG
        
        # Khởi tạo EasyOCR cho chữ viết tay
        if EASYOCR_AVAILABLE:
            try:
                self.easyocr_reader = easyocr.Reader(['vi', 'en'], gpu=False)
                logger.info("EasyOCR đã được khởi tạo cho tiếng Việt")
            except Exception as e:
                logger.error(f"Lỗi khởi tạo EasyOCR: {e}")
                self.easyocr_reader = None
        else:
            self.easyocr_reader = None
        
        # Khởi tạo PaddleOCR cho chữ viết tay
        if PADDLEOCR_AVAILABLE:
            try:
                self.paddleocr = PaddleOCR(
                    use_angle_cls=True, 
                    lang='vi'
                )
                logger.info("PaddleOCR đã được khởi tạo cho tiếng Việt")
            except Exception as e:
                logger.error(f"Lỗi khởi tạo PaddleOCR: {e}")
                self.paddleocr = None
        else:
            self.paddleocr = None
    
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
    
    def preprocess_image_for_handwriting(self, image: Union[Image.Image, np.ndarray]) -> np.ndarray:
        """Tiền xử lý hình ảnh cho chữ viết tay"""
        try:
            # Chuyển PIL Image sang OpenCV format
            if isinstance(image, Image.Image):
                image_array = np.array(image)
            else:
                image_array = image
            
            # Chuyển sang grayscale nếu cần
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            # Áp dụng Gaussian blur để giảm noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Adaptive thresholding tốt cho chữ viết tay
            adaptive_thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations để làm sạch
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_CLOSE, kernel)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Lỗi tiền xử lý hình ảnh: {str(e)}")
            # Fallback về image gốc
            if isinstance(image, Image.Image):
                return np.array(image.convert('L'))
            return image
    
    def preprocess_image_for_printed_text(self, image: Image.Image) -> Image.Image:
        """Tiền xử lý hình ảnh cho văn bản in"""
        try:
            # Chuyển sang grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            image_array = np.array(image)
            
            # Tăng contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image_array)
            
            # Threshold đơn giản cho văn bản in
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return Image.fromarray(binary)
            
        except Exception as e:
            logger.error(f"Lỗi tiền xử lý văn bản in: {str(e)}")
            return image
    
    def detect_handwriting_regions(self, image: Union[Image.Image, np.ndarray]) -> List[Dict]:
        """Phát hiện vùng chữ viết tay vs văn bản in"""
        try:
            if isinstance(image, Image.Image):
                image_array = np.array(image.convert('L'))
            else:
                image_array = image
            
            # Sử dụng edge detection để phân biệt chữ viết tay và in
            edges = cv2.Canny(image_array, 50, 150)
            
            # Tìm contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 20 and h > 10:  # Lọc các vùng quá nhỏ
                    # Phân tích đặc điểm để xác định loại text
                    roi = image_array[y:y+h, x:x+w]
                    
                    # Tính toán các đặc điểm
                    edge_density = np.sum(edges[y:y+h, x:x+w]) / (w * h)
                    aspect_ratio = w / h
                    
                    # Heuristic để phân loại
                    is_handwriting = edge_density > 0.1 and aspect_ratio < 10
                    
                    regions.append({
                        'bbox': (x, y, w, h),
                        'is_handwriting': is_handwriting,
                        'confidence': edge_density
                    })
            
            return regions
            
        except Exception as e:
            logger.error(f"Lỗi phát hiện vùng chữ viết tay: {str(e)}")
            return []
    
    def ocr_with_tesseract(self, image: Image.Image, page_num: int = 1, is_handwriting: bool = False) -> OCRResult:
        """OCR với Tesseract cho văn bản in và viết tay"""
        try:
            start_time = time.time()
            
            # Tiền xử lý dựa trên loại văn bản
            if is_handwriting:
                processed_image = Image.fromarray(self.preprocess_image_for_handwriting(image))
                # Cấu hình Tesseract cho chữ viết tay
                config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ .,!?/:;()-'
            else:
                processed_image = self.preprocess_image_for_printed_text(image)
                # Cấu hình Tesseract cho văn bản in
                config = r'--oem 3 --psm 6'
            
            # OCR
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.lang,
                config=config
            )
            
            # Lấy confidence score
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.lang,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            logger.info(f"Tesseract OCR trang {page_num}: {len(text)} ký tự, confidence: {avg_confidence:.2f}%")
            
            return OCRResult(
                text=text.strip(),
                confidence_score=avg_confidence / 100.0,
                page_number=page_num,
                bounding_box=None
            )
            
        except Exception as e:
            logger.error(f"Lỗi Tesseract OCR trang {page_num}: {str(e)}")
            return OCRResult(
                text="",
                confidence_score=0.0,
                page_number=page_num,
                bounding_box=None
            )
    
    def ocr_with_easyocr(self, image: Union[Image.Image, np.ndarray], page_num: int = 1) -> OCRResult:
        """OCR với EasyOCR cho chữ viết tay"""
        if not self.easyocr_reader:
            logger.warning("EasyOCR không khả dụng")
            return OCRResult(text="", confidence_score=0.0, page_number=page_num)
        
        try:
            start_time = time.time()
            
            # Tiền xử lý cho chữ viết tay
            if isinstance(image, Image.Image):
                processed_image = self.preprocess_image_for_handwriting(image)
            else:
                processed_image = self.preprocess_image_for_handwriting(image)
            
            # EasyOCR
            results = self.easyocr_reader.readtext(processed_image)
            
            # Kết hợp text và tính confidence
            text_parts = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                if confidence > 0.3:  # Lọc kết quả có confidence thấp
                    text_parts.append(text)
                    confidences.append(confidence)
            
            combined_text = " ".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            logger.info(f"EasyOCR trang {page_num}: {len(combined_text)} ký tự, confidence: {avg_confidence:.2f}")
            
            return OCRResult(
                text=combined_text.strip(),
                confidence_score=avg_confidence,
                page_number=page_num,
                bounding_box=None
            )
            
        except Exception as e:
            logger.error(f"Lỗi EasyOCR trang {page_num}: {str(e)}")
            return OCRResult(
                text="",
                confidence_score=0.0,
                page_number=page_num,
                bounding_box=None
            )
    
    def ocr_with_paddleocr(self, image: Union[Image.Image, np.ndarray], page_num: int = 1) -> OCRResult:
        """OCR với PaddleOCR cho chữ viết tay tiếng Việt"""
        if not self.paddleocr:
            logger.warning("PaddleOCR không khả dụng")
            return OCRResult(text="", confidence_score=0.0, page_number=page_num)
        
        try:
            start_time = time.time()
            
            # Tiền xử lý
            if isinstance(image, Image.Image):
                image_array = np.array(image)
            else:
                image_array = image
            
            # PaddleOCR
            results = self.paddleocr.ocr(image_array)
            
            # Xử lý kết quả
            text_parts = []
            confidences = []
            
            if results and results[0]:
                for line in results[0]:
                    if line and len(line) >= 2 and line[1]:
                        # Xử lý cấu trúc kết quả PaddleOCR
                        if isinstance(line[1], (list, tuple)) and len(line[1]) == 2:
                            text, confidence = line[1]
                        else:
                            # Fallback nếu cấu trúc khác
                            text = str(line[1])
                            confidence = 0.7  # Default confidence
                        
                        if confidence > 0.5:  # Lọc kết quả có confidence thấp
                            text_parts.append(text)
                            confidences.append(confidence)
            
            combined_text = " ".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            logger.info(f"PaddleOCR trang {page_num}: {len(combined_text)} ký tự, confidence: {avg_confidence:.2f}")
            
            return OCRResult(
                text=combined_text.strip(),
                confidence_score=avg_confidence,
                page_number=page_num,
                bounding_box=None
            )
            
        except Exception as e:
            logger.error(f"Lỗi PaddleOCR trang {page_num}: {str(e)}")
            return OCRResult(
                text="",
                confidence_score=0.0,
                page_number=page_num,
                bounding_box=None
            )
    
    def hybrid_ocr(self, image: Image.Image, page_num: int = 1) -> OCRResult:
        """OCR hybrid kết hợp nhiều engine"""
        try:
            logger.info(f"Bắt đầu hybrid OCR cho trang {page_num}")
            
            # Phát hiện vùng chữ viết tay
            regions = self.detect_handwriting_regions(image)
            
            # Chạy tất cả các engine
            tesseract_result = self.ocr_with_tesseract(image, page_num)
            easyocr_result = self.ocr_with_easyocr(image, page_num)
            paddleocr_result = self.ocr_with_paddleocr(image, page_num)
            
            # Chọn kết quả tốt nhất dựa trên confidence và length
            results = [
                ("Tesseract", tesseract_result),
                ("EasyOCR", easyocr_result),
                ("PaddleOCR", paddleocr_result)
            ]
            
            # Lọc kết quả có text
            valid_results = [(name, result) for name, result in results if result.text.strip()]
            
            if not valid_results:
                logger.warning(f"Không có kết quả OCR hợp lệ cho trang {page_num}")
                return OCRResult(text="", confidence_score=0.0, page_number=page_num)
            
            # Chọn kết quả tốt nhất (ưu tiên confidence cao và text dài)
            best_name, best_result = max(valid_results, 
                key=lambda x: x[1].confidence_score * 0.7 + (len(x[1].text) / 1000) * 0.3)
            
            logger.info(f"Chọn kết quả từ {best_name} cho trang {page_num}")
            
            # Nếu có nhiều kết quả tốt, kết hợp chúng
            if len(valid_results) > 1:
                high_confidence_results = [
                    result for name, result in valid_results 
                    if result.confidence_score > 0.7
                ]
                
                if len(high_confidence_results) > 1:
                    # Kết hợp text từ các kết quả tốt
                    combined_texts = []
                    total_confidence = 0
                    
                    for name, result in valid_results:
                        if result.confidence_score > 0.5:
                            combined_texts.append(result.text)
                            total_confidence += result.confidence_score
                    
                    if combined_texts:
                        # Loại bỏ duplicate và kết hợp
                        unique_sentences = list(set(combined_texts))
                        combined_text = " ".join(unique_sentences)
                        avg_confidence = total_confidence / len(valid_results)
                        
                        best_result = OCRResult(
                            text=combined_text,
                            confidence_score=avg_confidence,
                            page_number=page_num,
                            bounding_box=None
                        )
            
            return best_result
            
        except Exception as e:
            logger.error(f"Lỗi hybrid OCR trang {page_num}: {str(e)}")
            # Fallback về Tesseract
            return self.ocr_with_tesseract(image, page_num)
    
    def process_pdf_bytes(self, pdf_bytes: bytes) -> List[OCRResult]:
        """Xử lý PDF bytes với OCR nâng cao"""
        try:
            logger.info("Bắt đầu xử lý PDF bytes với OCR nâng cao")
            
            # Chuyển PDF sang hình ảnh
            images = self.pdf_bytes_to_images(pdf_bytes)
            
            # Xử lý OCR cho từng trang
            results = []
            for i, image in enumerate(images, 1):
                result = self.hybrid_ocr(image, i)
                results.append(result)
            
            logger.info(f"Hoàn thành OCR nâng cao {len(results)} trang")
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
