# CoffeeShop – Website Động (Python & SQLite)

Dự án website bán cà phê và bánh ngọt trực tuyến được phát triển bằng ngôn ngữ **Python (Flask)** và cơ sở dữ liệu **SQLite**.

---

## 🌟 Tính Năng Nổi Bật

### 1. Dành Cho Khách Hàng (Người Dùng)
- **Đăng ký thành viên** (`/register`): Tạo tài khoản mới, kiểm tra hợp lệ và tính duy nhất của Username/Email, mật khẩu được mã hóa an toàn bằng `generate_password_hash`.
- **Đăng nhập & Đăng xuất** (`/login`, `/logout`): Đăng nhập linh hoạt bằng Tên đăng nhập hoặc Email. Có nút điền nhanh tài khoản mẫu để dùng thử ngay.
- **Quản lý thông tin cá nhân** (`/profile`): Xem thông tin tài khoản, thống kê số đơn hàng đã đặt, cập nhật thông tin liên hệ (Họ tên, SĐT, Địa chỉ nhận hàng mặc định) và đổi mật khẩu bảo mật.
- **Xem thông tin đơn hàng** (`/orders` & `/orders/<id>`):
  - Theo dõi danh sách đơn hàng theo bộ lọc trạng thái: *Tất cả, Chờ xác nhận, Đang pha chế, Đang giao hàng, Hoàn thành, Đã hủy*.
  - Huy hiệu màu sắc trực quan cho từng trạng thái.
  - Chi tiết đơn hàng với **Thanh tiến trình trực quan (Step Tracker 4 bước)**, bảng liệt kê chi tiết từng món kèm giá, ghi chú và thông tin người nhận.
  - Tính năng **Hủy đơn hàng** trực tiếp khi đơn đang ở trạng thái *Chờ xác nhận*.
- **Giỏ hàng & Đặt hàng trực tuyến** (`/cart`, `/checkout`):
  - Thêm món vào giỏ hàng ngay từ trang chủ hoặc qua popup chi tiết món.
  - Tăng/giảm số lượng món trong giỏ hàng.
  - Điền sẵn thông tin giao hàng từ tài khoản người dùng và xác nhận tạo đơn hàng trong cơ sở dữ liệu SQLite.

### 2. Thực Đơn & Giao Diện
- **Gợi ý hôm nay**: 6 món đặc sắc được đề xuất trên trang chủ.
- **Phân loại danh mục**: Cà phê, Freeze, Trà, Bánh ngọt với số lượng món hiển thị trực tiếp.
- **Tìm kiếm thời gian thực**: Tìm kiếm không dấu tiếng Việt thông minh.
- **Sắp xếp linh hoạt**: Theo giá tăng dần, giá giảm dần hoặc tên món.
- **Giao diện hiện đại**: Phối màu thương hiệu nâu cà phê espresso (`#4B2E2A`) và vàng caramel (`#D9A441`), tối ưu hiển thị trên mọi thiết bị máy tính và điện thoại.

---

## 🛠️ Cài Đặt & Chạy Ứng Dụng

### 1. Yêu cầu hệ thống
- Python 3.10 trở lên
- Git

### 2. Cài đặt các gói phụ thuộc
```bash
pip install -r requirements.txt
```

### 3. Khởi chạy ứng dụng
```bash
python app.py
```
Ứng dụng sẽ chạy tại địa chỉ: **`http://127.0.0.1:5000`**

### 4. Tài khoản dùng thử (Demo)
Hệ thống đã tạo sẵn tài khoản thành viên mẫu kèm các đơn hàng mẫu để kiểm thử ngay:
- **Tên đăng nhập / Email**: `khachhang` (hoặc `khachhang@coffeeshop.vn`)
- **Mật khẩu**: `123456`

---

## 🧪 Chạy Kiểm Thử Tự Động (Unit Tests)

Dự án đi kèm bộ kiểm thử tự động toàn diện kiểm tra tất cả các luồng hoạt động chính:
```bash
python test_app.py
```
Kết quả kiểm thử: `6/6 tests passed (100% OK)`.

---

## 📁 Cấu Trúc Dự Án

```
coffee-shop/
├── app.py                # Ứng dụng Flask chính và định tuyến (Routes)
├── database.py           # Quản lý kết nối SQLite và khởi tạo CSDL
├── coffeeshop.db         # Cơ sở dữ liệu SQLite
├── test_app.py           # Bộ kiểm thử tự động (Unit Tests)
├── requirements.txt      # Danh sách thư viện Python cần thiết
├── README.md             # Tài liệu giới thiệu dự án
├── .gitignore            # Cấu hình bỏ qua tệp trong Git
├── data/                 # Dữ liệu CSV gốc (category.csv, product.csv)
├── images/products/      # Hình ảnh các món ăn & thức uống
├── templates/            # Giao diện Jinja2 (HTML)
│   ├── base.html         # Khung giao diện chuẩn, header, footer, alert
│   ├── index.html        # Trang chủ, thực đơn, popup xem nhanh
│   ├── login.html        # Trang đăng nhập
│   ├── register.html     # Trang đăng ký thành viên
│   ├── profile.html      # Trang quản lý thông tin cá nhân & đổi mật khẩu
│   ├── orders.html       # Trang danh sách đơn hàng & bộ lọc trạng thái
│   ├── order_detail.html # Chi tiết đơn hàng & thanh tiến trình
│   └── cart.html         # Giỏ hàng & đặt hàng
├── static/               # Tệp tĩnh (CSS, JS)
│   ├── css/style.css     # Định dạng phong cách thiết kế
│   └── js/app.js         # Xử lý tương tác tìm kiếm, lọc món, modal, giỏ hàng
└── site/                 # Phiên bản web tĩnh ban đầu
```
