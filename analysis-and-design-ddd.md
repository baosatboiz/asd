# Phân tích và Thiết kế — Domain-Driven Design (DDD)

> **Thay thế cho**: [`analysis-and-design.md`](analysis-and-design.md) (phương pháp SOA/Erl).
> Chọn **một** trong hai phương pháp. Dùng phương pháp này nếu team muốn khám phá ranh giới service thông qua domain event thay vì phân tích process.

**Tài liệu tham khảo:**
1. *Domain-Driven Design: Tackling Complexity in the Heart of Software* — Eric Evans
2. *Microservices Patterns: With Examples in Java* — Chris Richardson
3. *Bài tập — Phát triển phần mềm hướng dịch vụ* — Hung Dang (có bản tiếng Việt)

---

## Phần 1 — Khám phá Domain

### 1.1 Business Process

Mô tả hoặc sơ đồ hóa business process cấp cao cần được tự động hóa.

- **Domain**: Thương mại điện tử
- **Business Process**: Onboarding tài khoản, quản lý product catalog, và order-payment orchestration
- **Các actor**: Guest user, registered user, authentication service, product service, order service, inventory service, payment service, workflow worker, Camunda engine
- **Phạm vi**: Đăng ký người dùng; đăng nhập/đăng xuất; xem thông tin profile; duyệt product catalog công khai; tạo order; reserve/confirm/release inventory; khởi tạo payment và correlate kết quả; chuyển trạng thái order dựa trên kết quả payment

**Process Diagram:**

```mermaid
flowchart TD
    G[Guest User] --> R[Đăng ký tài khoản]
    R --> U[Registered User]

    subgraph IAM[Identity & Access Context]
        R
        LG[Đăng nhập và phát hành JWT]
        LO[Đăng xuất và blacklist token]
    end

    U --> LG
    U --> LO

    subgraph CAT[Catalog Context]
        BR[Duyệt product catalog]
    end

    LG --> BR

    BR --> CO[Tạo order]

    subgraph CHECKOUT[Checkout Saga Context]
        SP[Khởi động Saga]
        RS[Reserve Inventory]
        PI[Initiate Payment]
        PS[Nhận kết quả Payment]
        GW{Payment thành công?}
        CF[Confirm Inventory]
        RL[Release Inventory]
        US[Cập nhật trạng thái Order]
    end

    CO --> SP --> RS --> PI --> PS --> GW
    GW -->|Có| CF --> US
    GW -->|Không / Timeout| RL --> US
```

### 1.2 Các hệ thống hiện tại

| Tên hệ thống | Loại | Vai trò hiện tại | Phương thức tương tác |
|---|---|---|---|
| Không có | N/A | Quy trình hiện tại hoàn toàn chưa được tự động hóa. | N/A |

### 1.3 Non-Functional Requirements

| Requirement | Mô tả |
|---|---|
| Performance | P95 read latency dưới 300 ms cho product listing ở tải bình thường |
| Security | JWT bearer authentication, token invalidation khi logout, và service-to-service protection cho internal endpoint |
| Scalability | Product read traffic scale ngang; authentication service và catalog service deploy độc lập |
| Availability | Core API nhắm đến 99.9% uptime với independent deployment và horizontal scaling |
| Data Consistency | Checkout flow dùng Saga orchestration với compensating transaction — không dùng distributed transaction |
| Idempotency | Các thao tác reserve/confirm/release inventory phải idempotent thông qua `orderId` key |
| Async Payment | Payment confirmation là bất đồng bộ — saga tiếp tục thông qua message correlation |

---

## Phần 2 — Strategic Domain-Driven Design

### 2.1 Event Storming — Domain Events

Liệt kê các Domain Event theo thứ tự thời gian xảy ra trong business process.
Quy tắc đặt tên: dùng thì quá khứ (ví dụ: `OrderPlaced`, `PaymentReceived`).

