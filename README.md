# Báo Cáo Kỹ Thuật – Dự Án `clinic-ai-booking`
> **Cập nhật lần cuối:** 2026-05-22 — Đã bổ sung file AI từ commit `0c9e142`
### Các Chức Năng Được Phân Công: Đăng nhập · Đăng ký · Đặt lịch · Phỏng đoán bệnh AI

---

## 1. Danh Sách Chức Năng Được Phân Công

| # | Chức năng | Mô tả ngắn |
|---|-----------|------------|
| 1 | **Đăng ký tài khoản** | Người dùng tạo tài khoản mới bằng email + mật khẩu; tự động tạo hồ sơ bệnh nhân |
| 2 | **Đăng nhập** | Xác thực bằng email/mật khẩu hoặc Google OAuth; cấp JWT access + refresh token |
| 3 | **Đặt lịch khám** | Bệnh nhân chọn bác sĩ → cơ sở → slot thời gian → xác nhận lịch hẹn |
| 4 | **Phỏng đoán bệnh với AI** | Nhập triệu chứng → AI (Gemini) phân tích → trả về mức độ khẩn cấp + chuyên khoa đề xuất |

---

## 2. Kiến Trúc Chi Tiết Hệ Thống

### 2.1 Tổng quan kiến trúc (3 lớp)

```
┌──────────────────────────────────────────┐
│         MOBILE CLIENT (Flutter)           │
│  lib/features/{auth, booking, ai_triage} │
│         Dio HTTP Client                   │
└──────────────┬───────────────────────────┘
               │  HTTPS / REST API
┌──────────────▼───────────────────────────┐
│         BACKEND (NestJS + TypeScript)     │
│  src/modules/{auth, appointments, ai}     │
│  Guards: JwtGuard, RolesGuard            │
│  Validation: class-validator DTO         │
└──────────────┬───────────────────────────┘
               │  Prisma ORM
┌──────────────▼───────────────────────────┐
│         DATABASE (MySQL)                  │
│  tblUser, tblRefreshTokens,              │
│  tblPatientProfile, tblSlots,            │
│  tblAppointment, tblAiTriageSessions...  │
└──────────────────────────────────────────┘
```

### 2.2 Sơ đồ luồng dữ liệu từng chức năng

```
[ĐĂNG KÝ]
Flutter RegisterScreen
  → POST /auth/register (RegisterRequest DTO)
    → AuthService.register()
      → bcrypt.hash(password)
      → prisma.$transaction: tblUser.create + tblPatientProfile.create
      → return { user_id, email, role, status }

[ĐĂNG NHẬP]
Flutter LoginScreen
  → POST /auth/login (LoginRequest DTO)
    → AuthService.login()
      → prisma.user.findUnique(email)
      → bcrypt.compare(password, hash)
      → generateTokens() → tblRefreshTokens.create
      → return { access_token, refresh_token, expires_in }

[ĐẶT LỊCH KHÁM]
Flutter BookingFlowScreen
  → GET /slots?doctor_id=&date=     (chọn slot)
  → POST /appointments (CreateAppointmentDto)
    → AppointmentsService.createAppointment()
      → validate patient + slot + facility
      → prisma.$transaction: tblAppointment.create + tblSlots.update(decrement)
      → setTimeout(5 phút): tự hủy nếu chưa thanh toán
      → return appointment details

[AI PHỎNG ĐOÁN]
Flutter AiTriageScreen
  → POST /ai/triage (TriageRequestDto) [Bearer Token]
    → AiService.triageSymptoms()
      → Google Gemini API (gemini-flash-latest)
      → parseAndValidateTriageJson(response)
      → prisma.aiTriageSession.create()
      → return { urgency, specialty, reasoning }
```

### 2.3 Kết nối giữa các thành phần

