#!/usr/bin/env python3
"""
Script test cho chức năng OCR chữ viết tay tiếng Việt
"""
import requests
import json
import io
from PIL import Image, ImageDraw, ImageFont
import base64

# Cấu hình
API_BASE_URL = "http://localhost:8000"
API_V1_URL = f"{API_BASE_URL}/api/v1"

def create_handwriting_sample():
    """Tạo mẫu chữ viết tay giả lập"""
    # Tạo image với nền trắng
    width, height = 800, 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Thử tải font tiếng Việt (fallback về default nếu không có)
    try:
        # Tìm font hỗ trợ tiếng Việt
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        try:
            # Fallback font
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        except:
            font_large = None
            font_medium = None
    
    # Nội dung mẫu cho hồ sơ
    content_lines = [
        "HỒ SƠ SỐ: 2025/VKTL-001",
        "",
        "TIÊU ĐỀ HỒ SƠ:",
        "Hồ sơ tài liệu điện tử năm 2025",
        "",
        "ĐƠN VỊ LẬP HỒ SƠ:",
        "Phòng Văn thư - Lưu trữ",
        "",
        "THỜI HẠN BẢO QUẢN: Vĩnh viễn",
        "",
        "NGÀY BẮT ĐẦU: 01/01/2025",
        "NGÀY KẾT THÚC: 31/12/2025",
        "",
        "TỔNG SỐ TRANG: 150",
        "",
        "GHI CHÚ:",
        "Hồ sơ đã được số hóa và",
        "lưu trữ theo quy định hiện hành"
    ]
    
    y_pos = 50
    for line in content_lines:
        if line.strip():
            # Chọn font dựa trên nội dung
            current_font = font_large if line.isupper() or ":" in line else font_medium
            
            # Tạo hiệu ứng chữ viết tay bằng cách thêm noise nhẹ
            x_offset = 50 + (hash(line) % 10 - 5)  # Random offset nhỏ
            
            draw.text((x_offset, y_pos), line, fill='black', font=current_font)
            y_pos += 35 if current_font == font_large else 30
        else:
            y_pos += 20
    
    # Thêm một số đường kẻ để giả lập giấy có sẵn
    for i in range(5, height, 40):
        draw.line([(30, i), (width-30, i)], fill='lightgray', width=1)
    
    return image

def create_mixed_content_sample():
    """Tạo mẫu có cả chữ in và chữ viết tay"""
    width, height = 800, 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    try:
        font_printed = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
        font_handwritten = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        font_printed = ImageFont.load_default()
        font_handwritten = ImageFont.load_default()
    
    # Header in đẹp
    draw.text((50, 30), "CÔNG TY TNHH ABC", fill='black', font=font_printed)
    draw.text((50, 55), "PHIẾU ĐĂNG KÝ HỒ SƠ", fill='black', font=font_printed)
    
    # Các trường điền tay
    fields = [
        ("Số hồ sơ:", "2025/HS-456", 100),
        ("Tên hồ sơ:", "Báo cáo tài chính Q4/2024", 130),
        ("Người lập:", "Nguyễn Văn A", 160),
        ("Ngày lập:", "15/12/2024", 190),
        ("Ghi chú:", "Cần xem xét và phê duyệt", 220)
    ]
    
    for label, value, y_pos in fields:
        # Label in đẹp
        draw.text((50, y_pos), label, fill='black', font=font_printed)
        
        # Value viết tay
        x_offset = 180 + (hash(value) % 8 - 4)
        y_offset = y_pos + (hash(value) % 4 - 2)
        draw.text((x_offset, y_offset), value, fill='darkblue', font=font_handwritten)
    
    return image

def image_to_pdf_bytes(image):
    """Chuyển PIL Image thành PDF bytes"""
    pdf_buffer = io.BytesIO()
    image.save(pdf_buffer, format='PDF')
    return pdf_buffer.getvalue()

