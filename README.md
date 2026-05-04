# Sequence Diagram: Chức năng Đăng ký (Có xác thực Email)

Dưới đây là sơ đồ Sequence chi tiết cho chức năng Đăng ký tài khoản có bổ sung **Luồng Xác thực Email (Email Verification)**. Tất cả các bước được vẽ nối tiếp nghiêm ngặt (Synchronous Request - Response) để đảm bảo tính liên tục của luồng thực thi. 

*(Ghi chú: Lớp Service đã được gộp chung vào Controller theo yêu cầu của dự án)*

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant MobileApp as Register Screen
    participant VerifyScreen as Verify OTP Screen
    participant AuthCtrl as Auth Controller
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
    
    %% Xử lý nghiệp vụ Backend tại Controller
    AuthCtrl->>DBUser: SELECT findFirst (Kiểm tra trùng lặp Email hoặc SĐT)
    DBUser-->>AuthCtrl: Trả về kết quả (Null = Hợp lệ)
    
    AuthCtrl->>AuthCtrl: Băm mật khẩu (bcrypt) & Tạo Mã xác thực (OTP)
    
    %% Database Transaction
    Note over AuthCtrl,DBProfile: Bắt đầu Transaction tạo tài khoản
    AuthCtrl->>DBUser: INSERT bản ghi User (isEmailVerified: false, emailVerificationToken: OTP)
    DBUser-->>AuthCtrl: Trả về ID của User vừa tạo
    
    AuthCtrl->>DBProfile: INSERT bản ghi PatientProfile (is_primary: 1)
    DBProfile-->>AuthCtrl: Trả về kết quả tạo Profile
    Note over AuthCtrl,DBProfile: Kết thúc Transaction (Commit)
    
    %% Gửi Email
    AuthCtrl->>MailSvc: sendVerificationEmail(email, OTP)
    MailSvc-->>AuthCtrl: Xác nhận đã đẩy email vào hàng đợi
    MailSvc-)User: (Bất đồng bộ) Gửi Email thực tế đến hòm thư người dùng
    
    %% Phản hồi Đăng ký thành công (nhưng chưa verify)
    AuthCtrl-->>MobileApp: HTTP 201 Created Response (Thành công, yêu cầu xác thực)
    
    %% 2. QUÁ TRÌNH XÁC THỰC EMAIL (VERIFY)
    MobileApp->>VerifyScreen: Điều hướng tự động sang màn hình Nhập OTP
    VerifyScreen-->>User: Hiển thị form nhập OTP
    
    User->>VerifyScreen: Mở Email, đọc mã OTP và điền vào form
    User->>VerifyScreen: Nhấn nút "Xác nhận mã"
    
    VerifyScreen->>AuthCtrl: POST /auth/verify-email { token: OTP }
    
    %% Xử lý Verify Backend tại Controller
    AuthCtrl->>DBUser: SELECT tìm User theo emailVerificationToken
    DBUser-->>AuthCtrl: Trả về bản ghi User tương ứng
    
    AuthCtrl->>DBUser: UPDATE bản ghi User (isEmailVerified = true, emailVerificationToken = null)
    DBUser-->>AuthCtrl: Trả về kết quả Update thành công
    
    AuthCtrl-->>VerifyScreen: HTTP 200 OK (Xác thực thành công)
    
    %% Kết thúc và Đăng nhập
    VerifyScreen-->>User: Hiển thị thông báo "Xác thực tài khoản thành công"
    VerifyScreen->>VerifyScreen: Điều hướng về màn hình Đăng nhập (Login)
```
