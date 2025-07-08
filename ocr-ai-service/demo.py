#!/usr/bin/env python3
"""
Demo script để kiểm tra OCR-AI Service
"""
import requests
import json
import os
from pathlib import Path

# Cấu hình
API_BASE_URL = "http://localhost:8000"
API_V1_URL = f"{API_BASE_URL}/api/v1"

def test_health():
    """Kiểm tra sức khỏe service"""
    print("=== Kiểm tra sức khỏe service ===")
    try:
        response = requests.get(f"{API_V1_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Lỗi: {e}")
        return False

def test_config():
    """Kiểm tra cấu hình hệ thống"""
    print("\n=== Kiểm tra cấu hình hệ thống ===")
    try:
        response = requests.get(f"{API_V1_URL}/config")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Lỗi: {e}")
        return False

def create_sample_pdf():
    """Tạo file PDF mẫu để test"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    # Tạo file PDF mẫu
    filename = "sample_document.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Thêm nội dung
    c.drawString(100, 750, "HO SO SO: 12345/2025")
    c.drawString(100, 720, "TIEU DE HO SO: Ho so quan ly tai lieu")
    c.drawString(100, 690, "DON VI LAP HO SO: Phong Van thu")
    c.drawString(100, 660, "NGAY BAT DAU: 01/01/2025")
    c.drawString(100, 630, "NGAY KET THUC: 31/12/2025")
    c.drawString(100, 600, "TONG SO TRANG: 10")
    c.drawString(100, 570, "GHI CHU: Day la ho so mau")
    
    c.save()
    return filename

def test_document_processing():
    """Kiểm tra xử lý tài liệu"""
    print("\n=== Kiểm tra xử lý tài liệu ===")
    
    # Tạo file PDF mẫu
    try:
        pdf_file = create_sample_pdf()
        print(f"Đã tạo file PDF mẫu: {pdf_file}")
    except Exception as e:
        print(f"Không thể tạo file PDF mẫu: {e}")
        print("Sẽ bỏ qua test xử lý tài liệu")
        return False
    
    try:
        # Upload và xử lý tài liệu
        with open(pdf_file, 'rb') as f:
            files = {'file': (pdf_file, f, 'application/pdf')}
            data = {
                'document_type': 'THONG_TIN_HO_SO',
                'ocr_language': 'vie+eng'
            }
            
            response = requests.post(f"{API_V1_URL}/documents/process", files=files, data=data)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Document ID: {result.get('document_id')}")
                print(f"Filename: {result.get('filename')}")
                print(f"Document Type: {result.get('document_type')}")
                print(f"Status: {result.get('status')}")
                print(f"Total Pages: {result.get('total_pages')}")
                print(f"Processing Time: {result.get('processing_time'):.2f}s")
                
                if result.get('ai_extraction'):
                    print(f"AI Confidence: {result['ai_extraction'].get('confidence_score'):.2f}")
                    print(f"Extracted Fields: {len(result['ai_extraction'].get('fields', []))}")
                
                return result.get('document_id')
            else:
                print(f"Lỗi: {response.text}")
                return None
                
    except Exception as e:
        print(f"Lỗi: {e}")
        return None
    finally:
        # Xóa file PDF mẫu
        if os.path.exists(pdf_file):
            os.remove(pdf_file)

def test_document_list():
    """Kiểm tra danh sách tài liệu"""
    print("\n=== Kiểm tra danh sách tài liệu ===")
    try:
        response = requests.get(f"{API_V1_URL}/documents")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Total Documents: {result.get('total')}")
            print(f"Page: {result.get('page')}")
            print(f"Page Size: {result.get('page_size')}")
            return True
        else:
            print(f"Lỗi: {response.text}")
            return False
    except Exception as e:
        print(f"Lỗi: {e}")
        return False

def test_statistics():
    """Kiểm tra thống kê"""
    print("\n=== Kiểm tra thống kê ===")
    try:
        response = requests.get(f"{API_V1_URL}/statistics")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Total Documents: {result.get('total_documents')}")
            print(f"Average Processing Time: {result.get('average_processing_time'):.2f}s")
            print(f"Average Confidence: {result.get('average_confidence'):.2f}")
            return True
        else:
            print(f"Lỗi: {response.text}")
            return False
    except Exception as e:
        print(f"Lỗi: {e}")
        return False

def main():
    """Chạy tất cả các test"""
    print("🚀 Bắt đầu kiểm tra OCR-AI Service")
    print(f"API Base URL: {API_BASE_URL}")
    print("-" * 50)
    
    # Kiểm tra kết nối
    try:
        response = requests.get(API_BASE_URL, timeout=5)
        if response.status_code != 200:
            print("❌ Không thể kết nối tới service. Vui lòng kiểm tra service đã chạy chưa.")
            return
    except Exception as e:
        print(f"❌ Không thể kết nối tới service: {e}")
        print("Vui lòng chạy: python main.py")
        return
    
    # Chạy các test
    tests = [
        ("Health Check", test_health),
        ("Configuration", test_config),
        ("Document List", test_document_list),
        ("Statistics", test_statistics),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✅ {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ {test_name}: ERROR - {e}")
    
    # Test xử lý tài liệu (có thể cần thư viện bổ sung)
    print("\n=== Test xử lý tài liệu ===")
    try:
        import reportlab
        document_id = test_document_processing()
        if document_id:
            print(f"✅ Document Processing: PASS")
        else:
            print(f"❌ Document Processing: FAIL")
    except ImportError:
        print("⚠️  Bỏ qua test xử lý tài liệu (cần cài đặt: pip install reportlab)")
    
    # Tóm tắt
    print("\n" + "=" * 50)
    print("📊 TÓM TẮT KẾT QUẢ")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nKết quả: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Tất cả tests đã pass! Service hoạt động bình thường.")
    else:
        print("⚠️  Một số tests failed. Vui lòng kiểm tra lại.")

if __name__ == "__main__":
    main()
