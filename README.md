# Sequence Diagram: Chức năng Đăng ký (Có xác thực Email)

Dưới đây là sơ đồ Sequence chi tiết cho chức năng Đăng ký tài khoản có bổ sung **Luồng Xác thực Email (Email Verification)**. Tất cả các bước được vẽ nối tiếp nghiêm ngặt (Synchronous Request - Response) để đảm bảo tính liên tục của luồng thực thi.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant MobileApp as Register Screen
    participant VerifyScreen as Verify OTP Screen
    participant AuthCtrl as Auth Controller
    participant AuthSvc as Auth Service
    participant MailSvc as Mailer Service
    participant DBUser as Table: users
    participant DBProfile as Table: patient_profiles

    %% 1. QUÁ TRÌNH ĐĂNG KÝ CƠ BẢN
    User->>MobileApp: Mở màn hình Đăng ký
    User->>MobileApp: Điền thông tin (Tên, Email, SĐT, Mật khẩu)
    User->>MobileApp: Nhấn nút "Đăng ký"
    
    MobileApp->>MobileApp: Form Validation (Kiểm tra dữ liệu)
    
    %% Gọi API Đăng ký
    MobileApp->>AuthCtrl: POST /auth/register (payload)
    AuthCtrl->>AuthSvc: Gọi logic xử lý: register(dto)
    
    %% Xử lý nghiệp vụ Backend
    AuthSvc->>DBUser: SELECT findFirst (Kiểm tra trùng lặp Email hoặc SĐT)
    DBUser-->>AuthSvc: Trả về kết quả (Null = Hợp lệ)
    
    AuthSvc->>AuthSvc: Băm mật khẩu (bcrypt) & Tạo Mã xác thực (OTP)
    
    %% Database Transaction
    Note over AuthSvc,DBProfile: Bắt đầu Transaction tạo tài khoản
    AuthSvc->>DBUser: INSERT bản ghi User (isEmailVerified: false, emailVerificationToken: OTP)
    DBUser-->>AuthSvc: Trả về ID của User vừa tạo
    
    AuthSvc->>DBProfile: INSERT bản ghi PatientProfile (is_primary: 1)
    DBProfile-->>AuthSvc: Trả về kết quả tạo Profile
    Note over AuthSvc,DBProfile: Kết thúc Transaction (Commit)
    
    %% Gửi Email
    AuthSvc->>MailSvc: sendVerificationEmail(email, OTP)
    MailSvc-->>AuthSvc: Xác nhận đã đẩy email vào hàng đợi
    MailSvc-)User: (Bất đồng bộ) Gửi Email thực tế đến hòm thư người dùng
    
    %% Phản hồi Đăng ký thành công (nhưng chưa verify)
    AuthSvc-->>AuthCtrl: Trả kết quả (Thành công, yêu cầu xác thực)
    AuthCtrl-->>MobileApp: HTTP 201 Created Response
    
    %% 2. QUÁ TRÌNH XÁC THỰC EMAIL (VERIFY)
    MobileApp->>VerifyScreen: Điều hướng tự động sang màn hình Nhập OTP
    VerifyScreen-->>User: Hiển thị form nhập OTP
    
    User->>VerifyScreen: Mở Email, đọc mã OTP và điền vào form
    User->>VerifyScreen: Nhấn nút "Xác nhận mã"
    
    VerifyScreen->>AuthCtrl: POST /auth/verify-email { token: OTP }
    AuthCtrl->>AuthSvc: Gọi logic xử lý: verifyEmail(token)
    
    %% Xử lý Verify Backend
    AuthSvc->>DBUser: SELECT tìm User theo emailVerificationToken
    DBUser-->>AuthSvc: Trả về bản ghi User tương ứng
    
    AuthSvc->>DBUser: UPDATE bản ghi User (isEmailVerified = true, emailVerificationToken = null)
    DBUser-->>AuthSvc: Trả về kết quả Update thành công
    
    AuthSvc-->>AuthCtrl: Trả kết quả xác thực thành công
    AuthCtrl-->>VerifyScreen: HTTP 200 OK
    
    %% Kết thúc và Đăng nhập
    VerifyScreen-->>User: Hiển thị thông báo "Xác thực tài khoản thành công"
    VerifyScreen->>VerifyScreen: Điều hướng về màn hình Đăng nhập (Login)
```
