try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

import json
import logging
import time
from typing import List, Dict, Optional, Any
import re
from datetime import datetime

from app.models.schemas import DocumentField, AIExtractionResult, DocumentType, FieldType
from config.settings import settings

logger = logging.getLogger(__name__)

class AIService:
    """Dịch vụ AI để trích xuất thông tin từ văn bản OCR"""
    
    def __init__(self):
        """Khởi tạo AI service"""
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
        
        # Định nghĩa các trường cho từng loại tài liệu
        self.document_fields = {
            DocumentType.THONG_TIN_HO_SO: [
                {"name": "so_ho_so", "type": FieldType.TEXT, "required": True},
                {"name": "tieu_de_ho_so", "type": FieldType.TEXT, "required": True},
                {"name": "don_vi_lap_ho_so", "type": FieldType.TEXT, "required": False},
                {"name": "thoi_han_bao_quan", "type": FieldType.TEXT, "required": False},
                {"name": "ngay_bat_dau", "type": FieldType.DATE, "required": False},
                {"name": "ngay_ket_thuc", "type": FieldType.DATE, "required": False},
                {"name": "tong_so_trang", "type": FieldType.NUMERIC, "required": False},
                {"name": "ghi_chu", "type": FieldType.TEXT, "required": False}
            ],
            DocumentType.MUC_LUC_TAI_LIEU: [
                {"name": "so_thu_tu", "type": FieldType.NUMERIC, "required": True},
                {"name": "so_ky_hieu", "type": FieldType.TEXT, "required": True},
                {"name": "ngay_thang", "type": FieldType.DATE, "required": False},
                {"name": "trich_yeu_noi_dung", "type": FieldType.TEXT, "required": True},
                {"name": "so_trang", "type": FieldType.NUMERIC, "required": False},
                {"name": "ghi_chu", "type": FieldType.TEXT, "required": False}
            ],
            DocumentType.THONG_TIN_VAN_BAN: [
                {"name": "so_van_ban", "type": FieldType.TEXT, "required": True},
                {"name": "ngay_ban_hanh", "type": FieldType.DATE, "required": False},
                {"name": "trich_yeu", "type": FieldType.TEXT, "required": True},
                {"name": "don_vi_ban_hanh", "type": FieldType.TEXT, "required": False},
                {"name": "nguoi_ky", "type": FieldType.TEXT, "required": False},
                {"name": "loai_van_ban", "type": FieldType.TEXT, "required": False},
                {"name": "so_trang", "type": FieldType.NUMERIC, "required": False},
                {"name": "ghi_chu", "type": FieldType.TEXT, "required": False}
            ]
        }
    
    def create_extraction_prompt(self, text: str, document_type: DocumentType, custom_fields: Optional[List[str]] = None) -> str:
        """Tạo prompt cho việc trích xuất thông tin"""
        
        # Lấy danh sách trường theo loại tài liệu
        fields = self.document_fields.get(document_type, [])
        
        # Tạo mô tả các trường
        field_descriptions = []
        for field in fields:
            field_desc = f"- {field['name']}: {field['type'].value}"
            if field['required']:
                field_desc += " (Bắt buộc)"
            field_descriptions.append(field_desc)
        
        prompt = f"""
Bạn là một chuyên gia trích xuất thông tin từ tài liệu hành chính Việt Nam.
Nhiệm vụ: Trích xuất thông tin từ văn bản OCR theo cấu trúc đã định.

Loại tài liệu: {document_type.value}

Các trường cần trích xuất:
{chr(10).join(field_descriptions)}

Văn bản OCR:
{text}

Hướng dẫn:
1. Trích xuất chính xác thông tin từ văn bản
2. Nếu không tìm thấy thông tin, để trống
3. Với trường DATE, sử dụng định dạng DD/MM/YYYY
4. Với trường NUMERIC, chỉ trả về số
5. Loại bỏ ký tự đặc biệt không cần thiết
6. Đánh giá độ tin cậy cho từng trường (0-1)

Trả về kết quả dưới dạng JSON:
{{
  "fields": [
    {{
      "name": "tên_trường",
      "value": "giá_trị",
      "confidence_score": 0.9,
      "original_text": "văn_bản_gốc_tương_ứng"
    }}
  ],
  "overall_confidence": 0.85
}}
"""
        return prompt
    
    def extract_with_openai(self, text: str, document_type: DocumentType, custom_fields: Optional[List[str]] = None) -> AIExtractionResult:
        """Trích xuất thông tin sử dụng OpenAI API"""
        try:
            start_time = time.time()
            
            if not OPENAI_AVAILABLE or not settings.OPENAI_API_KEY:
                logger.warning("OpenAI không khả dụng hoặc API key không được cấu hình, sử dụng rule-based extraction")
                return self.extract_with_rules(text, document_type, custom_fields)
            
            # Tạo prompt
            prompt = self.create_extraction_prompt(text, document_type, custom_fields)
            
            # Gọi OpenAI API
            response = openai.ChatCompletion.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia trích xuất thông tin từ tài liệu hành chính."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=settings.AI_MAX_TOKENS,
                temperature=settings.AI_TEMPERATURE
            )
            
            # Xử lý response
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                logger.error("Không thể parse JSON response từ OpenAI")
                return self.extract_with_rules(text, document_type, custom_fields)
            
            # Chuyển đổi thành DocumentField objects
            fields = []
            for field_data in result_data.get("fields", []):
                field_info = next((f for f in self.document_fields[document_type] if f["name"] == field_data["name"]), None)
                if field_info:
                    field = DocumentField(
                        name=field_data["name"],
                        value=field_data.get("value", ""),
                        field_type=field_info["type"],
                        confidence_score=field_data.get("confidence_score", 0.5),
                        is_required=field_info["required"],
                        original_text=field_data.get("original_text", "")
                    )
                    fields.append(field)
            
            processing_time = time.time() - start_time
            overall_confidence = result_data.get("overall_confidence", 0.5)
            
            logger.info(f"OpenAI extraction hoàn thành: {len(fields)} trường, confidence: {overall_confidence:.2f}, thời gian: {processing_time:.2f}s")
            
            return AIExtractionResult(
                fields=fields,
                confidence_score=overall_confidence,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Lỗi OpenAI extraction: {str(e)}")
            return self.extract_with_rules(text, document_type, custom_fields)
    
    def extract_with_rules(self, text: str, document_type: DocumentType, custom_fields: Optional[List[str]] = None) -> AIExtractionResult:
        """Trích xuất thông tin sử dụng rules-based (fallback)"""
        try:
            start_time = time.time()
            
            fields = []
            fields_config = self.document_fields.get(document_type, [])
            
            for field_config in fields_config:
                field_name = field_config["name"]
                field_type = field_config["type"]
                is_required = field_config["required"]
                
                # Áp dụng rules cho từng loại trường
                value, confidence, original = self.extract_field_with_rules(text, field_name, field_type)
                
                field = DocumentField(
                    name=field_name,
                    value=value,
                    field_type=field_type,
                    confidence_score=confidence,
                    is_required=is_required,
                    original_text=original
                )
                fields.append(field)
            
            processing_time = time.time() - start_time
            
            # Tính confidence tổng thể
            confidences = [f.confidence_score for f in fields if f.confidence_score > 0]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            logger.info(f"Rule-based extraction hoàn thành: {len(fields)} trường, confidence: {overall_confidence:.2f}, thời gian: {processing_time:.2f}s")
            
            return AIExtractionResult(
                fields=fields,
                confidence_score=overall_confidence,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Lỗi rule-based extraction: {str(e)}")
            return AIExtractionResult(
                fields=[],
                confidence_score=0.0,
                processing_time=0.0
            )
    
    def extract_field_with_rules(self, text: str, field_name: str, field_type: FieldType) -> tuple[str, float, str]:
        """Trích xuất một trường cụ thể bằng rules"""
        
        # Patterns cho các loại trường khác nhau
        patterns = {
            "so_ho_so": [r"Số.*?(\d+[\w\-/]*\d*)", r"Hồ sơ số.*?(\d+[\w\-/]*\d*)"],
            "tieu_de_ho_so": [r"Tiêu đề.*?:\s*(.+)", r"Nội dung.*?:\s*(.+)"],
            "ngay_ban_hanh": [r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", r"Ngày.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})"],
            "so_van_ban": [r"Số.*?(\d+[\w\-/]*\d*)", r"Văn bản số.*?(\d+[\w\-/]*\d*)"],
            "don_vi_ban_hanh": [r"Ban hành.*?:\s*(.+)", r"Đơn vị.*?:\s*(.+)"],
            "nguoi_ky": [r"Người ký.*?:\s*(.+)", r"Ký.*?:\s*(.+)"],
            "so_trang": [r"(\d+)\s*trang", r"Trang.*?(\d+)"],
            "trich_yeu": [r"Trích yếu.*?:\s*(.+)", r"Nội dung.*?:\s*(.+)"]
        }
        
        # Lấy patterns cho trường
        field_patterns = patterns.get(field_name, [])
        
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                confidence = 0.8 if len(value) > 0 else 0.0
                return value, confidence, match.group(0)
        
        # Nếu không tìm thấy pattern cụ thể, thử tìm kiếm chung
        if field_type == FieldType.DATE:
            date_match = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", text)
            if date_match:
                return date_match.group(1), 0.6, date_match.group(0)
        
        elif field_type == FieldType.NUMERIC:
            num_match = re.search(r"(\d+)", text)
            if num_match:
                return num_match.group(1), 0.4, num_match.group(0)
        
        return "", 0.0, ""
    
    def process_document(self, text: str, document_type: DocumentType, custom_fields: Optional[List[str]] = None) -> AIExtractionResult:
        """Xử lý tài liệu và trích xuất thông tin"""
        try:
            logger.info(f"Bắt đầu AI extraction cho loại tài liệu: {document_type.value}")
            
            # Sử dụng OpenAI nếu có API key và thư viện, ngược lại dùng rules
            if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
                return self.extract_with_openai(text, document_type, custom_fields)
            else:
                return self.extract_with_rules(text, document_type, custom_fields)
                
        except Exception as e:
            logger.error(f"Lỗi AI extraction: {str(e)}")
            return AIExtractionResult(
                fields=[],
                confidence_score=0.0,
                processing_time=0.0
            )
    
    def validate_extracted_data(self, fields: List[DocumentField]) -> Dict[str, Any]:
        """Validate dữ liệu đã trích xuất"""
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        for field in fields:
            # Kiểm tra trường bắt buộc
            if field.is_required and (not field.value or field.value.strip() == ""):
                validation_results["is_valid"] = False
                validation_results["errors"].append(f"Trường {field.name} là bắt buộc nhưng bị thiếu")
            
            # Kiểm tra định dạng ngày
            if field.field_type == FieldType.DATE and field.value:
                if not re.match(r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}", field.value):
                    validation_results["warnings"].append(f"Định dạng ngày không đúng cho trường {field.name}: {field.value}")
            
            # Kiểm tra số
            if field.field_type == FieldType.NUMERIC and field.value:
                try:
                    float(field.value)
                except ValueError:
                    validation_results["warnings"].append(f"Giá trị không phải là số cho trường {field.name}: {field.value}")
            
            # Kiểm tra confidence thấp
            if field.confidence_score < settings.MIN_CONFIDENCE_SCORE:
                validation_results["warnings"].append(f"Confidence thấp cho trường {field.name}: {field.confidence_score:.2f}")
        
        return validation_results
