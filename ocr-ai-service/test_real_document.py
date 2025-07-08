#!/usr/bin/env python3
"""
Script test với file BIA.pdf thật từ thư mục docs
"""
import requests
import json
import os
from pathlib import Path

# Cấu hình
API_BASE_URL = "http://localhost:8000"
API_V1_URL = f"{API_BASE_URL}/api/v1"

def test_real_bia_document():
    """Test với file BIA.pdf thật"""
    print("📄 Test với file BIA.pdf thật")
    print("=" * 50)
    
    # Đường dẫn file
    file_path = Path("docs/BIA.pdf")
    
    if not file_path.exists():
        print(f"❌ File không tồn tại: {file_path}")
        return None
    
    print(f"✅ Tìm thấy file: {file_path}")
    print(f"📊 Kích thước file: {file_path.stat().st_size:,} bytes")
    
    try:
        # Đọc file
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Upload và xử lý
        files = {'file': (file_path.name, file_content, 'application/pdf')}
        data = {
            'document_type': 'THONG_TIN_HO_SO',
            'ocr_language': 'vie+eng'
        }
        
        print("\n🚀 Gửi request xử lý...")
        print("⏳ Đang xử lý... (có thể mất vài giây)")
        
        response = requests.post(f"{API_V1_URL}/documents/process", files=files, data=data, timeout=120)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ XỬ LÝ THÀNH CÔNG!")
            print("=" * 30)
            
            # Thông tin cơ bản
            print(f"🆔 Document ID: {result.get('document_id')}")
            print(f"📁 Filename: {result.get('filename')}")
            print(f"📋 Document Type: {result.get('document_type')}")
            print(f"📊 Status: {result.get('status')}")
            print(f"📄 Total Pages: {result.get('total_pages')}")
            print(f"⏱️  Processing Time: {result.get('processing_time'):.2f}s")
            
            # Kết quả OCR
            ocr_results = result.get('ocr_results', [])
            if ocr_results:
                print(f"\n🔍 KẾT QUẢ OCR:")
                print("-" * 20)
                for i, ocr in enumerate(ocr_results, 1):
                    print(f"📄 Trang {i}:")
                    print(f"   Confidence: {ocr.get('confidence_score', 0):.2f}")
                    print(f"   Text length: {len(ocr.get('text', ''))}")
                    
                    # Hiển thị 200 ký tự đầu
                    text_preview = ocr.get('text', '')[:200]
                    if text_preview:
                        print(f"   Preview: {text_preview}...")
                    print()
            
            # Kết quả AI Extraction
            ai_extraction = result.get('ai_extraction', {})
            if ai_extraction:
                print(f"🤖 KẾT QUẢ AI EXTRACTION:")
                print("-" * 25)
                print(f"Overall Confidence: {ai_extraction.get('confidence_score', 0):.2f}")
                print(f"Processing Time: {ai_extraction.get('processing_time', 0):.2f}s")
                
                fields = ai_extraction.get('fields', [])
                extracted_fields = [f for f in fields if f.get('value')]
                
                print(f"Extracted Fields: {len(extracted_fields)}/{len(fields)}")
                print()
                
                if extracted_fields:
                    print("📊 TRƯỜNG ĐÃ TRÍCH XUẤT:")
                    for field in extracted_fields:
                        name = field.get('name', 'N/A')
                        value = field.get('value', 'N/A')
                        confidence = field.get('confidence_score', 0)
                        required = "(*)" if field.get('is_required') else ""
                        
                        # Cắt ngắn value nếu quá dài
                        if len(value) > 60:
                            value = value[:60] + "..."
                        
                        print(f"   • {name}{required}: {value}")
                        print(f"     Confidence: {confidence:.2f}")
                        print()
                
                # Các trường chưa extract được
                missing_fields = [f for f in fields if not f.get('value')]
                if missing_fields:
                    print("⚠️  TRƯỜNG CHƯA TRÍCH XUẤT:")
                    for field in missing_fields:
                        name = field.get('name', 'N/A')
                        required = "(*)" if field.get('is_required') else ""
                        print(f"   • {name}{required}")
                    print()
            
            return result.get('document_id')
            
        else:
            print(f"\n❌ LỖI XỬ LÝ:")
            print(f"Status Code: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Chi tiết: {error_detail}")
            except:
                print(f"Raw response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("\n❌ TIMEOUT: Xử lý quá lâu (>120s)")
        return None
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        return None

def analyze_document_details(document_id):
    """Phân tích chi tiết tài liệu"""
    if not document_id:
        return
    
    print(f"\n🔍 PHÂN TÍCH CHI TIẾT DOCUMENT {document_id}")
    print("=" * 60)
    
    try:
        # Lấy OCR chi tiết
        print("📄 CHI TIẾT OCR:")
        response = requests.get(f"{API_V1_URL}/documents/{document_id}/ocr")
        if response.status_code == 200:
            ocr_data = response.json()
            ocr_results = ocr_data.get('ocr_results', [])
            
            for i, result in enumerate(ocr_results, 1):
                print(f"\n   Trang {i}:")
                print(f"   - Confidence: {result.get('confidence_score', 0):.2f}")
                print(f"   - Text length: {len(result.get('text', ''))}")
                
                # Hiển thị một số dòng đầu
                text = result.get('text', '')
                lines = text.split('\n')[:5]  # 5 dòng đầu
                for j, line in enumerate(lines, 1):
                    if line.strip():
                        print(f"   {j}: {line.strip()}")
                if len(lines) >= 5:
                    print("   ...")
        
        # Lấy fields chi tiết
        print(f"\n📊 CHI TIẾT FIELDS:")
        response = requests.get(f"{API_V1_URL}/documents/{document_id}/fields")
        if response.status_code == 200:
            fields_data = response.json()
            
            print(f"   Document Type: {fields_data.get('document_type')}")
            print(f"   Overall Confidence: {fields_data.get('confidence_score', 0):.2f}")
            
            fields = fields_data.get('fields', [])
            
            # Phân loại fields
            high_conf = [f for f in fields if f.get('confidence_score', 0) > 0.8]
            medium_conf = [f for f in fields if 0.5 <= f.get('confidence_score', 0) <= 0.8]
            low_conf = [f for f in fields if 0 < f.get('confidence_score', 0) < 0.5]
            no_value = [f for f in fields if not f.get('value')]
            
            if high_conf:
                print(f"\n   🟢 HIGH CONFIDENCE ({len(high_conf)} fields):")
                for field in high_conf:
                    print(f"      • {field['name']}: {field['value'][:50]}... ({field['confidence_score']:.2f})")
            
            if medium_conf:
                print(f"\n   🟡 MEDIUM CONFIDENCE ({len(medium_conf)} fields):")
                for field in medium_conf:
                    print(f"      • {field['name']}: {field['value'][:50]}... ({field['confidence_score']:.2f})")
            
            if low_conf:
                print(f"\n   🟠 LOW CONFIDENCE ({len(low_conf)} fields):")
                for field in low_conf:
                    print(f"      • {field['name']}: {field['value'][:50]}... ({field['confidence_score']:.2f})")
            
            if no_value:
                print(f"\n   🔴 NO VALUE ({len(no_value)} fields):")
                for field in no_value:
                    required = " (*)" if field.get('is_required') else ""
                    print(f"      • {field['name']}{required}")
        
    except Exception as e:
        print(f"❌ Lỗi phân tích: {e}")

def compare_with_expected():
    """So sánh với dữ liệu mong đợi"""
    print(f"\n📋 SO SÁNH VỚI DỮ LIỆU MONG ĐỢI")
    print("=" * 40)
    
    # Dữ liệu mong đợi cho file BIA (giả định)
    expected_fields = {
        "so_ho_so": "Số hồ sơ dự kiến",
        "tieu_de_ho_so": "Tiêu đề hồ sơ dự kiến", 
        "don_vi_lap_ho_so": "Đơn vị lập hồ sơ dự kiến",
        "thoi_han_bao_quan": "Thời hạn bảo quản dự kiến"
    }
    
    print("⚠️  Lưu ý: Cần cập nhật dữ liệu mong đợi dựa trên nội dung thật của file BIA.pdf")
    print("\nCác trường quan trọng cần trích xuất:")
    for field, desc in expected_fields.items():
        print(f"   • {field}: {desc}")

def main():
    """Chạy test với file BIA.pdf thật"""
    print("🚀 TEST VỚI FILE BIA.PDF THẬT")
    print("=" * 60)
    
    # Kiểm tra kết nối
    try:
        response = requests.get(API_BASE_URL, timeout=5)
        if response.status_code != 200:
            print("❌ Service không khả dụng")
            return
    except Exception as e:
        print(f"❌ Không thể kết nối tới service: {e}")
        print("💡 Hãy chắc chắn service đang chạy: python main.py")
        return
    
    print("✅ Service đã sẵn sàng")
    
    # Test file thật
    document_id = test_real_bia_document()
    
    # Phân tích chi tiết
    if document_id:
        analyze_document_details(document_id)
    
    # So sánh với mong đợi
    compare_with_expected()
    
    # Tổng kết
    print(f"\n🏁 TEST HOÀN TẤT!")
    print("=" * 30)
    
    if document_id:
        print("✅ Kết quả: THÀNH CÔNG")
        print(f"🔗 Chi tiết: GET /api/v1/documents/{document_id}")
        print(f"📊 OCR: GET /api/v1/documents/{document_id}/ocr")
        print(f"📋 Fields: GET /api/v1/documents/{document_id}/fields")
    else:
        print("❌ Kết quả: THẤT BẠI")
    
    print(f"\n💡 Gợi ý cải thiện:")
    print("• Kiểm tra file BIA.pdf có đúng định dạng không")
    print("• Cài đặt thêm OCR engines: EasyOCR, PaddleOCR")
    print("• Cài đặt NLP models: underthesea, sentence-transformers")
    print("• Cấu hình OpenAI API key cho fallback tốt hơn")
    print("• Điều chỉnh confidence thresholds trong settings")

if __name__ == "__main__":
    main()