| # | Domain Event | Được trigger bởi | Mô tả |
|---|---|---|---|
| 1 | UserRegistrationRequested | RegisterAccount | Guest gửi username, password và email |
| 2 | UserRegistered | RegisterAccount | User aggregate mới được tạo với trạng thái ACTIVE |
| 3 | UserLoginRequested | Login | Credential được gửi để xác thực |
| 4 | UserAuthenticated | Login | Access token và refresh token được phát hành |
| 5 | UserLoggedOut | Logout | Token hiện tại bị invalidate/blacklist |
| 6 | ProductQueried | QueryProducts / QueryProductDetail | User yêu cầu danh sách hoặc chi tiết sản phẩm |
| 7 | OrderCreated | CreateOrder | Customer gửi order với danh sách item |
| 8 | CheckoutSagaStarted | StartCheckoutSaga | Process instance được khởi tạo cho distributed checkout workflow |
| 9 | InventoryReserved | ReserveInventory | Số lượng yêu cầu được chuyển sang reserved inventory |
| 10 | InventoryReservationFailed | ReserveInventory | Reserve thất bại do không đủ hàng hoặc conflict |
| 11 | PaymentResultReceived | CorrelatePaymentResult | Tín hiệu success/failure được correlate với process instance |
| 12 | InventoryConfirmed | ConfirmInventory | Reserved inventory được confirm là xuất hàng chính thức |
| 13 | InventoryReleased | ReleaseInventory | Reserved inventory được hoàn trả về available inventory |
| 14 | OrderConfirmed | UpdateOrderStatus | Order chuyển sang trạng thái `confirmed` |
| 15 | OrderPaymentFailed | UpdateOrderStatus | Order chuyển sang `payment_failed` sau compensating transaction |
| 16 | PaymentInitiated | InitiatePayment | Payment record được tạo với trạng thái PENDING |
| 17 | PaymentSucceeded | MockResultCallback | Payment service nhận callback thành công |
| 18 | PaymentFailed | MockResultCallback | Payment service nhận callback thất bại |
| 19 | PaymentCorrelated | CorrelatePaymentResult | Camunda nhận message để tiếp tục saga |

### 2.2 Commands và Actors

Command nào trigger các domain event đó, và ai là người phát ra chúng?

| Command | Actor | Domain Event(s) được trigger |
|---|---|---|
| RegisterAccount | Guest user | UserRegistrationRequested, UserRegistered |
| Login | User | UserLoginRequested, UserAuthenticated |
| Logout | User | UserLoggedOut |
| GetMyInfo | User | _(đọc trực tiếp từ read-side, không tạo event)_ |
| QueryProducts | Guest / Registered user | ProductQueried |
| QueryProductDetail | Guest / Registered user | ProductQueried |
| CreateOrder | Registered user | OrderCreated |
| StartCheckoutSaga | Order service | CheckoutSagaStarted |
| ReserveInventory | Workflow worker | InventoryReserved hoặc InventoryReservationFailed |
| CorrelatePaymentResult | Payment adapter / client | PaymentResultReceived |
| InitiatePayment | Workflow worker | PaymentInitiated |
| MockPaymentResult | Webhook / client | PaymentSucceeded hoặc PaymentFailed |
| CorrelatePaymentResult | Payment service | PaymentCorrelated |
| ConfirmInventory | Workflow worker | InventoryConfirmed |
| ReleaseInventory | Workflow worker | InventoryReleased |
| UpdateOrderStatus | Workflow worker | OrderConfirmed, OrderPaymentFailed |

### 2.3 Aggregates

Nhóm các command và event liên quan quanh các business entity (aggregate) mà chúng tác động lên.

| Aggregate | Commands | Domain Events | Owned Data |
|---|---|---|---|
| UserAccount | RegisterAccount, Login, GetMyInfo | UserRegistered, UserAuthenticated | userId, username, email, passwordHash, status, roles |
| SessionToken | Login, Logout | UserAuthenticated, UserLoggedOut | jti, subjectUserId, issueTime, expiryTime, blacklistStatus |
| Product | QueryProducts, QueryProductDetail | ProductQueried | productId, name, description, price, stock, categoryId, images, isDeleted |
| Category | QueryProducts | CategoryReferenced | categoryId, categoryName |
| Order | CreateOrder, UpdateOrderStatus, CancelOrder | OrderCreated, OrderConfirmed, OrderPaymentFailed | orderId, userId, status, totalAmount, createdAt, updatedAt |
| OrderItem | CreateOrder | OrderCreated | orderId, productId, quantity, price |
| OrderEvent | UpdateOrderStatus | OrderConfirmed, OrderPaymentFailed | eventId, orderId, eventType, description, createdAt |
| InventoryItem | ReserveInventory, ConfirmInventory, ReleaseInventory | InventoryReserved, InventoryConfirmed, InventoryReleased | productId, availableStock, reservedStock, version |
| InventoryReservation | ReserveInventory, ConfirmInventory, ReleaseInventory | InventoryReserved, InventoryReservationFailed, InventoryConfirmed, InventoryReleased | reservationId, orderId, status, reservedAt, confirmedAt, releasedAt |
| InventoryHistory | ReserveInventory, ConfirmInventory, ReleaseInventory | InventoryReserved, InventoryConfirmed, InventoryReleased | historyId, productId, eventType, delta, source, idempotencyKey |
| Payment | InitiatePayment, MockPaymentResult | PaymentInitiated, PaymentSucceeded, PaymentFailed | paymentId, orderId, amount, status, paymentMethod, transactionId |

### 2.4 Bounded Contexts

Gom các aggregate thuộc cùng một business context lại với nhau. Mỗi Bounded Context là một service tiềm năng.

