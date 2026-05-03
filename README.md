# Sequence Diagram: Chức năng Đặt lịch khám (Tách bạch mọi Controller, Service, Database)

Dưới đây là phiên bản Sequence Diagram phân rã **mọi thành phần** trong hệ thống. Tuyệt đối không gộp chung bất kỳ Endpoint, Controller, Service hay Bảng Database nào. Mỗi luồng dữ liệu đều được vẽ chi tiết xuyên suốt từ: `Mobile UI` -> `Controller` -> `Service` -> `Database Table` và ngược lại.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    
    box rgba(200, 220, 255, 0.2) Mobile App (Frontend Screens)
    participant BookingFlow as BookingFlowScreen
    participant FacilityScreen as FacilitySelectionScreen
    participant DoctorScreen as DoctorSelectionScreen
    participant SlotScreen as SlotSelectionScreen
    end
    
    box rgba(255, 220, 200, 0.2) Backend Controllers (API)
    participant PatientCtrl as PatientController
    participant FacilityCtrl as FacilityController
    participant DoctorCtrl as DoctorController
    participant SlotCtrl as SlotController
    participant ApptCtrl as AppointmentsController
    participant PaymentCtrl as PaymentController
    end
    
    box rgba(200, 255, 200, 0.2) Backend Services (Logic)
    participant PatientSvc as PatientService
    participant FacilitySvc as FacilityService
    participant DoctorSvc as DoctorService
    participant SlotSvc as SlotService
    participant ApptSvc as AppointmentsService
    end
    
    box rgba(255, 255, 200, 0.2) Database (Tables)
    participant DBPatient as Table: patient_profiles
    participant DBFacility as Table: facilities
    participant DBService as Table: services
    participant DBDoctor as Table: doctors
    participant DBSlot as Table: slots
    participant DBAppt as Table: appointments
    end

    User->>BookingFlow: Mở chức năng Đặt lịch khám
    
    %% 1. Lấy Patient Profile
    BookingFlow->>PatientCtrl: GET /patient-profiles
    PatientCtrl->>PatientSvc: getPatientProfiles()
    PatientSvc->>DBPatient: SELECT thông tin bệnh nhân
    DBPatient-->>PatientSvc: Trả về dữ liệu
    PatientSvc-->>PatientCtrl: Dữ liệu đã xử lý
    PatientCtrl-->>BookingFlow: HTTP 200 OK (JSON)
    
    %% 2. Mở màn hình chọn Cơ sở
    BookingFlow->>FacilityScreen: Điều hướng (Navigator.push)
    FacilityScreen->>FacilityCtrl: GET /facilities
    FacilityCtrl->>FacilitySvc: getAllFacilities()
    FacilitySvc->>DBFacility: SELECT danh sách cơ sở
    DBFacility-->>FacilitySvc: Trả về dữ liệu
    FacilitySvc-->>FacilityCtrl: Danh sách cơ sở
    FacilityCtrl-->>FacilityScreen: HTTP 200 OK (JSON)
    FacilityScreen-->>User: Hiển thị danh sách Cơ sở
    User->>FacilityScreen: Click chọn Cơ sở
    FacilityScreen-->>BookingFlow: Trả kết quả & Đóng màn hình
    
    %% 3. Mở màn hình chọn Bác sĩ
    BookingFlow->>DoctorScreen: Điều hướng (Navigator.push)
    DoctorScreen->>DoctorCtrl: GET /doctors?facility_id=...
    DoctorCtrl->>DoctorSvc: getDoctors(facility_id)
    DoctorSvc->>DBDoctor: SELECT danh sách bác sĩ
    DBDoctor-->>DoctorSvc: Trả về dữ liệu
    DoctorSvc-->>DoctorCtrl: Danh sách bác sĩ
    DoctorCtrl-->>DoctorScreen: HTTP 200 OK (JSON)
    DoctorScreen-->>User: Hiển thị danh sách Bác sĩ
    User->>DoctorScreen: Click chọn Bác sĩ
    DoctorScreen-->>BookingFlow: Trả kết quả & Đóng màn hình
    
    %% 4. Mở màn hình chọn Ca khám
    BookingFlow->>SlotScreen: Điều hướng (Navigator.push)
    SlotScreen->>SlotCtrl: GET /slots?doctor_id=...&facility_id=...
    SlotCtrl->>SlotSvc: getSlots(doctor, facility)
    SlotSvc->>DBSlot: SELECT danh sách ca khám trống
    DBSlot-->>SlotSvc: Trả về dữ liệu
    SlotSvc-->>SlotCtrl: Danh sách ca khám
    SlotCtrl-->>SlotScreen: HTTP 200 OK (JSON)
    SlotScreen-->>User: Hiển thị danh sách Ca khám
    User->>SlotScreen: Click chọn Ca khám
    SlotScreen-->>BookingFlow: Trả kết quả & Đóng màn hình
    
    %% 5. Lấy thông tin Dịch vụ tại cơ sở
    BookingFlow->>FacilityCtrl: GET /services?facility_id=...
    FacilityCtrl->>FacilitySvc: getServicesByFacility(id)
    FacilitySvc->>DBService: SELECT danh sách dịch vụ
    DBService-->>FacilitySvc: Trả về dữ liệu
    FacilitySvc-->>FacilityCtrl: Danh sách dịch vụ
    FacilityCtrl-->>BookingFlow: HTTP 200 OK (JSON)
    
    %% 6. Xác nhận Đặt lịch
    BookingFlow-->>User: Hiển thị Giao diện Xác nhận (Final UI)
    User->>BookingFlow: Nhập Triệu chứng, Chọn Thanh toán & Nhấn "Xác nhận"
    BookingFlow->>BookingFlow: Validate Form (Kiểm tra dữ liệu)
    
    %% 7. Gọi API Đặt lịch
    BookingFlow->>ApptCtrl: POST /appointments (Gửi yêu cầu)
    ApptCtrl->>ApptSvc: createAppointment(dto)
    
    %% Validate ở Backend
    ApptSvc->>DBPatient: Truy vấn kiểm tra tồn tại Hồ sơ
    ApptSvc->>DBSlot: Truy vấn kiểm tra Slot hợp lệ & Trạng thái trống
    
    %% Database Transaction
    Note over ApptSvc,DBAppt: Bắt đầu Transaction Database
    ApptSvc->>DBAppt: Kiểm tra khóa (Slot đã có người đặt chưa?)
    ApptSvc->>DBAppt: INSERT bản ghi Appointment (Trạng thái: pending)
    ApptSvc->>DBSlot: UPDATE bản ghi Slot (Khóa is_active=0, giảm available_count)
    Note over ApptSvc,DBAppt: Kết thúc Transaction Database
    
    ApptSvc->>ApptSvc: Thiết lập Hẹn giờ 5 phút hủy lịch nếu chưa thanh toán
    
    ApptSvc-->>ApptCtrl: Trả về ID lịch hẹn
    ApptCtrl-->>BookingFlow: HTTP 200/201 OK (Kèm Appointment ID)
    
    %% 8. Khởi tạo Thanh toán
    BookingFlow->>PaymentCtrl: POST /payments (Tạo phiên thanh toán)
    PaymentCtrl-->>BookingFlow: HTTP 200 OK (Thông tin thanh toán)
    
    BookingFlow-->>User: Thông báo "Đặt lịch thành công" & Điều hướng Trang chủ
```
