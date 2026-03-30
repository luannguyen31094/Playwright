# TÀI LIỆU KỸ THUẬT & QUY TRÌNH HỆ THỐNG: N8N TIKTOK AFFILIATE BRIDGE (V10.0 - 2026)
*Chủ sở hữu: Luan Ultra | Kiến trúc: DB-Driven, Multi-Account & Isolated Browser Context*

Hệ thống được thiết kế để giải quyết bài toán cốt lõi: **Scale (mở rộng) hàng trăm tài khoản TikTok Affiliate**, hoạt động song song, tự động phân luồng Category, tự tạo và bảo vệ Profile trình duyệt, điều khiển bằng quy trình N8N tự động hoá chuẩn xác.

---

## PHẦN I: TÀI LIỆU KỸ THUẬT (TECHNICAL ARCHITECTURE)

### 1. Mô Hình Tổng Quan
Hệ thống là một cầu nối (Bridge) giữa **N8N** (Trình điều khiển Workflow) và **Playwright** (Trình tự động hóa trình duyệt).
*   **API Gateway (`gateway.py`)**: Chạy thường trực ở Port `8000`. Cổng tiếp nhận HTTP Request từ N8N.
*   **Database (`PostgreSQL`)**: Đóng vai trò làm Source of Truth (Nguồn chân lý). Mọi cấu hình Account, Profile, Category đều được truy xuất từ đây thay vì Hardcode trên Code.
*   **Workers**: Các Process độc lập được Gateway gọi lên (`category_scraper_admin.py`, `web_affiliate_validator.py`). Chúng chạy trên nền (Background), độc lập lẫn nhau.

### 2. Kiến Trúc Dữ Liệu Các Bảng Chính (Database)
Hệ thống sử dụng cơ sở dữ liệu `Affiliate DB` tại PostgreSQL:

#### Bảng `tiktok_accounts` (Trái tim hệ thống)
Chứa toàn bộ thông tin về các tài khoản tham gia cào dữ liệu và quản lý hoa hồng. Các cột quan trọng:
*   `id` (PK): Định danh Account (Sử dụng làm `tiktok_account_id` trong hệ thống).
*   `chrome_profile_folder`: Tên thư mục chứa dữ liệu trình duyệt Chrome của riêng tài khoản này (Ví dụ: `Profile_Scraper_1_fashion`).
*   `category_id`: Mã Category đang được gán tự động cho tài khoản này lúc đi cào.
*   `status`: Trạng thái hoạt động (`active`, `banned`, etc).
*   **[NEW]** `tiktok_id`: Định danh dạng chữ của tài khoản TikTok (Ví dụ: `@shop_quanao`).
*   **[NEW]** `phone` / `email`: Thông tin liên lạc dùng để phục hồi / Verify OTP.
*   **[NEW]** `login_method`: Hình thức đăng nhập mặc định (`tiktokid`, `phone`, `email`). Có gài `CONSTRAINT` để chống sai số.

### 3. Cấu Trúc Khối Code Trọng Tâm
*   **`gateway.py`**:
    *   Nhận `POST` tại `/api/tiktok_scrape` và `/api/showcase_sync`.
    *   Bắt buộc nhận tham số `tiktok_account_id` từ Body JSON.
    *   Nhồi mã ID này vào biến môi trường hệ điều hành `os.environ["TIKTOK_ACCOUNT_ID"]`.
    *   Dùng `subprocess` / `threading` kích hoạt các Worker chạy nền, trả ngay HTTP 202 để N8N không bị đơ.
*   **`tiktok_db.py`**:
    *   `get_tiktok_account_by_id(account_id)`: Truy vấn cấu hình Account đầy đủ.
    *   `update_tiktok_account_category(account_id, category_id)`: Tự động khoá ID Category vào Account đang cào.
*   **`category_scraper_admin.py` (Cào Thô)**:
    *   Đọc Env `TIKTOK_ACCOUNT_ID`. Tra DB -> Lấy `chrome_profile_folder`.
    *   Dựng Playwright nối thẳng vào Profile đã chỉ định.
    *   Cào dữ liệu (BƯỚC 1).
    *   Tự động phát hiện Category và gán ngược bản ghi Category vào `tiktok_accounts` qua `tiktok_db.py`.
*   **`web_affiliate_validator.py` (Xử Lý Tinh)**:
    *   Xử lý BƯỚC 2 (Sync Showcase), BƯỚC 3 (Check Commission đa luồng), BƯỚC 5 (Add to Showcase từ AI).
    *   Tự động móc Profile đúng chuẩn theo `TIKTOK_ACCOUNT_ID`.