| Thành phần | Kết nối với | Giao thức/Cơ chế |
|---|---|---|
| Flutter `AuthService` | NestJS `AuthController` | HTTP POST qua `DioClient` |
| NestJS `AuthController` | `AuthService` | Dependency Injection |
| `AuthService` | MySQL (`tblUser`) | Prisma ORM |
| `AuthService` | Google OAuth API | `fetch()` HTTPS |
| `AiService` | Google Gemini API | `@google/generative-ai` SDK |
| `AppointmentsService` | MySQL (`tblAppointment`, `tblSlots`) | Prisma transaction |
| Flutter screens | NestJS (các route bảo vệ) | JWT Bearer Token trong Header |

---

## 3. Code Đáp Ứng Chức Năng

### ─── CHỨC NĂNG 1: ĐĂNG KÝ ───

#### 3.1.1 Backend – DTO (Kiểm tra đầu vào)

**File:** [auth.dto.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/auth/dto/auth.dto.ts)

```typescript
export class RegisterRequest {
  @IsEmail()        email!: string;       // Phải là email hợp lệ
  @IsString()       phone!: string;       // Số điện thoại
  @IsString()
  @MinLength(8)     password!: string;    // Mật khẩu tối thiểu 8 ký tự
  @IsString()
  @MaxLength(150)   full_name!: string;   // Họ tên
  @IsEnum(UserRole) role!: UserRole;      // 'patient' | 'doctor' | 'admin'
}
```

#### 3.1.2 Backend – Controller

