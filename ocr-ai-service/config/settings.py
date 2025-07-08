from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    """Cấu hình cho OCR-AI Service"""
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "OCR-AI Service"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Dịch vụ OCR và AI để nhận dạng và xử lý tài liệu PDF"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # OCR settings
    TESSERACT_CMD: Optional[str] = None  # Đường dẫn tới tesseract nếu cần
    OCR_LANG: str = "vie+eng"  # Ngôn ngữ OCR (Vietnamese + English)
    OCR_DPI: int = 300  # DPI cho OCR
    
    # AI settings
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-3.5-turbo"  # Model AI sử dụng
    AI_MAX_TOKENS: int = 2000
    AI_TEMPERATURE: float = 0.1
    
    # File settings
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "uploads"
    ALLOWED_EXTENSIONS: str = ".pdf"
    
    @property
    def allowed_extensions_set(self) -> set:
        """Chuyển đổi ALLOWED_EXTENSIONS từ string thành set"""
        if isinstance(self.ALLOWED_EXTENSIONS, str):
            return {ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")}
        return self.ALLOWED_EXTENSIONS
    
    # Confidence thresholds
    MIN_CONFIDENCE_SCORE: float = 0.7
    HIGH_CONFIDENCE_SCORE: float = 0.9
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Tạo instance settings
settings = Settings()
