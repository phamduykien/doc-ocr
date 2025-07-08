#!/usr/bin/env python3
"""
Script test API đơn giản cho OCR-AI Service
"""
import requests
import json

# Cấu hình
API_BASE_URL = "http://localhost:8000"
API_V1_URL = f"{API_BASE_URL}/api/v1"

def test_document_processing():
    """Test xử lý tài liệu bằng file PDF giả lập"""
    print("=== Test xử lý tài liệu ===")
    
    # Tạo nội dung PDF giả lập (binary data)
    fake_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    
    try:
        # Upload và xử lý tài liệu
        files = {'file': ('BIA_test_document.pdf', fake_pdf_content, 'application/pdf')}
        data = {
            'document_type': 'THONG_TIN_HO_SO',
            'ocr_language': 'vie+eng'
        }
        
        response = requests.post(f"{API_V1_URL}/documents/process", files=files, data=data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Document Processing: SUCCESS")
            print(f"Document ID: {result.get('document_id')}")
            print(f"Filename: {result.get('filename')}")
            print(f"Document Type: {result.get('document_type')}")
            print(f"Status: {result.get('status')}")
            print(f"Total Pages: {result.get('total_pages')}")
            print(f"Processing Time: {result.get('processing_time'):.2f}s")
            
            if result.get('ai_extraction'):
                ai_result = result['ai_extraction']
                print(f"AI Confidence: {ai_result.get('confidence_score'):.2f}")
                print(f"Extracted Fields: {len(ai_result.get('fields', []))}")
                
                # Hiển thị một vài trường đầu tiên
                fields = ai_result.get('fields', [])
                if fields:
                    print("Sample extracted fields:")
                    for field in fields[:3]:
                        print(f"  - {field['name']}: {field['value']} (confidence: {field['confidence_score']:.2f})")
            
            return result.get('document_id')
        else:
            print(f"❌ Document Processing: FAILED")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Document Processing: ERROR - {e}")
        return None

def test_get_document(document_id):
    """Test lấy thông tin tài liệu"""
    if not document_id:
        return False
        
    print(f"\n=== Test lấy thông tin tài liệu {document_id} ===")
    
    try:
        response = requests.get(f"{API_V1_URL}/documents/{document_id}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Get Document: SUCCESS")
            print(f"Document Type: {result.get('document_type')}")
            print(f"Created At: {result.get('created_at')}")
            return True
        else:
            print(f"❌ Get Document: FAILED - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Get Document: ERROR - {e}")
        return False

def test_document_fields(document_id):
    """Test lấy trường dữ liệu"""
    if not document_id:
        return False
        
    print(f"\n=== Test lấy trường dữ liệu {document_id} ===")
    
    try:
        response = requests.get(f"{API_V1_URL}/documents/{document_id}/fields")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Get Fields: SUCCESS")
            print(f"Document Type: {result.get('document_type')}")
            print(f"Confidence Score: {result.get('confidence_score'):.2f}")
            print(f"Number of Fields: {len(result.get('fields', []))}")
            return True
        else:
            print(f"❌ Get Fields: FAILED - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Get Fields: ERROR - {e}")
        return False

def test_statistics_after_processing():
    """Test thống kê sau khi xử lý tài liệu"""
    print(f"\n=== Test thống kê sau xử lý ===")
    
    try:
        response = requests.get(f"{API_V1_URL}/statistics")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Statistics: SUCCESS")
            print(f"Total Documents: {result.get('total_documents')}")
            print(f"Average Processing Time: {result.get('average_processing_time'):.2f}s")
            print(f"Average Confidence: {result.get('average_confidence'):.2f}")
            
            # Hiển thị thống kê theo status
            by_status = result.get('by_status', {})
            if by_status:
                print("Status breakdown:")
                for status, count in by_status.items():
                    print(f"  - {status}: {count}")
            
            return True
        else:
            print(f"❌ Statistics: FAILED - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Statistics: ERROR - {e}")
        return False

def main():
    """Chạy test API với xử lý tài liệu"""
    print("🚀 Test API với xử lý tài liệu giả lập")
    print(f"API Base URL: {API_BASE_URL}")
    print("-" * 50)
    
    # Kiểm tra kết nối
    try:
        response = requests.get(API_BASE_URL, timeout=5)
        if response.status_code != 200:
            print("❌ Không thể kết nối tới service.")
            return
    except Exception as e:
        print(f"❌ Không thể kết nối tới service: {e}")
        return
    
    # Test xử lý tài liệu
    document_id = test_document_processing()
    
    if document_id:
        # Test các API khác với document đã tạo
        test_get_document(document_id)
        test_document_fields(document_id)
        test_statistics_after_processing()
        
        print("\n" + "=" * 50)
        print("🎉 Tất cả tests hoàn thành!")
        print(f"📄 Swagger UI: {API_BASE_URL}/docs")
        print(f"📚 ReDoc: {API_BASE_URL}/redoc")
    else:
        print("\n❌ Không thể xử lý tài liệu, bỏ qua các test khác.")

if __name__ == "__main__":
    main()