def test_handwriting_ocr():
    """Test OCR với chữ viết tay"""
    print("🖋️  Test OCR chữ viết tay tiếng Việt")
    print("=" * 50)
    
    # Tạo mẫu chữ viết tay
    print("Tạo mẫu chữ viết tay...")
    handwriting_image = create_handwriting_sample()
    
    # Chuyển thành PDF
    pdf_content = image_to_pdf_bytes(handwriting_image)
    
    try:
        # Upload và test
        files = {'file': ('BIA_handwritten_sample.pdf', pdf_content, 'application/pdf')}
        data = {
            'document_type': 'THONG_TIN_HO_SO',
            'ocr_language': 'vie+eng'
        }
        
        print("Gửi request xử lý...")
        response = requests.post(f"{API_V1_URL}/documents/process", files=files, data=data, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Xử lý thành công!")
            print(f"Document ID: {result.get('document_id')}")
            print(f"Processing Time: {result.get('processing_time'):.2f}s")
            
            # Hiển thị kết quả OCR
            ocr_results = result.get('ocr_results', [])
            if ocr_results:
                print(f"\n📄 Kết quả OCR (Confidence: {ocr_results[0].get('confidence_score', 0):.2f}):")
                print("-" * 30)
                print(ocr_results[0].get('text', 'Không có text'))
            
            # Hiển thị kết quả AI extraction
            ai_extraction = result.get('ai_extraction', {})
            if ai_extraction.get('fields'):
                print(f"\n🤖 Kết quả AI Extraction (Confidence: {ai_extraction.get('confidence_score', 0):.2f}):")
                print("-" * 40)
                for field in ai_extraction['fields']:
                    if field.get('value'):
                        print(f"• {field['name']}: {field['value']} (confidence: {field.get('confidence_score', 0):.2f})")
            
            return result.get('document_id')
        else:
            print(f"❌ Lỗi: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_mixed_content():
    """Test OCR với nội dung hỗn hợp"""
    print("\n📝 Test OCR nội dung hỗn hợp (in + viết tay)")
    print("=" * 50)
    
    # Tạo mẫu hỗn hợp
    print("Tạo mẫu nội dung hỗn hợp...")
    mixed_image = create_mixed_content_sample()
    
    # Chuyển thành PDF
    pdf_content = image_to_pdf_bytes(mixed_image)
    
    try:
        files = {'file': ('FORM_mixed_content.pdf', pdf_content, 'application/pdf')}
        data = {
            'document_type': 'THONG_TIN_VAN_BAN',
            'ocr_language': 'vie+eng'
        }
        
        print("Gửi request xử lý...")
        response = requests.post(f"{API_V1_URL}/documents/process", files=files, data=data, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Xử lý thành công!")
            
            # So sánh kết quả
            ocr_results = result.get('ocr_results', [])
            ai_extraction = result.get('ai_extraction', {})
            
            if ocr_results:
                print(f"\n📄 Raw OCR Output:")
                print("-" * 25)
                print(ocr_results[0].get('text', 'Không có text')[:500] + "...")
            
            if ai_extraction.get('fields'):
                print(f"\n🤖 Extracted Fields:")
                print("-" * 20)
                for field in ai_extraction['fields']:
                    if field.get('value'):
                        print(f"• {field['name']}: {field['value']}")
            
            return result.get('document_id')
        else:
            print(f"❌ Lỗi: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def compare_ocr_engines(document_id):
    """So sánh kết quả từ các OCR engines"""
    if not document_id:
        return
        
    print(f"\n🔍 Phân tích chi tiết OCR cho document {document_id}")
    print("=" * 50)
    
    try:
        # Lấy kết quả OCR chi tiết
        response = requests.get(f"{API_V1_URL}/documents/{document_id}/ocr")
        if response.status_code == 200:
            ocr_data = response.json()
            ocr_results = ocr_data.get('ocr_results', [])
            
            for i, result in enumerate(ocr_results, 1):
                print(f"\nTrang {i}:")
                print(f"Confidence: {result.get('confidence_score', 0):.2f}")
                print(f"Text length: {len(result.get('text', ''))}")
                print("Sample text:")
                text_sample = result.get('text', '')[:200]
                print(f"'{text_sample}...'")
        
        # Lấy kết quả fields
        response = requests.get(f"{API_V1_URL}/documents/{document_id}/fields")
        if response.status_code == 200:
            fields_data = response.json()
            print(f"\n📊 Field Extraction Summary:")
            print(f"Document Type: {fields_data.get('document_type')}")
            print(f"Overall Confidence: {fields_data.get('confidence_score', 0):.2f}")
            
            fields = fields_data.get('fields', [])
            extracted_count = sum(1 for f in fields if f.get('value'))
            print(f"Fields extracted: {extracted_count}/{len(fields)}")
            
            # Hiển thị fields với confidence cao
            high_confidence_fields = [f for f in fields if f.get('confidence_score', 0) > 0.7]
            if high_confidence_fields:
                print("\n🎯 High confidence fields:")
                for field in high_confidence_fields:
                    print(f"• {field['name']}: {field['value']} ({field.get('confidence_score', 0):.2f})")
            
            # Hiển thị fields cần cải thiện
            low_confidence_fields = [f for f in fields if 0 < f.get('confidence_score', 0) <= 0.7]
            if low_confidence_fields:
                print("\n⚠️  Fields cần cải thiện:")
                for field in low_confidence_fields:
                    value = field.get('value', 'N/A')
                    if len(value) > 50:
                        value = value[:50] + "..."
                    print(f"• {field['name']}: {value} ({field.get('confidence_score', 0):.2f})")
            
    except Exception as e:
        print(f"❌ Lỗi phân tích: {e}")

def test_performance():
    """Test performance với nhiều loại tài liệu"""
    print(f"\n⚡ Test Performance")
    print("=" * 30)
    
    # Test với các loại tài liệu khác nhau
    test_cases = [
        ("handwriting", "Chữ viết tay"),
        ("mixed", "Nội dung hỗn hợp")
    ]
    
    results = []
    
    for test_type, description in test_cases:
        print(f"\nTest {description}...")
        
        if test_type == "handwriting":
            doc_id = test_handwriting_ocr()
        else:
            doc_id = test_mixed_content()
        
        if doc_id:
            # Lấy thống kê
            response = requests.get(f"{API_V1_URL}/documents/{doc_id}")
            if response.status_code == 200:
                doc_data = response.json()
                results.append({
                    'type': description,
                    'processing_time': doc_data.get('processing_time', 0),
                    'confidence': doc_data.get('ai_extraction', {}).get('confidence_score', 0),
                    'pages': doc_data.get('total_pages', 0)
                })
    
    if results:
        print(f"\n📊 Performance Summary:")
        print("-" * 40)
        for result in results:
            print(f"{result['type']}:")
            print(f"  • Processing time: {result['processing_time']:.2f}s")
            print(f"  • Confidence: {result['confidence']:.2f}")
            print(f"  • Pages: {result['pages']}")

def main():
    """Chạy tất cả tests"""
    print("🚀 Test chức năng OCR chữ viết tay tiếng Việt")
    print("=" * 60)
    
    # Kiểm tra kết nối
    try:
        response = requests.get(API_BASE_URL, timeout=5)
        if response.status_code != 200:
            print("❌ Service không khả dụng")
            return
    except Exception as e:
        print(f"❌ Không thể kết nối: {e}")
        return
    
    print("✅ Service đã sẵn sàng\n")
    
    # Chạy tests
    doc_id1 = test_handwriting_ocr()
    doc_id2 = test_mixed_content()
    
    # Phân tích chi tiết
    if doc_id1:
        compare_ocr_engines(doc_id1)
    
    # Test performance
    print(f"\n" + "="*60)
    test_performance()
    
    # Tổng kết
    print(f"\n🏁 Test hoàn tất!")
    print("💡 Tips để cải thiện kết quả:")
    print("• Cài đặt thêm OCR engines: EasyOCR, PaddleOCR")
    print("• Cài đặt AI models: sentence-transformers")
    print("• Cấu hình OpenAI API key cho fallback")
    print("• Điều chỉnh confidence thresholds trong settings")

if __name__ == "__main__":
    main()
