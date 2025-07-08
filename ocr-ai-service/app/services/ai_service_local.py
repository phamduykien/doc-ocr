import logging
import time
import json
import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import pickle
import os
from pathlib import Path

from app.models.schemas import DocumentField, AIExtractionResult, DocumentType, FieldType
from config.settings import settings

logger = logging.getLogger(__name__)

# Import ML libraries với fallback
try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers không khả dụng")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("SentenceTransformers không khả dụng")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("Scikit-learn không khả dụng")

try:
    import underthesea
    UNDERTHESEA_AVAILABLE = True
except ImportError:
    UNDERTHESEA_AVAILABLE = False
    logger.warning("Underthesea không khả dụng")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class VietnameseNLPProcessor:
    """Xử lý NLP tiếng Việt"""
    
    def __init__(self):
        self.initialized = False
        self.word_segmenter = None
        self.pos_tagger = None
        self.ner_model = None
        
    def initialize(self):
        """Khởi tạo các model NLP"""
        if self.initialized:
            return
            
        try:
            if UNDERTHESEA_AVAILABLE:
                logger.info("Khởi tạo Underthesea NLP processor")
                # Underthesea sẽ tự động download model khi cần
                self.initialized = True
                logger.info("Underthesea NLP processor đã sẵn sàng")
            else:
                logger.warning("Underthesea không khả dụng, sử dụng fallback")
                self.initialized = True
        except Exception as e:
            logger.error(f"Lỗi khởi tạo NLP processor: {e}")
            self.initialized = True  # Vẫn cho phép chạy với fallback
    
    def segment_words(self, text: str) -> List[str]:
        """Tách từ tiếng Việt"""
        if not self.initialized:
            self.initialize()
            
        try:
            if UNDERTHESEA_AVAILABLE:
                return underthesea.word_tokenize(text)
            else:
                # Fallback: tách bằng khoảng trắng
                return text.split()
        except Exception as e:
            logger.error(f"Lỗi tách từ: {e}")
            return text.split()
    
    def extract_named_entities(self, text: str) -> List[Dict]:
        """Trích xuất thực thể có tên"""
        if not self.initialized:
            self.initialize()
            
        try:
            if UNDERTHESEA_AVAILABLE:
                entities = underthesea.ner(text)
                return [{"text": entity[0], "label": entity[1]} for entity in entities if entity[1] != 'O']
            else:
                # Fallback: regex patterns
                return self._extract_entities_with_regex(text)
        except Exception as e:
            logger.error(f"Lỗi trích xuất thực thể: {e}")
            return self._extract_entities_with_regex(text)
    
    def _extract_entities_with_regex(self, text: str) -> List[Dict]:
        """Trích xuất thực thể bằng regex patterns"""
        entities = []
        
        # Patterns cho các loại thực thể
        patterns = {
            'DATE': r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}\b',
            'NUMBER': r'\b\d+[\w\-/]*\d*\b',
            'ORGANIZATION': r'\b(?:Phòng|Ban|Sở|Cục|Văn phòng|Công ty|Trường)\s+[\w\s]+\b',
            'PERSON': r'\b[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝ][a-zàáâãèéêìíòóôõùúý]+(?:\s+[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝ][a-zàáâãèéêìíòóôõùúý]+)*\b'
        }
        
        for label, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    "text": match.group(),
                    "label": label,
                    "start": match.start(),
                    "end": match.end()
                })
        
        return entities

