# Produce Desk

Website nội bộ giúp nhân viên cửa hàng nông sản quản lý khách hàng, ghi nhận và chỉnh sửa đơn hàng, cập nhật trạng thái xử lý và xem lịch giao hàng theo ngày. Giao diện sử dụng tiếng Anh.

**Chức năng chính:** đăng nhập bằng mã nhân viên và mật khẩu; quản lý khách hàng; tạo/sửa đơn với nhiều sản phẩm; tìm kiếm và lọc đơn theo trạng thái; xem lịch sử trạng thái và lịch giao hàng.

**Công nghệ:** React + Vite + CSS, FastAPI (Python), SQLite + SQLAlchemy. Dữ liệu được lưu thật trong database và vẫn còn khi tắt/mở lại ứng dụng.

## 1. Yêu cầu trước khi cài

- Python **3.11 trở lên**, có `pip` và `venv`.
- Node.js **22.12 trở lên**, kèm npm.
- Kết nối Internet để tải thư viện lần đầu.

Các lệnh dưới đây dành cho **macOS/Linux**. Tải hoặc clone mã nguồn về máy, rồi mở terminal tại thư mục gốc của dự án — nơi chứa `backend/` và `frontend/`.

Kiểm tra công cụ đã được cài:

```bash
python3 --version
node --version
npm --version
```

Không cần cài database server riêng: SQLite được sử dụng qua Python. Không cần tạo file `.env` cho cấu hình mặc định.

## 2. Cài đặt và chạy backend

Trong **terminal thứ nhất**, bắt đầu từ thư mục gốc dự án:

```bash
# Tạo và kích hoạt môi trường Python riêng
python3 -m venv .venv
source .venv/bin/activate

# Cài toàn bộ thư viện backend theo phiên bản đã kiểm thử
python -m pip install -r backend/requirements-lock.txt

# Tạo database, dữ liệu mẫu và tài khoản demo
cd backend
python -m app.seed

# Khởi động API
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Giữ terminal này chạy. Database được tạo tại `backend/data/produce.db`. Lần seed đầu tạo **5 khách hàng, 10 sản phẩm, 10 đơn hàng và 1 tài khoản nhân viên demo**. Chạy seed lại không nhân đôi dữ liệu hoặc đặt lại mật khẩu tài khoản đã có.

## 3. Cài đặt và chạy frontend

Mở **terminal thứ hai** tại thư mục gốc dự án:

```bash
cd frontend
npm ci
npm run dev
```

Giữ cả hai terminal chạy, sau đó mở **http://127.0.0.1:5173**.

| Thông tin đăng nhập demo | Giá trị |
| --- | --- |
| Mã nhân viên | `NV001` |
| Mật khẩu | `Produce@123` |

Đăng nhập → **New Order** để tạo đơn → **Orders** để xem/sửa và cập nhật trạng thái → **Deliveries** để xem lịch giao hàng. Dùng **Sign Out** để đăng xuất.

Tài liệu API: **http://127.0.0.1:8000/docs**. Frontend tự chuyển các yêu cầu `/api` tới backend ở cổng `8000`.

## 4. Chạy lại sau khi đã cài

Không cần cài thư viện hoặc seed lại mỗi lần. Mở hai terminal tại thư mục gốc:

**Terminal 1 — backend:**

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Nhấn `Ctrl+C` trong từng terminal để dừng. Dữ liệu đã lưu vẫn được giữ trong file SQLite.

## 5. Kiểm thử và build

Chạy từ thư mục gốc:

```bash
# Kiểm thử backend bằng database tạm, không thay đổi dữ liệu demo
cd backend
../.venv/bin/python -m pytest -q

# Build frontend
cd ../frontend
npm run build

# Xem bản build tại http://127.0.0.1:4173
npm run preview
```

Khi xem bản build, backend ở cổng `8000` vẫn phải chạy. Kết quả kiểm thử được ghi trong [VERIFICATION.md](VERIFICATION.md).

## Lưu ý

- Nếu hiện “Cannot reach the server”, kiểm tra backend đã chạy ở cổng `8000` chưa.
- Nếu cổng `5173` đang được sử dụng, kiểm tra ứng dụng đã chạy ở terminal khác trước khi mở thêm.
- Các ngày giao hàng mẫu được tính ở lần seed đầu; seed lại không chuyển chúng sang ngày hiện tại.
- Đây là bản demo local. Tài khoản trên chỉ dùng thử; chưa có giao diện tạo nhân viên, phân quyền hoặc khôi phục mật khẩu.
- Trạng thái đơn hiện cập nhật thủ công, tiến từng bước: **Received → Packed → Handed to Courier → In Transit → Delivered**. Quy trình này là giả định cần xác nhận với khách hàng.
- Chi tiết API, quy tắc nghiệp vụ, câu hỏi cho khách hàng và kịch bản demo: [Ghi chú dự án](docs/PROJECT_NOTES.md).