*   **`cleanup_profiles.py`**:
    *   Bảo vệ dữ liệu hệ thống: Quét DB lấy danh sách `chrome_profile_folder` đang Active và các Folder chứa chữ `Scraper` để tránh việc dọn rác nhầm làm mất Cookie Đăng nhập.

---

## PHẦN II: TÀI LIỆU QUY TRÌNH VẬN HÀNH (OPERATIONAL WORKFLOW)

### 1. Quy Trình Thêm Account Mới (Scale / Mở Rộng)
Kịch bản: Sếp muốn thêm 1 tài khoản TikTok mới chuyên đánh mảng "Đồ Công Nghệ".

**Bước 1: Khai báo Database**
*   Mở Database PostgreSQL, vào bảng `tiktok_accounts`.
*   Thêm dòng mới, điền các thông tin:
    *   `tiktok_id`: (Ví dụ: `@tech_review_vn`)
    *   `chrome_profile_folder`: Ghi theo chuẩn (Ví dụ: `Profile_Scraper_3_tech_review_vn`). Khuyến khích Format `Profile_Scraper_[ID]_[Tên]`.
    *   `login_method`: (Ví dụ: `tiktokid` hoặc `phone`).
    *   `status`: `active`.

**Bước 2: Cấy Cookie (Login mồi Trình duyệt)**
*   Chạy Tool hỗ trợ mở Trình duyệt (ví dụ File `open_browsers.py` Sếp sửa ruột nó thành mục tiêu là tên Folder mới).
*   Đăng nhập bằng tay tài khoản đó vào TikTok 1 lần duy nhất cho ngấm Cookie. Sau đó tắt đi.

**Bước 3: Chạy trên N8N**
*   Không cần đụng vào thư mục Code nữa.
*   Lên N8N, truyền mã `id` (số nguyên sinh ra từ Bước 1) vào Body của Node HTTP Request.

### 2. Quy Trình Gọi N8N Tiêu Chuẩn
Hệ thống thiết kế theo cơ chế Event-Driven từ N8N. Node Gọi API (HTTP Request Node) bắn Payload JSON xuống Gateway như sau:

#### A. Gọi Tiến Trình Cào Thô Danh Mục (Bước 1):
`POST http://localhost:8000/api/tiktok_scrape`
```json
{
  "tiktok_account_id": 3, 
  "category_url": "https://www.tiktok.com/shop/vn/c/do-cong-nghe...",
  "webhook_url": "https://n8n.domain.com/webhook/success_step1"
}
```
*Lưu ý: Sau khi gọi, hệ thống sẽ tự sinh ra `category_id` và Map nó thẳng vào Account 3 trong Database.*

#### B. Gọi Tiến Trình Xử Lý Tinh (Đồng bộ Showcase - Bước 2/3/5):
`POST http://localhost:8000/api/showcase_sync`
```json
{
  "tiktok_account_id": 3,
  "webhook_url": "https://n8n.domain.com/webhook/success_step2"
}
```

### 3. Quy Trình Back-up và Bảo mật (Tiêu Chuẩn V10)
**1. Sự Cố "Văng Cookie"**
*   **Cơ chế:** Vì Profile được cô lập hoàn toàn (`AdminScraperProfiles/Profile_Scraper_X`), nếu một tài khoản bị văng Cookie hoặc yêu cầu Captcha, Browser đó rớt lỗi, nhưng các dòng Browser (Account) khác đang chạy song song KHÔNG HIỆU ỨNG CHÉM.
*   **Xử lý:** Chạy tay file `open_browsers.py` (nhập tên folder), giải Captcha/Đăng nhập lại, hệ thống lại bào tiền bình thường.

**2. Sự Cố Rác Máy Cào**
*   **Cơ chế:** File `cleanup_profiles.py` chạy hằng ngày. Những folder Chrome sinh ra trong quá trình sinh Video, rác... sẽ bị xoá.
*   **Bảo vệ:** Những file nằm trong bảng `tiktok_accounts` (những con Gà đẻ trứng Vàng) được thêm vào Safe-List động + Safe-List tĩnh (Chứa cụm từ `Scraper`). Mãi mãi không bị xoá nhầm.

---
**TỔNG KẾT:** Kiến trúc V10 giải phóng Sếp khỏi việc đụng chạm vào Cấu hình Code. Tất cả quyền năng điều khiển `Account`, `Category`, `Multi-thread`... đều nằm trên giao diện của N8N và Database. Khối động cơ này có thể bào mòn mọi mặt trận từ mảng Thời trang đến Gia dụng chỉ với 1 cái Click Duplicate luồng trong N8N!