class LocalAIExtractor:
    """AI Extractor sử dụng models local"""
    
    def __init__(self):
        self.nlp_processor = VietnameseNLPProcessor()
        self.sentence_model = None
        self.vectorizer = None
        self.field_patterns = self._load_field_patterns()
        self.semantic_model_ready = False
        
        # Khởi tạo models
        self._initialize_semantic_models()
    
    def _initialize_semantic_models(self):
        """Khởi tạo các model semantic"""
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.info("Đang tải SentenceTransformer model...")
                # Sử dụng model đa ngôn ngữ hỗ trợ tiếng Việt
                self.sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self.semantic_model_ready = True
                logger.info("SentenceTransformer model đã sẵn sàng")
            
            if SKLEARN_AVAILABLE:
                # Khởi tạo TF-IDF vectorizer cho tiếng Việt
                self.vectorizer = TfidfVectorizer(
                    max_features=5000,
                    ngram_range=(1, 3),
                    stop_words=None  # Sẽ tự define stop words cho tiếng Việt
                )
                logger.info("TF-IDF vectorizer đã sẵn sàng")
                
        except Exception as e:
            logger.error(f"Lỗi khởi tạo semantic models: {e}")
            self.semantic_model_ready = False
    
    def _load_field_patterns(self) -> Dict[str, Dict]:
        """Load patterns cho từng loại trường"""
        return {
            "so_ho_so": {
                "patterns": [
                    r"(?:số\s*hồ\s*sơ|hồ\s*sơ\s*số)[:\s]*(\d+[\w\-/]*\d*)",
                    r"(?:mã\s*số|số)[:\s]*(\d+[\w\-/]*\d*)",
                    r"(\d+/\d+(?:/\d+)?)"
                ],
                "keywords": ["số hồ sơ", "mã số", "số", "hồ sơ"],
                "field_type": FieldType.TEXT
            },
            "tieu_de_ho_so": {
                "patterns": [
                    r"(?:tiêu\s*đề|tên\s*hồ\s*sơ|chủ\s*đề)[:\s]*(.+?)(?:\n|$)",
                    r"(?:về|v\/v)[:\s]*(.+?)(?:\n|$)",
                    r"(?:nội\s*dung)[:\s]*(.+?)(?:\n|$)"
                ],
                "keywords": ["tiêu đề", "tên hồ sơ", "chủ đề", "nội dung", "về", "v/v"],
                "field_type": FieldType.TEXT
            },
            "don_vi_lap_ho_so": {
                "patterns": [
                    r"(?:đơn\s*vị\s*lập|cơ\s*quan\s*lập|phòng\s*ban)[:\s]*(.+?)(?:\n|$)",
                    r"((?:phòng|ban|sở|cục|văn\s*phòng|công\s*ty|trường)\s+[\w\s]+)",
                ],
                "keywords": ["đơn vị lập", "cơ quan lập", "phòng ban", "phòng", "ban", "sở"],
                "field_type": FieldType.TEXT
            },
            "thoi_han_bao_quan": {
                "patterns": [
                    r"(?:thời\s*hạn\s*bảo\s*quản|bảo\s*quản)[:\s]*(.+?)(?:\n|$)",
                    r"(?:vĩnh\s*viễn|dài\s*hạn|tạm\s*thời|\d+\s*năm)"
                ],
                "keywords": ["thời hạn bảo quản", "bảo quản", "vĩnh viễn", "dài hạn"],
                "field_type": FieldType.TEXT
            },
            "ngay_bat_dau": {
                "patterns": [
                    r"(?:ngày\s*bắt\s*đầu|từ\s*ngày|bắt\s*đầu)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})",
                    r"(?:từ)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})"
                ],
                "keywords": ["ngày bắt đầu", "từ ngày", "bắt đầu", "từ"],
                "field_type": FieldType.DATE
            },
            "ngay_ket_thuc": {
                "patterns": [
                    r"(?:ngày\s*kết\s*thúc|đến\s*ngày|kết\s*thúc)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})",
                    r"(?:đến)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})"
                ],
                "keywords": ["ngày kết thúc", "đến ngày", "kết thúc", "đến"],
                "field_type": FieldType.DATE
            },
            "tong_so_trang": {
                "patterns": [
                    r"(?:tổng\s*số\s*trang|số\s*trang|trang)[:\s]*(\d+)",
                    r"(\d+)\s*trang"
                ],
                "keywords": ["tổng số trang", "số trang", "trang"],
                "field_type": FieldType.NUMERIC
            },
            "ghi_chu": {
                "patterns": [
                    r"(?:ghi\s*chú|chú\s*thích|lưu\s*ý)[:\s]*(.+?)(?:\n|$)"
                ],
                "keywords": ["ghi chú", "chú thích", "lưu ý", "note"],
                "field_type": FieldType.TEXT
            },
            # Thêm patterns cho các loại tài liệu khác
            "so_van_ban": {
                "patterns": [
                    r"(?:số\s*văn\s*bản|văn\s*bản\s*số)[:\s]*(\d+[\w\-/]*\d*)",
                    r"(?:số)[:\s]*(\d+[\w\-/]*\d*)"
                ],
                "keywords": ["số văn bản", "văn bản số", "số"],
                "field_type": FieldType.TEXT
            },
            "ngay_ban_hanh": {
                "patterns": [
                    r"(?:ngày\s*ban\s*hành|ban\s*hành)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})",
                    r"(?:ngày)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})"
                ],
                "keywords": ["ngày ban hành", "ban hành", "ngày"],
                "field_type": FieldType.DATE
            },
            "don_vi_ban_hanh": {
                "patterns": [
                    r"(?:đơn\s*vị\s*ban\s*hành|cơ\s*quan\s*ban\s*hành)[:\s]*(.+?)(?:\n|$)",
                    r"((?:phòng|ban|sở|cục|văn\s*phòng|công\s*ty|trường)\s+[\w\s]+)"
                ],
                "keywords": ["đơn vị ban hành", "cơ quan ban hành"],
                "field_type": FieldType.TEXT
            },
            "nguoi_ky": {
                "patterns": [
                    r"(?:người\s*ký|ký\s*tên)[:\s]*(.+?)(?:\n|$)",
                    r"(?:ký)[:\s]*(.+?)(?:\n|$)"
                ],
                "keywords": ["người ký", "ký tên", "ký"],
                "field_type": FieldType.TEXT
            },
            "trich_yeu": {
                "patterns": [
                    r"(?:trích\s*yếu|tóm\s*tắt|nội\s*dung)[:\s]*(.+?)(?:\n|$)",
                    r"(?:về|v\/v)[:\s]*(.+?)(?:\n|$)"
                ],
                "keywords": ["trích yếu", "tóm tắt", "nội dung", "về", "v/v"],
                "field_type": FieldType.TEXT
            }
        }
    
    def extract_field_with_patterns(self, text: str, field_name: str, field_config: Dict) -> Tuple[str, float, str]:
        """Trích xuất trường bằng patterns"""
        patterns = field_config.get("patterns", [])
        keywords = field_config.get("keywords", [])
        
        # Thử patterns regex
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match.groups():
                    value = match.group(1).strip()
                    confidence = 0.9  # High confidence cho pattern match
                    return value, confidence, match.group(0)
                else:
                    value = match.group(0).strip()
                    confidence = 0.8
                    return value, confidence, match.group(0)
        
        # Thử semantic search nếu có keywords
        if keywords and self.semantic_model_ready:
            semantic_result = self._extract_with_semantic_search(text, keywords, field_config)
            if semantic_result[0]:
                return semantic_result
        
        return "", 0.0, ""
    
    def _extract_with_semantic_search(self, text: str, keywords: List[str], field_config: Dict) -> Tuple[str, float, str]:
        """Trích xuất bằng semantic search"""
        try:
            if not self.sentence_model:
                return "", 0.0, ""
            
            # Tách text thành các câu
            sentences = re.split(r'[.!?;\n]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return "", 0.0, ""
            
            # Encode keywords và sentences
            keyword_embeddings = self.sentence_model.encode(keywords)
            sentence_embeddings = self.sentence_model.encode(sentences)
            
            # Tìm câu có similarity cao nhất
            similarities = cosine_similarity(keyword_embeddings, sentence_embeddings)
            max_similarity = similarities.max()
            
            if max_similarity > 0.6:  # Threshold cho semantic similarity
                best_sentence_idx = similarities.argmax() // len(keywords)
                best_sentence = sentences[best_sentence_idx]
                
                # Trích xuất value từ câu tốt nhất
                value = self._extract_value_from_sentence(best_sentence, field_config)
                confidence = min(max_similarity, 0.8)  # Cap confidence
                
                return value, confidence, best_sentence
            
        except Exception as e:
            logger.error(f"Lỗi semantic search: {e}")
        
        return "", 0.0, ""
    
    def _extract_value_from_sentence(self, sentence: str, field_config: Dict) -> str:
        """Trích xuất giá trị từ câu"""
        field_type = field_config.get("field_type", FieldType.TEXT)
        
        # Xử lý theo loại trường
        if field_type == FieldType.DATE:
            date_match = re.search(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}', sentence)
            return date_match.group() if date_match else ""
        
        elif field_type == FieldType.NUMERIC:
            num_match = re.search(r'\d+', sentence)
            return num_match.group() if num_match else ""
        
        else:  # TEXT
            # Loại bỏ keywords và lấy phần còn lại
            keywords = field_config.get("keywords", [])
            cleaned_sentence = sentence
            
            for keyword in keywords:
                cleaned_sentence = re.sub(rf'\b{re.escape(keyword)}[:\s]*', '', cleaned_sentence, flags=re.IGNORECASE)
            
            return cleaned_sentence.strip()
    
    def extract_with_entities(self, text: str, field_name: str, field_config: Dict) -> Tuple[str, float, str]:
        """Trích xuất dựa trên named entities"""
        try:
            entities = self.nlp_processor.extract_named_entities(text)
            field_type = field_config.get("field_type", FieldType.TEXT)
            
            # Map field type với entity labels
            entity_type_mapping = {
                FieldType.DATE: ['DATE'],
                FieldType.NUMERIC: ['NUMBER'],
                FieldType.TEXT: ['PERSON', 'ORGANIZATION', 'LOCATION']
            }
            
            target_labels = entity_type_mapping.get(field_type, [])
            
            # Tìm entities phù hợp
            matching_entities = [
                entity for entity in entities 
                if entity['label'] in target_labels
            ]
            
            if matching_entities:
                # Chọn entity đầu tiên (có thể cải thiện logic này)
                best_entity = matching_entities[0]
                return best_entity['text'], 0.7, best_entity['text']
            
        except Exception as e:
            logger.error(f"Lỗi extract với entities: {e}")
        
        return "", 0.0, ""
    
    def process_document(self, text: str, document_type: DocumentType, custom_fields: Optional[List[str]] = None) -> AIExtractionResult:
        """Xử lý tài liệu với local AI models"""
        start_time = time.time()
        
        try:
            logger.info(f"Bắt đầu local AI extraction cho {document_type.value}")
            
            # Khởi tạo NLP processor nếu chưa
            if not self.nlp_processor.initialized:
                self.nlp_processor.initialize()
            
            # Định nghĩa fields theo document type
            field_configs = self._get_field_configs_for_document_type(document_type)
            
            extracted_fields = []
            
            for field_name, field_config in field_configs.items():
                # Thử multiple extraction methods
                methods = [
                    self.extract_field_with_patterns,
                    self.extract_with_entities,
                ]
                
                best_value = ""
                best_confidence = 0.0
                best_original = ""
                
                for method in methods:
                    try:
                        value, confidence, original = method(text, field_name, field_config)
                        if confidence > best_confidence:
                            best_value = value
                            best_confidence = confidence
                            best_original = original
                    except Exception as e:
                        logger.error(f"Lỗi method {method.__name__}: {e}")
                        continue
                
                # Tạo DocumentField
                field = DocumentField(
                    name=field_name,
                    value=best_value,
                    field_type=field_config["field_type"],
                    confidence_score=best_confidence,
                    is_required=field_config.get("required", False),
                    original_text=best_original
                )
                extracted_fields.append(field)
            
            # Tính overall confidence
            confidences = [f.confidence_score for f in extracted_fields if f.confidence_score > 0]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            processing_time = time.time() - start_time
            
            logger.info(f"Local AI extraction hoàn thành: {len(extracted_fields)} trường, confidence: {overall_confidence:.2f}, thời gian: {processing_time:.2f}s")
            
            return AIExtractionResult(
                fields=extracted_fields,
                confidence_score=overall_confidence,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Lỗi local AI extraction: {str(e)}")
            return AIExtractionResult(
                fields=[],
                confidence_score=0.0,
                processing_time=time.time() - start_time
            )
    
    def _get_field_configs_for_document_type(self, document_type: DocumentType) -> Dict:
        """Lấy cấu hình fields cho loại tài liệu"""
        field_mappings = {
            DocumentType.THONG_TIN_HO_SO: [
                "so_ho_so", "tieu_de_ho_so", "don_vi_lap_ho_so", 
                "thoi_han_bao_quan", "ngay_bat_dau", "ngay_ket_thuc", 
                "tong_so_trang", "ghi_chu"
            ],
            DocumentType.MUC_LUC_TAI_LIEU: [
                "so_thu_tu", "so_ky_hieu", "ngay_thang", 
                "trich_yeu_noi_dung", "so_trang", "ghi_chu"
            ],
            DocumentType.THONG_TIN_VAN_BAN: [
                "so_van_ban", "ngay_ban_hanh", "trich_yeu", 
                "don_vi_ban_hanh", "nguoi_ky", "loai_van_ban", 
                "so_trang", "ghi_chu"
            ]
        }
        
        field_names = field_mappings.get(document_type, [])
        return {
            name: {
                **self.field_patterns.get(name, {}),
                "required": name in ["so_ho_so", "tieu_de_ho_so", "so_van_ban", "trich_yeu"]
            }
            for name in field_names
            if name in self.field_patterns
        }

class AIServiceLocal:
    """AI Service sử dụng local models với OpenAI fallback"""
    
    def __init__(self):
        """Khởi tạo AI service local"""
        self.local_extractor = LocalAIExtractor()
        
        # OpenAI fallback
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.openai_available = True
        else:
            self.openai_available = False
    
    def process_document(self, text: str, document_type: DocumentType, custom_fields: Optional[List[str]] = None) -> AIExtractionResult:
        """Xử lý tài liệu với local AI và OpenAI fallback"""
        try:
            logger.info(f"Bắt đầu AI extraction cho loại tài liệu: {document_type.value}")
            
            # Thử local extraction trước
            local_result = self.local_extractor.process_document(text, document_type, custom_fields)
            
            # Nếu local result có confidence tốt, sử dụng luôn
            if local_result.confidence_score >= settings.MIN_CONFIDENCE_SCORE:
                logger.info(f"Sử dụng kết quả local AI (confidence: {local_result.confidence_score:.2f})")
                return local_result
            
            # Nếu local result không tốt và có OpenAI, thử OpenAI
            if self.openai_available and local_result.confidence_score < 0.6:
                logger.info("Local confidence thấp, thử OpenAI fallback")
                openai_result = self._extract_with_openai(text, document_type, custom_fields)
                
                # So sánh và chọn kết quả tốt hơn
                if openai_result.confidence_score > local_result.confidence_score:
                    logger.info(f"Sử dụng kết quả OpenAI (confidence: {openai_result.confidence_score:.2f})")
                    return openai_result
            
            logger.info(f"Sử dụng kết quả local AI (confidence: {local_result.confidence_score:.2f})")
            return local_result
            
        except Exception as e:
            logger.error(f"Lỗi AI extraction: {str(e)}")
            return AIExtractionResult(
                fields=[],
                confidence_score=0.0,
                processing_time=0.0
            )
    
    def _extract_with_openai(self, text: str, document_type: DocumentType, custom_fields: Optional[List[str]] = None) -> AIExtractionResult:
        """OpenAI extraction (fallback)"""
        try:
            # Import logic from original ai_service.py
            # ... (implement OpenAI extraction similar to original)
            # For now, return empty result
            return AIExtractionResult(
                fields=[],
                confidence_score=0.0,
                processing_time=0.0
            )
        except Exception as e:
            logger.error(f"Lỗi OpenAI extraction: {str(e)}")
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
