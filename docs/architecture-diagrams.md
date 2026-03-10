# Bookstore Microservice Architecture Diagrams

This document provides a focused diagram for each service in the system.

## 1) Staff Service (`staff`, host port `8000`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /staff/]
  B --> C[StaffViewSet]
  C --> D[StaffSerializer]
  D --> E[(Staff DB Table)]
```

## 2) Manager Service (`manager`, host port `8001`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /managers/]
  B --> C[ManagerViewSet]
  C --> D[ManagerSerializer]
  D --> E[(Manager DB Table)]
```

## 3) Customer Service (`customer`, host port `8002`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /customers/]
  B --> C[CustomerViewSet]
  C --> D[CustomerSerializer]
  D --> E[(Customer DB Table)]
  C --> F[POST /carts/ on Cart Service]
  F --> G[(Cart DB Table)]
```

## 4) Catalog Service (`catalog`, host port `8003`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /categories/]
  B --> C[CategoryViewSet]
  C --> D[CategorySerializer]
  D --> E[(Category DB Table)]
```

## 5) Book Service (`book`, host port `8004`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /books/]
  B --> C[BookViewSet]
  C --> D[BookSerializer]
  D --> E[(Book DB Table)]
```

## 6) Cart Service (`cart`, host port `8005`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /carts/]
  B --> C[CartViewSet]
  C --> D[CartSerializer + CartItemSerializer]
  D --> E[(Cart DB Table)]
  D --> F[(CartItem DB Table)]
  C --> G[Validate book_id via Book Service /books/{id}/]
```

## 7) Order Service (`order`, host port `8006`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /orders/]
  B --> C[OrderViewSet]
  C --> D[OrderSerializer]
  D --> E[(Order DB Table)]
  C --> F[POST /payments/ on Pay Service]
  C --> G[POST /shipments/ on Ship Service]
```

## 8) Ship Service (`ship`, host port `8007`)

```mermaid
flowchart LR
  A[Order Service or API Gateway] --> B[DRF Router /shipments/]
  B --> C[ShipmentViewSet]
  C --> D[ShipmentSerializer]
  D --> E[(Shipment DB Table)]
```

## 9) Pay Service (`pay`, host port `8008`)

```mermaid
flowchart LR
  A[Order Service or API Gateway] --> B[DRF Router /payments/]
  B --> C[PaymentViewSet]
  C --> D[PaymentSerializer]
  D --> E[(Payment DB Table)]
```

## 10) Comment-Rate Service (`comment-rate`, host port `8009`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /comments/ and /comments-rates/]
  B --> C[CommentRateViewSet]
  C --> D[CommentRateSerializer]
  D --> E[(CommentRate DB Table)]
  C --> F[GET /orders/ on Order Service]
  F --> C
```

## 11) Recommender-AI Service (`recommender-ai`, host port `8010`)

```mermaid
flowchart LR
  A[Client or API Gateway] --> B[DRF Router /recommendations/]
  B --> C[RecommendationViewSet]
  C --> D[Score Engine in list()]
  D --> E[GET /orders/ on Order Service]
  D --> F[GET /comments-rates/ on Comment-Rate Service]
  C --> G[(Recommendation DB Table)]
```

## 12) API Gateway Service (`api-gateway`, host port `8011`)

```mermaid
flowchart LR
  U[Browser / UI User] --> A[Gateway Django Views]
  A --> B[Templates index/cart/book_detail/success/dashboard/staff/manage_books]
  A --> C[Catalog Service]
  A --> D[Book Service]
  A --> E[Cart Service]
  A --> F[Order Service]
  A --> G[Pay Service]
  A --> H[Ship Service]
  A --> I[Comment-Rate Service]
  A --> J[Customer Service]
  A --> K[Recommender-AI Service]
```

## End-to-End System Overview

```mermaid
flowchart LR
  U[User Browser] --> GW[API Gateway :8011]
  GW --> CAT[Catalog :8003]
  GW --> BOOK[Book :8004]
  GW --> CART[Cart :8005]
  GW --> ORD[Order :8006]
  GW --> PAY[Pay :8008]
  GW --> SHIP[Ship :8007]
  GW --> COM[Comment-Rate :8009]
  GW --> CUS[Customer :8002]
  GW --> REC[Recommender-AI :8010]

  CUS --> CART
  CART --> BOOK
  ORD --> PAY
  ORD --> SHIP
  COM --> ORD
  REC --> ORD
  REC --> COM
```
