sequenceDiagram
    autonumber
    actor User as User
    participant RegisterScreen as RegisterScreen
    participant AuthStorage as AuthStorage
    participant AuthController as AuthController
    participant AuthService as AuthService
    participant TableUser as Table: users
    participant TablePatientProfile as Table: patient_profiles

    User->>RegisterScreen: Nhập thông tin (Tên, Email, SĐT, Mật khẩu)
    User->>RegisterScreen: Nhấn nút "Đăng ký"
    
    RegisterScreen->>RegisterScreen: Kiểm tra tính hợp lệ dữ liệu (Validation)
    
    RegisterScreen->>AuthController: Gửi request POST /auth/register
    
    AuthController->>AuthService: Gọi logic register(registerDto)
    
    AuthService->>TableUser: Kiểm tra trùng lặp Email hoặc SĐT (findFirst)
    TableUser-->>AuthService: Trả về kết quả kiểm tra
    
    AuthService->>AuthService: Băm mật khẩu (bcrypt.hash)
    
    Note over AuthService,TablePatientProfile: Bắt đầu Transaction Database
    
    AuthService->>TableUser: Lưu bản ghi User mới
    TableUser-->>AuthService: Trả về ID của User
    
    AuthService->>TablePatientProfile: Lưu bản ghi PatientProfile (nếu role=patient)
    TablePatientProfile-->>AuthService: Lưu thành công
    
    Note over AuthService,TablePatientProfile: Kết thúc Transaction
    
    AuthService-->>AuthController: Trả về kết quả thành công và thông tin User
    AuthController-->>RegisterScreen: HTTP 201 Created Response
    
    RegisterScreen->>AuthStorage: Lưu tạm thông tin User: saveUser()
    
    RegisterScreen->>RegisterScreen: Chuyển hướng tới trang Đăng nhập / Trang chủ
    RegisterScreen-->>User: Thông báo đăng ký thành công
