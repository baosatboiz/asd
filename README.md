# Sequence Diagram: Chức năng Đăng nhập (Kịch bản chuẩn)

Dưới đây là Sequence Diagram mô tả luồng đăng nhập thành công. Để sơ đồ tinh gọn hơn, toàn bộ logic gửi API ở phía Client (Mobile) đã được gộp chung vào khối `LoginScreen`. Khi đó khối `AuthService` sẽ chỉ còn đại diện duy nhất cho logic xử lý ở phía Backend.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant LoginScreen as LoginScreen
    participant AuthStorage as AuthStorage
    participant AuthController as AuthController
    participant AuthService as AuthService
    participant TableUser as Table: users
    participant TableRefreshToken as Table: refresh_tokens

    User->>LoginScreen: Nhập Email & Mật khẩu
    User->>LoginScreen: Nhấn nút "Đăng nhập"
    
    LoginScreen->>LoginScreen: Kiểm tra tính hợp lệ (Validation)
    
    LoginScreen->>AuthController: Gửi request POST /auth/login
    
    AuthController->>AuthService: Gọi logic login(loginDto)
    
    AuthService->>TableUser: Lấy thông tin User bằng email
    TableUser-->>AuthService: Trả về dữ liệu User (có mật khẩu băm)
    
    AuthService->>AuthService: Đối chiếu mật khẩu mã hóa
    AuthService->>AuthService: Generate Access & Refresh Tokens
    
    AuthService->>TableRefreshToken: Lưu bản ghi Refresh Token
    TableRefreshToken-->>AuthService: Lưu thành công
    
    AuthService-->>AuthController: Trả về Tokens & thông tin User
    AuthController-->>LoginScreen: HTTP 200 OK Response
    
    LoginScreen->>AuthStorage: Lưu Tokens: saveTokens()
    LoginScreen->>AuthStorage: Lưu User: saveUser()
    
    LoginScreen->>LoginScreen: Chuyển hướng context.go('/home')
    LoginScreen-->>User: Hiển thị Màn hình Home
```