| Bounded Context | Aggregates | Trách nhiệm |
|---|---|---|
| Identity & Access Context | UserAccount, SessionToken | Vòng đời người dùng, authentication, và authorization boundary |
| Catalog Context | Product, Category | Quản lý thông tin sản phẩm và truy vấn catalog công khai |
| Order Management Context | Order, OrderItem, OrderEvent | Vòng đời order, state transition, và order timeline |
| Inventory Management Context | InventoryItem, InventoryReservation, InventoryHistory | Reserve inventory và compensating inventory change an toàn |
| Payment Management Context | Payment | Quản lý payment record, theo dõi trạng thái, và tích hợp gateway/webhook |
| Saga Orchestration Context | Process state trong Camunda | Điều phối các bước checkout và compensating path |

### 2.5 Context Map

Thể hiện mối quan hệ giữa các Bounded Context.

```mermaid
graph LR
    IAM["Identity & Access"] -- "OHS + Published Language (JWT claims)" --> CATALOG["Catalog"]
    CATALOG -- "Conformist to IAM auth contract" --> IAM
    IAM -- "Token-based user identity" --> ORDERCTX["Order Management"]
    ORDERCTX -- "Reserve-Confirm-Release (Customer/Supplier)" --> INV["Inventory Management"]
    ORDERCTX -- "Initiate-Result (Customer/Supplier)" --> PAY["Payment Management"]
    ORCH["Saga Orchestration"] -- "Orchestrates process tasks" --> ORDERCTX
    ORCH -- "Orchestrates process tasks" --> INV
    ORCH -- "Orchestrates process tasks" --> PAY
```

**Các kiểu quan hệ:** Upstream/Downstream, Customer/Supplier, Conformist, Anti-Corruption Layer (ACL), Shared Kernel, Open Host Service (OHS), Published Language.

| Upstream | Downstream | Kiểu quan hệ |
|---|---|---|
| Identity & Access | Catalog | Open Host Service + Published Language |
| Identity & Access | API Gateway (edge layer) | Upstream auth provider để validate token |
| Identity & Access | Order Management | Open Host Service + Published Language |
| Order Management | Inventory Management | Customer/Supplier |
| Saga Orchestration | Order Management | Upstream/Downstream orchestration contract |
| Saga Orchestration | Inventory Management | Upstream/Downstream orchestration contract |
| Order Management | Payment Management | Customer/Supplier |
| Saga Orchestration | Payment Management | Upstream/Downstream orchestration contract |

---

## Phần 3 — Service-Oriented Design

### 3.1 Service Contract

Thiết kế service contract cho từng Bounded Context.
Các OpenAPI specification đầy đủ:
- [`docs/api-specs/identity-service.yaml`](api-specs/identity-service.yaml)
- [`docs/api-specs/product-service.yaml`](api-specs/product-service.yaml)
- `docs/api-specs/order-service.yaml` _(bổ sung)_
- `docs/api-specs/inventory-service.yaml` _(bổ sung)_
- `docs/api-specs/payment-service.yaml` _(bổ sung)_

**Identity Service:**

| Endpoint | Method | Media Type | Response Codes |
|---|---|---|---|
| /api/v1/auth/register | POST | application/json | 201, 409 |
| /api/v1/auth/login | POST | application/json | 200, 401, 403 |
| /api/v1/auth/logout | POST | application/json | 200, 401 |
| /api/v1/users/my-info | GET | application/json | 200, 401 |

**Product Service:**

| Endpoint | Method | Media Type | Response Codes |
|---|---|---|---|
| /api/v1/products | GET | application/json | 200 |
| /api/v1/products/{productId} | GET | application/json | 200, 404 |

> Phạm vi bài tập hiện tại không bao gồm admin write endpoint (POST/PUT/DELETE cho product management).

**Order Service _(bổ sung)_:**

| Endpoint | Method | Media Type | Response Codes |
|---|---|---|---|
| /api/v1/orders | POST | application/json | 202, 400 |
| /api/v1/orders/{orderId} | GET | application/json | 200, 404 |
| /api/v1/orders/user/{userId} | GET | application/json | 200 |
| /api/v1/orders/{orderId}/timeline | GET | application/json | 200, 404 |
| /api/v1/orders/{orderId}/status | PATCH | application/json | 200, 404 |
| /api/v1/orders/{orderId}/compensation | POST | application/json | 200, 404 |

**Inventory Service _(bổ sung)_:**

| Endpoint | Method | Media Type | Response Codes |
|---|---|---|---|
| /api/v1/inventory/{productId} | GET | application/json | 200, 404 |
| /api/v1/inventory/reserve | POST | application/json | 200, 409 |
| /api/v1/inventory/confirm | POST | application/json | 200, 404 |
| /api/v1/inventory/release | POST | application/json | 200, 404 |

