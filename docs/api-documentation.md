# Bookstore Microservice API Documentation

Base URL pattern (local docker-compose): `http://localhost:<host-port>/`

## Common Notes

- Services using DRF `ModelViewSet` expose standard REST endpoints:
- `GET /resource/` list
- `POST /resource/` create
- `GET /resource/{id}/` retrieve
- `PUT /resource/{id}/` full update
- `PATCH /resource/{id}/` partial update
- `DELETE /resource/{id}/` delete
- API Gateway uses template-rendering routes and form posts.

---

## 1) Staff Service (`http://localhost:8000`)

Resource: `/staff/`

### Entity Fields
- `id` (int, auto)
- `full_name` (string, max 120)
- `email` (string, unique)
- `role` (string, max 80)
- `is_active` (bool, default true)
- `created_at` (datetime)

---

## 2) Manager Service (`http://localhost:8001`)

Resource: `/managers/`

### Entity Fields
- `id` (int, auto)
- `full_name` (string, max 120)
- `email` (string, unique)
- `department` (string, max 120)
- `created_at` (datetime)

---

## 3) Customer Service (`http://localhost:8002`)

Resource: `/customers/`

### Entity Fields
- `id` (int, auto)
- `full_name` (string, max 120)
- `email` (string, unique)
- `phone` (string, optional)
- `address` (string, optional)
- `cart_id` (int, nullable)
- `created_at` (datetime)

### Special Behavior
- `POST /customers/` also tries to auto-create cart in cart-service (`POST /carts/`).
- On cart creation issue, response may include `cart_warning`.

### Example Create Request
```json
{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+1-555-0100",
  "address": "12 Market Street"
}
```

---

## 4) Catalog Service (`http://localhost:8003`)

Resource: `/categories/`

### Entity Fields
- `id` (int, auto)
- `name` (string, unique)
- `description` (string, optional)

---

## 5) Book Service (`http://localhost:8004`)

Resource: `/books/`

### Entity Fields
- `id` (int, auto)
- `title` (string, max 255)
- `author` (string, max 180)
- `isbn` (string, unique)
- `price` (decimal)
- `stock` (int, unsigned)
- `category_id` (int, nullable)
- `created_at` (datetime)

### Example Create Request
```json
{
  "title": "The Pragmatic Programmer",
  "author": "Andrew Hunt",
  "isbn": "978-0201616224",
  "price": "42.50",
  "stock": 10,
  "category_id": 1
}
```

---

## 6) Cart Service (`http://localhost:8005`)

Resource: `/carts/`

### Cart Fields
- `id` (int, auto)
- `customer_id` (int, unique)
- `is_active` (bool)
- `created_at` (datetime)
- `items` (read-only nested list)

### Cart Item Fields
- `id` (int, auto)
- `cart` (int FK)
- `book_id` (int)
- `quantity` (int)
- `created_at` (datetime)

### Custom Endpoints
- `POST /carts/{id}/add-item/`
- `POST /carts/{id}/clear-items/`

### `POST /carts/{id}/add-item/`
Request body:
```json
{
  "book_id": 4,
  "quantity": 2
}
```
Behavior:
- Validates `book_id` against book-service.
- Creates or increments cart item quantity.

### `POST /carts/{id}/clear-items/`
- Removes all `CartItem` rows for the cart.

---

## 7) Order Service (`http://localhost:8006`)

Resource: `/orders/`

### Entity Fields
- `id` (int, auto)
- `customer_id` (int)
- `total_price` (decimal)
- `status` (`pending|paid|shipped|completed`)
- `shipping_address` (string)
- `created_at` (datetime)

### Special Behavior on Create
`POST /orders/`:
- Creates order record.
- Calls pay-service `POST /payments/`.
- Calls ship-service `POST /shipments/`.
- If payment succeeds, updates order status to `paid`.
- Response includes extra fields: `payment_status`, `shipping_status`, and optional errors.

### Example Create Request
```json
{
  "customer_id": 1,
  "total_price": "89.99",
  "shipping_address": "Customer 1 default address |books:3,7"
}
```

---

## 8) Ship Service (`http://localhost:8007`)

Resource: `/shipments/`

### Entity Fields
- `id` (int, auto)
- `order_id` (int)
- `customer_id` (int)
- `address` (string)
- `status` (`processing|shipped|delivered|failed`)
- `created_at` (datetime)

---

## 9) Pay Service (`http://localhost:8008`)

Resource: `/payments/`

### Entity Fields
- `id` (int, auto)
- `order_id` (int, unique)
- `amount` (decimal)
- `status` (`pending|paid|failed`)
- `paid_at` (datetime)

---

## 10) Comment-Rate Service (`http://localhost:8009`)

Resources:
- `/comments/`
- `/comments-rates/`

Both routes are backed by the same `CommentRateViewSet` and data model.

### Entity Fields
- `id` (int, auto)
- `book_id` (int)
- `customer_id` (int)
- `comment` (string)
- `rating` (int, default 5)
- `created_at` (datetime)

### Special Behavior on Create
- Validates purchase history through order-service `GET /orders/`.
- Accepts review only if the customer purchased the target book.
- Returns `403` with `"You can only review books you have purchased"` when invalid.

### Example Create Request
```json
{
  "book_id": 3,
  "customer_id": 1,
  "rating": 5,
  "comment": "Excellent book"
}
```

---

## 11) Recommender-AI Service (`http://localhost:8010`)

Resource: `/recommendations/`

### Model Fields
- `id` (int, auto)
- `customer_id` (int)
- `recommended_book_id` (int)
- `score` (float)
- `reason` (string)
- `created_at` (datetime)

### Special List Behavior
`GET /recommendations/` dynamically computes recommendations using:
- Successful orders from order-service (`paid|shipped|completed`)
- High ratings (`rating > 4`) from comment-rate service
- Header `X-Actor-Id` to avoid recommending already-owned books

Response items are computed at runtime with fields:
- `id`
- `customer_id`
- `recommended_book_id`
- `score`
- `reason`

---

## 12) API Gateway (`http://localhost:8011`)

The API Gateway serves HTML pages and orchestrates calls to microservices.

### Gateway Routes
- `GET /` Home catalog page
- `POST /switch-identity/` Change active session actor
- `GET /books/{book_id}/` Book details + comments
- `POST /add-to-cart/` Add book to customer cart
- `GET /cart/` Cart detail view
- `POST /checkout/` Create order from cart
- `GET /success/?order_id={id}` Order result page + review options
- `POST /submit-review/` Submit review (customer only)
- `GET /dashboard/` Manager dashboard
- `GET /staff/dashboard/` Staff dashboard
- `POST /staff/mark-shipped/` Mark order as shipped
- `GET /staff/manage-books/` Staff inventory page
- `GET|POST /staff/add-book/` Create book via gateway UI
- `GET|POST /staff/edit-book/{book_id}/` Edit book via gateway UI
- `POST /staff/delete-book/{book_id}/` Delete book via gateway UI
- `GET /aggregate/` Aggregate API payload (customers, orders, payments, comments)

### Headers Used Internally
Gateway forwards actor identity with:
- `X-Actor-Role`
- `X-Actor-Id`

These headers are used for role-aware behavior across services.

---

## Auth and Validation Notes

- Current system is role-switched by session identity in gateway UI, not token-based auth.
- Service-to-service validation is implemented in code paths such as:
- cart-service book existence check
- comment-rate purchase verification
- order-service payment/shipment orchestration

## Error Behavior (Summary)

- Upstream request failures commonly return service-specific messages and 4xx/5xx statuses.
- Gateway UI routes generally redirect with query-string `error=` or `success=` messages.