**File:** [auth.controller.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/auth/auth.controller.ts#L52-L55)

```typescript
@Post('register')           // Route: POST /auth/register
async register(@Body() registerDto: RegisterRequest) {
  return this.authService.register(registerDto);
}
```

#### 3.1.3 Backend – Service (Logic chính)

**File:** [auth.service.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/auth/auth.service.ts#L173-L231)

| Hàm | Mô tả |
|-----|-------|
| `register(dto)` | Hàm đăng ký chính – kiểm tra trùng email/phone, hash mật khẩu, tạo User + PatientProfile trong transaction |
| `bcrypt.hash(password, 10)` | Mã hóa mật khẩu với cost factor 10 (≈ 100ms) trước khi lưu DB |
| `prisma.$transaction(...)` | Đảm bảo tạo `tblUser` và `tblPatientProfile` **đồng thời** – nếu 1 bước lỗi thì cả 2 đều rollback |

**Logic quan trọng:**
- Kiểm tra `email` hoặc `phone` đã tồn tại → ném `ConflictException`
- Nếu `role === 'patient'`: tự động tạo `PatientProfile` với `is_primary = 1` (hồ sơ chính của bản thân)

#### 3.1.4 Mobile – Flutter UI & Service

**File:** [register_screen.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/auth/screens/register_screen.dart) | [auth_service.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/auth/services/auth_service.dart#L32-L66)

```dart
// AuthService.register() – gọi API đăng ký
Future<Map<String, dynamic>> register({
  required String email,
  required String password,
  required String full_name,
  required String phone,
  String role = 'patient',        // Mặc định là bệnh nhân
}) async {
  final response = await dioClient.post('/auth/register', data: {
    'email': email, 'phone': phone,
    'password': password, 'full_name': full_name,
    'role': role.toLowerCase(),
  });
  // Lưu thông tin user vào local storage sau khi đăng ký thành công
  await authStorage.saveUser(data['data']);
}
```

---

### ─── CHỨC NĂNG 2: ĐĂNG NHẬP ───

#### 3.2.1 Backend – DTO

```typescript
export class LoginRequest {
  @IsEmail()  email!: string;
  @IsString() password!: string;
}
```

#### 3.2.2 Backend – Controller Endpoints

**File:** [auth.controller.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/auth/auth.controller.ts)

| Method | Route | Chức năng |
|--------|-------|-----------|
| `POST` | `/auth/login` | Đăng nhập email/password |
| `GET` | `/auth/google` | Redirect sang Google OAuth (web) |
| `GET` | `/auth/callback/google` | Callback nhận `code` từ Google |
| `POST` | `/auth/google/mobile` | Đăng nhập Google từ app (nhận `id_token`) |
| `POST` | `/auth/refresh` | Làm mới access token |
| `POST` | `/auth/forgot-password` | Yêu cầu reset mật khẩu (gửi OTP) |
| `POST` | `/auth/reset-password` | Đặt lại mật khẩu với OTP |
| `POST` | `/auth/logout` | Đăng xuất (thu hồi refresh token) |

#### 3.2.3 Backend – Service (Logic chính)

**File:** [auth.service.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/auth/auth.service.ts)

| Hàm | Mô tả |
|-----|-------|
| `login(dto)` | Tìm user theo email → so sánh password hash → gọi `generateTokens()` |
| `generateTokens(user_id, email, role)` | Tạo JWT access token (15 phút) + refresh token (7 ngày), lưu refresh token vào `tblRefreshTokens` |
| `refresh(refreshToken)` | Xác minh refresh token → kiểm tra DB → thu hồi token cũ → cấp cặp token mới |
| `logout(user_id)` | Đánh dấu `is_revoked = 1` cho toàn bộ refresh token của user |
| `loginWithGoogleMobile(dto)` | Xác minh `id_token` với Google API → upsert user → cấp JWT |
| `upsertGoogleUserAndIssueTokens(profile)` | Nếu email chưa có trong DB → tạo user mới tự động; nếu có → đăng nhập luôn |
| `forgotPassword(dto)` | Tạo OTP 6 số → lưu vào `tblPasswordResetTokens` (hết hạn sau 15 phút) |
| `resetPassword(dto)` | Kiểm tra OTP còn hiệu lực → hash mật khẩu mới → cập nhật DB trong transaction |

**Cấu trúc JWT Payload:**
```typescript
interface JwtPayload {
  sub: string;      // user_id (dạng string)
  email: string;
  role: UserRole;   // 'patient' | 'doctor' | 'admin'
}
```

#### 3.2.4 Mobile – Flutter Service

**File:** [auth_service.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/auth/services/auth_service.dart)

```dart
// Đăng nhập email/password
Future<Map<String, dynamic>> login({required String email, required String password}) async {
  final response = await dioClient.post('/auth/login', data: {'email': email, 'password': password});
  // Lưu access_token + refresh_token vào secure storage
  await authStorage.saveTokens(
    accessToken: responseData['access_token'],
    refreshToken: responseData['refresh_token'],
  );
}

// Đăng nhập Google (mobile)
Future<Map<String, dynamic>> loginWithGoogle() async {
  final account = await _googleSignIn.signIn();  // Hiện dialog chọn Google account
  final auth = await account.authentication;
  // Gửi id_token lên backend để verify
  final response = await dioClient.post('/auth/google/mobile', data: {'id_token': auth.idToken});
}
```

---

### ─── CHỨC NĂNG 3: ĐẶT LỊCH KHÁM ───

#### 3.3.1 Backend – DTO

**File:** [appointment.dto.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/appointments/dto)

```typescript
export class CreateAppointmentDto {
  patient_id!: string;       // ID hồ sơ bệnh nhân
  slot_id!: string;          // ID khung giờ được chọn
  facility_id!: string;      // ID cơ sở y tế
  service_id?: string;       // ID dịch vụ (tuỳ chọn)
  appointmentType!: string;  // 'consultation' | 'vaccination'
  symptomsNote?: string;     // Mô tả triệu chứng (tuỳ chọn)
  note?: string;             // Ghi chú thêm
}
```

#### 3.3.2 Backend – Controller

**File:** [appointments.controller.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/appointments/appointments.controller.ts)

| Method | Route | Guard | Chức năng |
|--------|-------|-------|-----------|
| `POST` | `/appointments` | JWT + Role=patient | Tạo lịch hẹn mới |
| `GET` | `/appointments` | JWT | Xem danh sách lịch hẹn của user |
| `GET` | `/appointments/:id` | JWT | Xem chi tiết 1 lịch hẹn |

#### 3.3.3 Backend – Service (Logic chính)

**File:** [appointments.service.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/appointments/appointments.service.ts)

| Hàm | Mô tả |
|-----|-------|
| `createAppointment(user_id, dto)` | Hàm đặt lịch chính – validation đầy đủ → tạo appointment trong transaction |
| `getAppointmentById(user_id, id)` | Trả về chi tiết 1 lịch hẹn, có kèm thông tin bác sĩ, cơ sở, dịch vụ |
| `getUserAppointments(user_id)` | Trả danh sách tất cả lịch hẹn của user, sắp xếp theo ngày mới nhất |

**Logic đặt lịch chi tiết (trong `createAppointment`):**

1. Validate `patient_id` thuộc về `user_id` đang đăng nhập
2. Validate `slot` tồn tại, `is_active = 1`, `status = AVAILABLE`, `available_count > 0`
3. Validate `slot.facility_id` khớp với `facility_id` trong request
4. Kiểm tra chưa có appointment nào đã book slot này
5. Mở **Prisma Transaction**:
   - Tạo bản ghi `tblAppointment` với `status = pending`
   - Giảm `available_count` của slot đi 1, đặt `is_active = 0`
6. Cài **setTimeout 5 phút**: nếu appointment vẫn `pending` (chưa thanh toán) → tự động `cancelled` + restore slot

#### 3.3.4 Mobile – Booking Flow

**File:** [booking_flow_screen.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/booking/screens/booking_flow_screen.dart)

Màn hình booking là một **multi-step wizard** bao gồm các bước:

```
Step 1: Chọn cơ sở y tế  (FacilitySelectionScreen)
Step 2: Chọn bác sĩ       (DoctorSelectionScreen)
Step 3: Chọn ngày/giờ     (SlotSelectionScreen)
Step 4: Xác nhận & ghi chú
Step 5: Thanh toán
```

**Các màn hình liên quan:**

| File | Chức năng |
|------|-----------|
| [booking_flow_screen.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/booking/screens/booking_flow_screen.dart) | Controller chính quản lý các bước booking |
| [slot_selection_screen.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/booking/screens/slot_selection_screen.dart) | Hiển thị lịch + chọn khung giờ trống |
| [doctor_selection_screen.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/booking/screens/doctor_selection_screen.dart) | Danh sách + bộ lọc bác sĩ |
| [appointment_history_screen.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/booking/screens/appointment_history_screen.dart) | Xem lịch sử các lịch hẹn |

---

### ─── CHỨC NĂNG 4: PHỎNG ĐOÁN BỆNH VỚI AI ───

#### 3.4.1 Backend – DTO

**File:** [ai.dto.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/ai/dto/ai.dto.ts)

```typescript
// Input
export class TriageRequestDto {
  @IsString() @MinLength(3)
  symptoms!: string;           // Mô tả triệu chứng (bắt buộc, ít nhất 3 ký tự)
  
  @IsOptional() duration?: string;         // Thời gian bị bệnh (tuỳ chọn)
  @IsOptional() severity?: string;         // Mức độ nặng nhẹ (tuỳ chọn)
  @IsOptional() additionalInfo?: object;   // Thông tin bổ sung
}

// Output
export class TriageResultDto {
  urgency!: 'Emergency' | 'Urgent' | 'Routine';  // Mức độ khẩn cấp
  specialty!: string;      // Chuyên khoa được đề xuất
  reasoning!: string;      // Lý do giải thích (tiếng Việt)
}
```

#### 3.4.2 Backend – Controller

**File:** [ai.controller.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/ai/ai.controller.ts)

| Method | Route | Guard | Chức năng |
|--------|-------|-------|-----------|
| `POST` | `/ai/triage` | JWT | Phân tích triệu chứng → trả kết quả AI |
| `POST` | `/ai/previsit-summary` | JWT | Tóm tắt tiền thăm khám cho bác sĩ |

#### 3.4.3 Backend – Service (Logic AI)

**File:** [ai.service.ts](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/src/modules/ai/ai.service.ts)

| Hàm | Mô tả |
|-----|-------|
| `triageSymptoms(userId, symptoms)` | Hàm phân tích chính: gọi Gemini API → parse JSON → lưu session vào DB |
| `generateWithModel(gemini, text)` | Wrapper gọi Gemini SDK, có log thời gian thực thi và xử lý lỗi |
| `parseAndValidateTriageJson(rawText)` | Làm sạch markdown/code blocks → parse JSON → validate `urgency`, `specialty`, `reasoning` |
| `mapUrgencyToDb(urgency)` | Ánh xạ `Emergency→URGENT`, `Urgent→SOON`, `Routine→NORMAL` (enum DB) |
| `generatePrevisitSummary(dto)` | Tạo tóm tắt tiền khám (hiện là mock data, chưa gọi LLM thật) |

**System Prompt gửi cho Gemini (tiếng Việt không dấu):**
```
"Ban la y ta phan luong (triage nurse) cho phong kham.
Nhiem vu: phan tich trieu chung benh nhan va phan loai muc do uu tien.
Bat buoc tra ve DUY NHAT mot JSON hop le:
{"urgency":"Emergency|Urgent|Routine","specialty":"<ten chuyen khoa>","reasoning":"<giai thich>"}"
```

**Model sử dụng:** `gemini-flash-latest` (cấu hình qua env `GEMINI_MODEL`)

#### 3.4.4 API Gọi Ngoài (External API)

| API | Mục đích | Endpoint |
|-----|----------|----------|
| **Google Gemini AI** | Phân tích triệu chứng → triage | `@google/generative-ai` SDK |
| **Google OAuth** (tokeninfo) | Xác thực `id_token` đăng nhập Google | `https://oauth2.googleapis.com/tokeninfo` |
| **Google UserInfo** | Lấy thông tin profile người dùng | `https://www.googleapis.com/oauth2/v3/userinfo` |
| **Google OAuth token** | Đổi `code` → `access_token` (web flow) | `https://oauth2.googleapis.com/token` |
| **SMTP (Nodemailer)** | Gửi email xác thực tài khoản | Cấu hình qua `SMTP_HOST/USER/PASS` |

#### 3.4.5 Mobile – Flutter Service (`AiService`)

**File:** [ai_service.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/ai/services/ai_service.dart)
_(Kéo về từ commit `0c9e142` – đây là bản gọi API thật)_

```dart
// Model kết quả trả về từ backend
class AiTriageResult {
  final String urgency;    // 'Emergency' | 'Urgent' | 'Routine'
  final String specialty;  // Chuyên khoa gợi ý
  final String reasoning;  // Lý do (tiếng Việt)

  factory AiTriageResult.fromJson(Map<String, dynamic> json) { ... }
}

// Service gọi API
class AiService {
  final DioClient dioClient;

  Future<AiTriageResult> triageSymptoms(String symptoms) async {
    final response = await dioClient.post('/ai/triage',
        data: {'symptoms': symptoms});
    // Parse + validate response
    return AiTriageResult.fromJson(response.data);
  }
}
```

| Hàm | Mô tả |
|-----|-------|
| `triageSymptoms(symptoms)` | Gọi `POST /ai/triage`, parse JSON → `AiTriageResult` |
| `AiTriageResult.fromJson()` | Parse field `urgency`, `specialty`, `reasoning`; trim() từng field |
| Xử lý lỗi | Bắt `DioException`, đọc `response.data['message']` từ server để hiện thông báo chính xác |

#### 3.4.6 Mobile – UI Triage (`AiTriageScreen`)

**File:** [ai_triage_screen.dart](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/mobile/lib/features/ai/screens/ai_triage_screen.dart)
_(Kéo về từ commit `0c9e142` – thay thế bản mock cũ tại `ai_triage/screens/triage_screen.dart`)_

Màn hình `AiTriageScreen` là form **hướng dẫn 5 bước** đầy đủ:

| Bước | UI Component | Dữ liệu thu thập |
|------|-------------|------------------|
| 1 | `FilterChip` (multi-select) | Triệu chứng chính: Fever, Cough, Chest pain, Shortness of breath,... (12 mục) |
| 2 | `DropdownButtonFormField` | Vùng cơ thể: Head, ENT, Chest, Abdomen, Back, Skin, Urinary, General |
| 3 | `ChoiceChip` (màu động) | Mức độ nặng: Mild(1-3) 🟢 / Moderate(4-6) 🟡 / Severe(7-8) 🟠 / Emergency(9-10) 🔴 |
| 4 | `ChoiceChip` | Thời gian: Today / 1-2 days / 3-7 days / 1-4 weeks / >1 month |
| 5 | `FilterChip` (multi-select) | Dấu hiệu cảnh báo khẩn: Trouble breathing, Severe chest pain, Fainting, High fever >39C,... |
| + | `TextField` (3-5 dòng) | Mô tả thêm tự do (tuỳ chọn) |

**Luồng xử lý trong `_runTriage()`:**
```dart
// 1. Gom tất cả input thành 1 chuỗi payload
String _buildSymptomsPayload() {
  // VD: "Main symptoms: Fever, Cough. Affected area: Chest.
  //      Muc do: Severe (7-8). Duration: 3-7 days.
  //      Warning signs: Trouble breathing"
}

// 2. Validate: phải có ít nhất 1 symptom hoặc 5+ ký tự mô tả
// 3. Gọi AiService.triageSymptoms(payload)
// 4. Cập nhật state: _result / _error / _isLoading
```

**Hiển thị kết quả:**
```dart
if (_result != null) {
  Text('Urgency: ${_result!.urgency}');        // Emergency / Urgent / Routine
  Text('Suggested Specialty: ${_result!.specialty}');  // VD: Nội tổng quát
  Text(_result!.reasoning);                    // Giải thích bằng tiếng Việt
  OutlinedButton(
    onPressed: () => context.go('/?tab=0&specialty=${_result!.specialty}'),
    child: Text('Find Doctors'),   // → chuyển sang trang tìm bác sĩ đúng chuyên khoa
  );
}
```

**Route trong router:** `path: '/ai-triage'` → `AiTriageScreen(authService: authService)`

---

## 4. Bảng Cơ Sở Dữ Liệu (CSDL)

### Các bảng liên quan đến chức năng được phân công

**File schema:** [schema.prisma](file:///c:/Users/ADMIN/Desktop/developer/app/clinic-ai-booking/backend/prisma/schema.prisma)

#### `tblUser` – Bảng người dùng

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `user_id` | BigInt PK | ID tự tăng |
| `role` | Enum | `admin` / `doctor` / `patient` |
| `full_name` | VarChar(150) | Họ và tên |
| `email` | VarChar(150) UNIQUE | Email đăng nhập |
| `phone` | VarChar(20) UNIQUE | Số điện thoại |
| `password_hash` | VarChar(255) | Mật khẩu đã bcrypt hash |
| `avatar_url` | VarChar(255)? | Ảnh đại diện |
| `status` | Enum | `active` / `inactive` / `blocked` |

#### `tblRefreshTokens` – Quản lý phiên đăng nhập

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | BigInt PK | |
| `user_id` | BigInt FK | Liên kết với `tblUser` |
| `token` | VarChar(512) UNIQUE | Chuỗi JWT refresh token |
| `expires_at` | DateTime | Thời hạn hết hạn |
| `is_revoked` | TinyInt | `0` = còn hiệu lực, `1` = đã thu hồi |

#### `tblPasswordResetTokens` – OTP đặt lại mật khẩu

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `token` | VarChar(512) UNIQUE | OTP 6 chữ số |
| `status` | Enum | `PENDING` / `USED` / `EXPIRED` |
| `expires_at` | DateTime | Hết hạn sau 15 phút |

#### `tblPatientProfile` – Hồ sơ bệnh nhân

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `patient_id` | BigInt PK | |
| `user_id` | BigInt FK | Chủ tài khoản |
| `full_name` | VarChar(150) | Họ tên bệnh nhân |
| `is_primary` | TinyInt | `1` = hồ sơ chính của bản thân |
| `relationship_to_user` | VarChar(50) | Quan hệ với chủ tài khoản (VD: "Bản thân", "Con") |
| `gender`, `date_of_birth` | Enum / Date | Thông tin nhân khẩu học |
| `medical_conditions`, `allergies` | Text | Bệnh sử, dị ứng |

#### `tblSlots` – Khung giờ khám

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `slot_id` | BigInt PK | |
| `doctor_id` | BigInt FK | Bác sĩ phụ trách slot |
| `facility_id` | BigInt FK | Cơ sở y tế |
| `slot_date` | Date | Ngày khám |
| `start_time`, `end_time` | Time | Giờ bắt đầu/kết thúc |
| `available_count` | Int | Số chỗ còn trống |
| `status` | Enum | `AVAILABLE` / `FULL` / `CANCELLED` |
| `is_active` | TinyInt | `0` = đang được giữ chỗ |

#### `tblAppointment` – Lịch hẹn khám

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `appointment_id` | BigInt PK | |
| `appointment_code` | VarChar(30) UNIQUE | Mã lịch hẹn, VD: `APT-1716287400000` |
| `user_id`, `patient_id` | BigInt FK | Người đặt / hồ sơ bệnh nhân |
| `doctor_id`, `facility_id` | BigInt FK | Bác sĩ / cơ sở y tế |
| `slot_id` | BigInt FK UNIQUE | Khung giờ (1 slot = 1 appointment) |
| `appointment_type` | Enum | `consultation` / `vaccination` |
| `status` | Enum | `pending` / `confirmed` / `completed` / `cancelled` / `no_show` |
| `symptoms_note` | Text? | Triệu chứng do bệnh nhân khai |
| `total_amount` | Decimal(12,2) | Tổng tiền |

#### `tblAiTriageSessions` – Lịch sử phiên AI

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | BigInt PK | |
| `user_id` | BigInt FK | Người dùng thực hiện triage |
| `symptoms_input` | Text? | Triệu chứng đã nhập |
| `urgency_level` | Enum | `NORMAL` / `SOON` / `URGENT` |
| `recommended_specialties` | JSON | Danh sách chuyên khoa đề xuất |
| `pre_visit_summary` | JSON | Kết quả phân tích (có `reasoning`) |
| `status` | Enum | `IN_PROGRESS` / `COMPLETED` / `ABANDONED` |
| `is_completed` | TinyInt | `1` = đã hoàn thành |

---

## 5. Hướng Dẫn Cài Đặt & Triển Khai

### 5.1 Yêu Cầu Môi Trường

| Công cụ | Phiên bản tối thiểu |
|---------|-------------------|
| Node.js | 18.x trở lên |
| npm | 9.x trở lên |
| MySQL | 8.0 trở lên |
| Flutter SDK | 3.x trở lên |
| Dart SDK | 3.x (đi kèm Flutter) |

### 5.2 Cài Đặt Backend (NestJS)

**Bước 1 – Clone & cài dependencies:**
```bash
cd backend
npm install
```

**Bước 2 – Cấu hình biến môi trường:**
```bash
# Tạo file .env từ mẫu
copy .env.example .env
```

Chỉnh sửa `.env`:
```env
# Database
DATABASE_URL="mysql://root:password@localhost:3306/clinic_ai"

# JWT (PHẢI đổi thành chuỗi random dài trong production)
JWT_SECRET="your_super_secret_key_here"
JWT_REFRESH_SECRET="your_super_secret_refresh_key"
JWT_EXPIRES_IN="15m"
JWT_REFRESH_EXPIRES_IN="7d"

# Google OAuth (lấy từ Google Cloud Console)
GOOGLE_CLIENT_ID="your_google_client_id"
GOOGLE_CLIENT_SECRET="your_google_client_secret"
GOOGLE_CALLBACK_URL="http://localhost:3000/auth/callback/google"

# Google Gemini AI (lấy từ Google AI Studio)
GEMINI_API_KEY="your_gemini_api_key"
GEMINI_MODEL="gemini-flash-latest"

# SMTP (cho tính năng gửi email)
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="your_email@gmail.com"
SMTP_PASS="your_app_password"

# Server
NODE_ENV="development"
PORT=3000
```

**Bước 3 – Khởi tạo cơ sở dữ liệu:**
```bash
# Chạy migration tạo bảng
npx prisma migrate dev --name init

# (Tuỳ chọn) Seed dữ liệu mẫu
npx ts-node prisma/seed.ts
```

**Bước 4 – Chạy server:**
```bash
# Development (có hot-reload)
npm run start:dev

# Production
npm run build
npm run start:prod
```

Server sẽ chạy tại: `http://localhost:3000`
Swagger API docs tại: `http://localhost:3000/api`

### 5.3 Cài Đặt Mobile (Flutter)

**Bước 1 – Cài dependencies:**
```bash
cd mobile
flutter pub get
```

**Bước 2 – Cấu hình API endpoint:**

Tìm file cấu hình API (thường là `lib/core/config/api_config.dart`) và cập nhật:
```dart
// Khi chạy trên emulator Android, dùng 10.0.2.2 thay cho localhost
const String baseUrl = 'http://10.0.2.2:3000';

// Khi chạy trên thiết bị thật, dùng IP máy tính
// const String baseUrl = 'http://192.168.1.x:3000';
```

**Bước 3 – Cấu hình Google Sign-In:**

Thêm `google-services.json` vào thư mục `android/app/` (tải từ Firebase Console hoặc Google Cloud Console).

**Bước 4 – Chạy ứng dụng:**
```bash
flutter run
```

### 5.4 Lưu Ý Quan Trọng Khi Triển Khai

> [!CAUTION]
> **Bảo mật JWT:** Không bao giờ commit `JWT_SECRET` và `JWT_REFRESH_SECRET` lên Git. Dùng chuỗi ngẫu nhiên dài ít nhất 64 ký tự trong production.

> [!WARNING]
> **Gemini API Key:** File `.env` đã được thêm vào `.gitignore`. Kiểm tra lại trước khi push code. Nếu key bị lộ, revoke ngay tại [Google AI Studio](https://aistudio.google.com/).

> [!WARNING]
> **Race Condition Slot:** Logic `setTimeout(5 phút)` để hủy appointment dùng JavaScript timer thuần, **không tồn tại khi server restart**. Trong production nên dùng job queue (Bull/BullMQ) để đảm bảo độ tin cậy.

> [!NOTE]
> **Google OAuth Mobile:** Cần `serverClientId` (Web Client ID) trong Flutter để lấy được `id_token`. Android Client ID dùng cho việc hiển thị dialog chọn tài khoản. Phải cấu hình đúng cả hai trong Google Cloud Console.

> [!NOTE]
> **BigInt trong NestJS:** Prisma trả về `BigInt` cho các cột `id`. Khi serialize sang JSON, cần convert sang `string` (đã có hàm `toNumberId()` hoặc `.toString()` trong service). Không dùng `JSON.stringify` trực tiếp với BigInt.

> [!TIP]
> **Kiểm tra Gemini API:** Chạy lệnh curl để test trước khi chạy toàn bộ app:
> ```bash
> curl -X POST http://localhost:3000/ai/triage \
>   -H "Authorization: Bearer <your_jwt>" \
>   -H "Content-Type: application/json" \
>   -d '{"symptoms": "đau đầu, sốt cao, mệt mỏi"}'
> ```

### 5.5 Tóm Tắt Luồng Xác Thực Token

```
1. Đăng nhập  → nhận access_token (15 phút) + refresh_token (7 ngày)
2. Mỗi API call → gửi: Authorization: Bearer <access_token>
3. Khi access_token hết hạn (lỗi 401):
   → Gọi POST /auth/refresh với refresh_token
   → Nhận cặp token mới
   → Retry request ban đầu
4. Khi refresh_token hết hạn → bắt buộc đăng nhập lại
```

---

*Tài liệu được tạo tự động từ mã nguồn dự án `clinic-ai-booking` – phiên bản 2026-05-21*