> Bài tập hiện tại tập trung vào 4 endpoint phục vụ checkout saga flow. Các endpoint quản lý tồn kho đặc quyền (stock-in, low-stock, history) là phần thiết kế bổ sung ngoài phạm vi.

**Payment Service _(bổ sung)_:**

| Endpoint | Method | Media Type | Response Codes |
|---|---|---|---|
| /api/v1/payments/initiate | POST | application/json | 201, 400, 404, 409 |
| /api/v1/payments/{paymentId} | GET | application/json | 200, 404 |
| /api/v1/payments/order/{orderId} | GET | application/json | 200, 404 |
| /api/v1/payments/mock-result | POST | application/json | 200, 400 |

### 3.2 Service Logic

Luồng xử lý nội bộ của từng service.

**Identity Service:**

```mermaid
flowchart TD
    A[Nhận authentication request] --> B{Input hợp lệ?}
    B -->|Không| C[Trả về 4xx với business error code]
    B -->|Có| D{Loại command}
    D -->|Register| E[Tạo user với trạng thái ACTIVE]
    D -->|Login| F[Xác thực credential và phát hành JWT]
    D -->|Logout| G[Blacklist token JTI]
    D -->|GetMyInfo| H[Resolve user từ token claims]
    E --> I[Trả về ApiResponse]
    F --> I
    G --> I
    H --> I
```

**Product Service:**

```mermaid
flowchart TD
    A[Nhận product query request] --> B{Loại query}
    B -->|Listing| C[Lấy danh sách product với filter và pagination]
    B -->|Detail| D[Lấy product theo productId]
    C --> E[Trả về ApiResponse]
    D --> E
```

**Order Service _(bổ sung)_:**

```mermaid
flowchart TD
    A[Nhận request tạo order] --> B{Payload hợp lệ?}
    B -->|Không| C[Trả về 4xx]
    B -->|Có| D[Lưu order với status = PENDING]
    D --> E[Khởi động Camunda Saga với businessKey = orderId]
    E --> F[Trả về 202 Accepted]

    G[Nhận status update từ Saga] --> H{State transition hợp lệ?}
    H -->|Không| I[Trả về 404]
    H -->|Có| J[Cập nhật order status và append order event]
    J --> K[Trả về order đã cập nhật]

    L[Nhận compensation request] --> M[Chuyển order sang CANCELLED]
    M --> N[Trả về 200]
```

**Inventory Service _(bổ sung)_:**

```mermaid
flowchart TD
    A[Nhận lệnh reserve / confirm / release] --> B{Có orderId?}
    B -->|Không| C[Trả về 400]
    B -->|Có| D{Lookup orderId trong reservation table}
    D -->|Đã xử lý trước đó| E[Trả về kết quả cũ - idempotent]
    D -->|Chưa có| F{Loại thao tác}

    F -->|Reserve| G[Kiểm tra available stock với atomic update]
    G -->|Không đủ| H[Trả về 409]
    G -->|Đủ| I[Chuyển available stock sang reserved]
    I --> J[Ghi reservation record theo orderId]

    F -->|Confirm| K[Kiểm tra reservation ở trạng thái RESERVED]
    K --> L[Commit reservation thành xuất hàng]

    F -->|Release| M[Kiểm tra reservation ở trạng thái RESERVED]
    M --> N[Hoàn trả reservation về available stock]

    J --> O[Trả về kết quả]
    L --> O
    N --> O
```

- Dùng **atomic update** để tránh race condition khi có nhiều request reserve đồng thời.
- Tra cứu theo `orderId` trong bảng `inventory_reservation` để đảm bảo **idempotency**.
- Stock không bao giờ được phép giảm xuống dưới 0.

**Payment Service _(bổ sung)_:**

```mermaid
sequenceDiagram
    participant C as Camunda Engine
    participant W as Workflow Worker
    participant O as Order Service
    participant P as Payment Service
    participant U as Webhook / Client

    C->>W: Fetch External Task (initiate-payment)
    W->>P: POST /api/v1/payments/initiate (orderId, amount)
    P-->>W: 201 Created (Payment: PENDING)
    W->>O: PATCH /internal/orders/{id}/status → WAITING_PAYMENT
    W->>C: Complete Task
    Note over C,W: Camunda chờ tại Intermediate Message Catch Event (payment-result)

    U->>P: POST /api/v1/payments/mock-result (orderId, isSuccess)
    P->>P: DB Update — Payment status = SUCCESS / FAILED

    alt Payment thành công
        P->>C: POST /engine-rest/message (messageName: payment-result, var: PAYMENT_SUCCESS)
    else Payment thất bại
        P->>C: POST /engine-rest/message (messageName: payment-result, var: PAYMENT_FAILED)
    end
    C-->>P: 200 OK (correlation thành công)
    P-->>U: 200 OK (PaymentResponse)
```