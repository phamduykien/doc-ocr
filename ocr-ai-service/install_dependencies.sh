#!/bin/bash

echo "🚀 Cài đặt dependencies cho OCR-AI Service"
echo "==========================================="

# Kiểm tra Python version
echo "Kiểm tra Python version..."
python_version=$(python3 --version 2>&1)
echo "Python version: $python_version"

# Cài đặt system dependencies
echo "📦 Cài đặt system dependencies..."

if command -v apt-get &> /dev/null; then
    echo "Phát hiện Ubuntu/Debian system"
    sudo apt-get update
    
    # Tesseract và language packs
    echo "Cài đặt Tesseract OCR..."
    sudo apt-get install -y tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng
    
    # Poppler cho PDF processing
    echo "Cài đặt Poppler..."
    sudo apt-get install -y poppler-utils
    
    # OpenCV dependencies
    echo "Cài đặt OpenCV dependencies..."
    sudo apt-get install -y libopencv-dev python3-opencv
    
    # Other system libs
    sudo apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1
    
elif command -v yum &> /dev/null; then
    echo "Phát hiện CentOS/RHEL system"
    # CentOS/RHEL commands
    sudo yum update -y
    sudo yum install -y tesseract tesseract-langpack-vie tesseract-langpack-eng
    sudo yum install -y poppler-utils opencv-python3
    
elif command -v brew &> /dev/null; then
    echo "Phát hiện macOS system"
    # macOS commands
    brew install tesseract tesseract-lang
    brew install poppler opencv
    
else
    echo "⚠️  Không thể tự động cài đặt system dependencies"
    echo "Vui lòng cài đặt thủ công:"
    echo "- Tesseract OCR với Vietnamese language pack"
    echo "- Poppler utils"
    echo "- OpenCV"
fi

# Kiểm tra Tesseract
echo "🔍 Kiểm tra Tesseract..."
if command -v tesseract &> /dev/null; then
    tesseract_version=$(tesseract --version 2>&1 | head -n1)
    echo "✅ Tesseract: $tesseract_version"
    
    # Kiểm tra Vietnamese language pack
    if tesseract --list-langs | grep -q "vie"; then
        echo "✅ Vietnamese language pack đã cài đặt"
    else
        echo "⚠️  Vietnamese language pack chưa cài đặt"
    fi
else
    echo "❌ Tesseract chưa được cài đặt"
fi

# Upgrade pip
echo "📈 Upgrade pip..."
python3 -m pip install --upgrade pip

# Cài đặt Python dependencies theo thứ tự ưu tiên
echo "🐍 Cài đặt Python dependencies..."

# Core dependencies trước
echo "Cài đặt core dependencies..."
pip3 install fastapi uvicorn pydantic pydantic-settings python-multipart python-dotenv aiofiles requests

# OCR dependencies
echo "Cài đặt OCR dependencies..."
pip3 install pytesseract Pillow pdf2image PyPDF2 pdfplumber

# Computer vision
echo "Cài đặt OpenCV..."
pip3 install opencv-python

# ML dependencies (có thể mất thời gian)
echo "Cài đặt ML dependencies..."

# Cài đặt lightweight versions trước
pip3 install scikit-learn numpy pandas

# NLP cho tiếng Việt
echo "Cài đặt NLP libraries..."
pip3 install underthesea pyvi regex

# AI libraries (optional, large downloads)
echo "Cài đặt AI libraries (có thể mất thời gian)..."
echo "Nếu bạn không cần AI local, có thể bỏ qua bước này (Ctrl+C)"
read -p "Tiếp tục cài đặt Transformers và PyTorch? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # PyTorch CPU version (nhẹ hơn)
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    
    # Transformers và sentence transformers
    pip3 install transformers sentence-transformers
    
    echo "✅ AI libraries đã được cài đặt"
else
    echo "⏭️  Bỏ qua AI libraries. Service sẽ sử dụng rule-based extraction."
fi

# OCR engines nâng cao (optional)
echo "Cài đặt OCR engines nâng cao..."
read -p "Cài đặt EasyOCR và PaddleOCR? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip3 install easyocr paddlepaddle paddleocr
    echo "✅ OCR engines nâng cao đã được cài đặt"
else
    echo "⏭️  Bỏ qua OCR engines nâng cao. Sẽ sử dụng Tesseract."
fi

# OpenAI (optional)
read -p "Cài đặt OpenAI client? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip3 install openai
    echo "✅ OpenAI client đã được cài đặt"
    echo "💡 Nhớ cấu hình OPENAI_API_KEY trong file .env"
fi

echo ""
echo "🎉 Cài đặt hoàn tất!"
echo "==================="

# Kiểm tra cài đặt
echo "🔍 Kiểm tra cài đặt..."

python3 -c "
import sys
modules = [
    'fastapi', 'uvicorn', 'pydantic', 'pytesseract', 
    'PIL', 'pdf2image', 'cv2', 'numpy'
]
missing = []
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError:
        print(f'❌ {module}')
        missing.append(module)

print()
if missing:
    print(f'⚠️  Các modules sau chưa được cài đặt: {missing}')
else:
    print('🎉 Tất cả core modules đã được cài đặt!')
"

echo ""
echo "📋 Các bước tiếp theo:"
echo "1. Sao chép .env.example thành .env: cp .env.example .env"
echo "2. Cấu hình các biến trong file .env"
echo "3. Chạy service: python main.py"
echo "4. Truy cập http://localhost:8000/docs để xem API documentation"
echo ""
echo "🚀 Chúc bạn sử dụng thành công!"
