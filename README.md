# 3. MÔ TẢ YÊU CẦU CHỨC NĂNG

## 3.1 Quản trị hệ thống

### 3.1.1 Quản lý người dùng
- Tạo, sửa, xoá tài khoản người dùng.
- Phân quyền theo nhóm:
  - Quản trị viên
  - Nhân viên nhập liệu
  - Nhân viên kiểm V1, V2, V3
  - Người kết xuất dữ liệu
- Đăng nhập bằng tài khoản, mật khẩu.
- Ghi nhận lịch sử đăng nhập, nhật ký thao tác của người dùng.

### 3.1.2 Cấu hình luồng nhập liệu
- Thiết lập các bước xử lý cho từng loại tài liệu:
  - Tích hợp dữ liệu (Upload PDF)
  - Nhận dạng dữ liệu (OCR + AI)
  - Nhập liệu thủ công (nếu cần)
  - Kiểm tra dữ liệu V1
  - Kiểm tra dữ liệu V2 (ngẫu nhiên theo tỷ lệ)
  - Kiểm tra dữ liệu V3 (ngẫu nhiên theo tỷ lệ)
- Cấu hình phân công nhân viên/nhóm nhân viên cho từng bước xử lý.

### 3.1.3 Cấu hình danh mục và trường dữ liệu
- Khai báo danh mục loại tài liệu:
  - Ví dụ: Thông tin Hồ sơ, Mục lục tài liệu, Thông tin Văn bản.
- Danh sách các trường dữ liệu tương ứng với từng loại tài liệu.
- Định dạng trường dữ liệu:
  - Text
  - Numeric
  - Date
  - Dropdown List
- Thiết lập bắt buộc nhập hay không.
- Thiết lập kiểm tra logic:
  - Kiểm tra trùng dữ liệu.
  - Kiểm tra định dạng (chỉ số, ngày/tháng/năm).
  - Kiểm tra quy luật (VD: Số hồ sơ không được trùng nhau).

### 3.1.4 Cấu hình nhận diện loại tài liệu từ tên file
- Khai báo quy tắc nhận diện loại tài liệu:
  - Tên file bắt đầu bằng “BIA” → Loại tài liệu: Thông tin Hồ sơ
  - Tên file bắt đầu bằng “MUCLUC” → Loại tài liệu: Mục lục tài liệu
  - Còn lại → Loại tài liệu: Thông tin Văn bản
- Sau nhận diện:
  - Áp dụng bộ trường nhập liệu tương ứng.
  - Cho phép người dùng chỉnh sửa lại loại tài liệu nếu sai.

---

## 3.2 Chức năng nhập liệu

### 3.2.1 Tích hợp dữ liệu (Upload PDF)
- Hỗ trợ upload:
  - File PDF đơn lẻ
  - Nhiều file PDF cùng lúc (multi-upload)
- Lưu thông tin:
  - Tên file gốc
  - Loại tài liệu nhận diện
  - Ngày giờ upload
  - Người upload
- Tự động nhận diện loại tài liệu.
- Hiển thị trạng thái upload thành công/thất bại.

### 3.2.2 Nhận dạng dữ liệu (OCR + AI)
- Áp dụng công nghệ OCR:
  - Đọc từ PDF scan hoặc PDF có text.
- Tích hợp AI:
  - Tự động gán thông tin vào các trường đã cấu hình.
  - Ghi nhận tỉ lệ chính xác (Confidence score) từng trường.
- Cho phép người dùng:
  - Điều chỉnh vùng OCR (drag & drop).
  - Sửa nội dung trường dữ liệu.
- Hiển thị song song:
  - PDF gốc
  - Bảng trường dữ liệu đã nhận dạng

### 3.2.3 Nhập liệu thủ công (tuỳ dự án)
- Giao diện:
  - Hiển thị PDF gốc (zoom, di chuyển, highlight)
- Tải trường tự động theo loại tài liệu.
- Kiểm tra dữ liệu đầu vào:
  - Bắt buộc nhập hoặc không
  - Kiểm tra định dạng
- Cho phép lưu tạm hoặc lưu hoàn thành.

### 3.2.4 Kiểm tra dữ liệu (V1, V2, V3)
- V1: kiểm 100%
- V2, V3: kiểm ngẫu nhiên theo tỷ lệ cấu hình
- Hệ thống tự động:
  - Phân bổ phiếu kiểm tra
  - Chọn ngẫu nhiên hồ sơ kiểm ở V2, V3
- Chức năng kiểm:
  - Hiển thị song song PDF gốc và dữ liệu
  - Cho phép sửa dữ liệu nếu sai
  - Ghi nhận:
    - Trạng thái kiểm (Đúng/Sai)
    - Nội dung chỉnh sửa (trước/sau)
- Thống kê kết quả kiểm:
  - Số lỗi
  - Loại lỗi theo trường
  - Thống kê lỗi theo nhân viên nhập hoặc kiểm

---

## 3.3 Kết xuất dữ liệu

- Hỗ trợ xuất định dạng:
  - Excel
  - PDF/A, TIFF
- Đảm bảo theo chuẩn:
  - Hướng dẫn số 40-HD/VPTW
  - Công văn 14748/VPTW-TCNS
- Chức năng:
  - Lựa chọn trường cần xuất
  - Kết xuất theo loại tài liệu
  - Ghi nhật ký kết xuất:
    - Thời gian
    - Người thực hiện
    - Số lượng hồ sơ đã xuất

---

## 3.4 Báo cáo thống kê

- **Thống kê tiến độ:**
  - Số tài liệu đã upload
  - Số tài liệu đã nhập liệu
  - Số tài liệu đã kiểm V1, V2, V3
  - Số tài liệu tồn đọng

- **Thống kê năng suất:**
  - Năng suất nhập liệu từng nhân viên
  - Năng suất kiểm dữ liệu

- **Thống kê tỷ lệ lỗi:**
  - Theo loại tài liệu
  - Theo trường dữ liệu
  - Theo nhân viên nhập / kiểm

- **Thống kê kết quả OCR:**
  - Tỷ lệ nhận dạng chính xác trung bình

- **Cho phép xuất báo cáo:**
  - Excel
  - PDF

---

# 4. YÊU CẦU PHI CHỨC NĂNG

## 4.1 Bảo mật
- Phân quyền chi tiết theo nhóm người dùng.
- Ghi nhật ký toàn bộ thao tác.
- Mã hoá dữ liệu nhạy cảm (nếu có).

## 4.2 Hiệu năng
- Đáp ứng xử lý hàng ngàn file PDF mà không bị chậm.

## 4.3 Giao diện
- Web-based
- Tương thích Chrome, Edge, Firefox
- Giao diện thân thiện, dễ sử dụng
