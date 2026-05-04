# Sequence Diagram: Chức năng Dự đoán Bệnh (AI Triage)

Dưới đây là Sequence Diagram chi tiết cho chức năng Trợ lý Y tế AI. Sơ đồ mô tả quy trình tổng hợp dữ liệu từ người dùng, gọi API hệ thống, tương tác với dịch vụ AI của Google (Gemini API) để phân tích, xử lý kết quả, lưu lịch sử vào Database và trả về giao diện.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    
    participant AiScreen as AiTriageScreen
    
    participant AiCtrl as AiController
    
    participant AiSvc as AiService
    
    participant GeminiAPI as Google Gemini API
    
    participant DBTriage as Table: ai_triage_sessions

    User->>AiScreen: Mở màn hình Trợ lý Y tế AI
    User->>AiScreen: Chọn triệu chứng, vị trí, mức độ đau, thời gian...
    User->>AiScreen: Nhập thêm chi tiết triệu chứng & Nhấn "Phân tích"
    
    %% Xử lý tại Frontend
    AiScreen->>AiScreen: Tổng hợp dữ liệu thành văn bản (Build Symptoms Payload)
    AiScreen->>AiScreen: Kiểm tra tính hợp lệ (Validate input)
    
    %% Gọi API Backend
    AiScreen->>AiCtrl: Gửi request POST /ai/triage { symptoms }
    
    %% Chuyển qua Service
    AiCtrl->>AiSvc: Gọi hàm triageSymptoms(userId, symptoms)
    
    %% Logic chuẩn bị gọi Gemini
    AiSvc->>AiSvc: Kiểm tra GEMINI_API_KEY
    AiSvc->>AiSvc: Xây dựng Prompt (System Prompt + User Symptoms)
    
    %% Gọi ra External API
    Note over AiSvc,GeminiAPI: Quá trình AI suy luận (được giới hạn Timeout)
    AiSvc->>GeminiAPI: Gọi model.generateContent() qua SDK
    GeminiAPI-->>AiSvc: Trả về văn bản thô (Raw Text chứa Markdown JSON)
    
    %% Xử lý kết quả AI
    AiSvc->>AiSvc: Hàm parseAndValidateTriageJson()
    Note right of AiSvc: Bóc tách markdown, Parse JSON, Validate cấu trúc<br>(urgency, specialty, reasoning)
    
    %% Lưu lịch sử
    AiSvc->>DBTriage: INSERT bản ghi (Lưu lịch sử phiên Triage)
    DBTriage-->>AiSvc: Lưu thành công
    
    %% Trả kết quả
    AiSvc-->>AiCtrl: Trả đối tượng TriageResultDto
    AiCtrl-->>AiScreen: Phản hồi HTTP 200 OK (JSON)
    
    %% Hiển thị và điều hướng
    AiScreen-->>User: Hiển thị kết quả: Mức độ, Chuyên khoa, Giải thích
    User->>AiScreen: Nhấn nút "Tìm Bác sĩ ngay"
    AiScreen->>AiScreen: Điều hướng về màn hình Home (kèm bộ lọc chuyên khoa)
```
