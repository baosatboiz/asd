import json
import random
import sys
from decimal import Decimal

import requests

BASE_URLS = {
    "staff": "http://localhost:8000",
    "manager": "http://localhost:8001",
    "customer": "http://localhost:8002",
    "catalog": "http://localhost:8003",
    "book": "http://localhost:8004",
    "cart": "http://localhost:8005",
    "order": "http://localhost:8006",
    "ship": "http://localhost:8007",
    "pay": "http://localhost:8008",
    "comment_rate": "http://localhost:8009",
    "recommender": "http://localhost:8010",
    "api_gateway": "http://localhost:8011",
}

TIMEOUT = 10


def endpoint(service_key, path):
    base = BASE_URLS[service_key].rstrip("/")
    clean_path = path.strip("/")
    return f"{base}/{clean_path}/"


def request_api(method, url, payload=None):
    try:
        response = requests.request(method=method, url=url, json=payload, timeout=TIMEOUT)
    except requests.RequestException as exc:
        print(f"[FAIL] {method} {url} -> Request error: {exc}")
        return None

    ok = 200 <= response.status_code < 300
    label = "OK" if ok else "FAIL"

    body = None
    content_type = response.headers.get("Content-Type", "")
    try:
        body = response.json()
    except ValueError:
        body = response.text

    pretty = json.dumps(body, indent=2) if isinstance(body, (dict, list)) else str(body)
    print(f"[{label}] {method} {url} -> {response.status_code}")
    if payload is not None:
        print(f"  payload: {json.dumps(payload)}")
    if "text/html" in content_type.lower():
        print("  warning: received HTML response (likely Django debug/error page).")
    print(f"  response: {pretty}")

    if not ok:
        return None
    return body


def create_books():
    print("\n=== Step 1: Create sample books (book-service:8004) ===")
    samples = [
        {
            "title": "Distributed Systems for Learners",
            "author": "Anita Bose",
            "isbn": "978-0-0001-1001-1",
            "price": "42.50",
            "stock": 25,
            "category_id": 1,
        },
        {
            "title": "Practical Django Microservices",
            "author": "Carlos Nguyen",
            "isbn": "978-0-0001-1002-8",
            "price": "55.00",
            "stock": 18,
            "category_id": 2,
        },
        {
            "title": "API Design in Real Projects",
            "author": "Leila Haddad",
            "isbn": "978-0-0001-1003-5",
            "price": "36.75",
            "stock": 30,
            "category_id": 3,
        },
        {
            "title": "Cloud Native Patterns",
            "author": "Martin Alvarez",
            "isbn": "978-0-0001-1004-2",
            "price": "61.20",
            "stock": 12,
            "category_id": 4,
        },
        {
            "title": "Data Modeling Essentials",
            "author": "Sara Ibrahim",
            "isbn": "978-0-0001-1005-9",
            "price": "29.99",
            "stock": 40,
            "category_id": 5,
        },
    ]

    created = []
    url = endpoint("book", "books")
    for item in samples:
        result = request_api("POST", url, item)
        if isinstance(result, dict) and result.get("id"):
            created.append(result)

    print(f"Created {len(created)} books.")
    return created


def create_managers_and_staff():
    print("\n=== Step 2: Create managers (8001) and staff (8000) ===")
    managers = [
        {"full_name": "Dr. Amal Rahman", "email": "amal.rahman@bookstore.edu", "department": "Operations"},
        {"full_name": "Victor Stein", "email": "victor.stein@bookstore.edu", "department": "Academic Sales"},
    ]
    staff_members = [
        {"full_name": "Noah Kim", "email": "noah.kim@bookstore.edu", "role": "Inventory Specialist", "is_active": True},
        {"full_name": "Maya Torres", "email": "maya.torres@bookstore.edu", "role": "Support Associate", "is_active": True},
        {"full_name": "Rami Zaki", "email": "rami.zaki@bookstore.edu", "role": "Fulfillment Clerk", "is_active": True},
    ]

    created_managers = []
    created_staff = []

    for manager in managers:
        result = request_api("POST", endpoint("manager", "managers"), manager)
        if isinstance(result, dict) and result.get("id"):
            created_managers.append(result)

    for staff in staff_members:
        result = request_api("POST", endpoint("staff", "staff"), staff)
        if isinstance(result, dict) and result.get("id"):
            created_staff.append(result)

    print(f"Created {len(created_managers)} managers and {len(created_staff)} staff members.")
    return created_managers, created_staff


def create_customers():
    print("\n=== Step 3: Create customers (8002, cart auto-create expected) ===")
    customers = [
        {
            "full_name": "Aisha Farouk",
            "email": "aisha.farouk@student.edu",
            "phone": "+20-100-111-2222",
            "address": "Dorm A, Nile University Campus",
        },
        {
            "full_name": "Daniel Okeke",
            "email": "daniel.okeke@student.edu",
            "phone": "+234-803-456-7890",
            "address": "Maple Street 14, Faculty Housing",
        },
        {
            "full_name": "Elena Petrov",
            "email": "elena.petrov@student.edu",
            "phone": "+7-921-555-0198",
            "address": "Science Block Residence, Room 307",
        },
    ]

    created = []
    for customer in customers:
        result = request_api("POST", endpoint("customer", "customers"), customer)
        if isinstance(result, dict) and result.get("id"):
            created.append(result)

    print(f"Created {len(created)} customers.")
    return created


def get_or_find_cart_id(customer_obj):
    cart_id = customer_obj.get("cart_id")
    if cart_id:
        return cart_id

    customer_id = customer_obj.get("id")
    if not customer_id:
        return None

    carts = request_api("GET", endpoint("cart", "carts"))
    if not isinstance(carts, list):
        return None

    for cart in carts:
        if cart.get("customer_id") == customer_id:
            return cart.get("id")
    return None


def add_items_to_carts(customers, books):
    print("\n=== Step 4: Add book items to carts (8005) ===")
    if not customers or not books:
        print("[WARN] Skipped cart item seeding because customers or books are missing.")
        return []

    seeded_items = []
    for customer in customers:
        cart_id = get_or_find_cart_id(customer)
        if not cart_id:
            print(f"[FAIL] Could not find cart for customer_id={customer.get('id')}")
            continue

        picks = random.sample(books, k=min(2, len(books)))
        for pick in picks:
            quantity = random.randint(1, 3)
            payload = {"book_id": pick["id"], "quantity": quantity}
            result = request_api("POST", endpoint("cart", f"carts/{cart_id}/add-item"), payload)
            if isinstance(result, dict) and result.get("id"):
                seeded_items.append(result)

    print(f"Added {len(seeded_items)} cart items.")
    return seeded_items


def create_orders(customers, books):
    print("\n=== Step 5: Create orders (8006, triggers pay+ship) ===")
    if not customers or not books:
        print("[WARN] Skipped order seeding because customers or books are missing.")
        return []

    book_prices = {book["id"]: Decimal(str(book["price"])) for book in books if "id" in book and "price" in book}
    created_orders = []

    for customer in customers:
        chosen_books = random.sample(list(book_prices.items()), k=min(2, len(book_prices)))
        total_price = sum(price for _, price in chosen_books)
        payload = {
            "customer_id": customer["id"],
            "total_price": str(total_price.quantize(Decimal("0.01"))),
            "shipping_address": customer.get("address", "Default Campus Address"),
        }
        result = request_api("POST", endpoint("order", "orders"), payload)
        if isinstance(result, dict) and result.get("id"):
            created_orders.append(result)

    print(f"Created {len(created_orders)} orders.")
    return created_orders


def verify_payments_and_shipments():
    print("\n=== Verification: Payments (8008) and Shipments (8007) ===")
    payments = request_api("GET", endpoint("pay", "payments"))
    shipments = request_api("GET", endpoint("ship", "shipments"))

    pay_count = len(payments) if isinstance(payments, list) else 0
    ship_count = len(shipments) if isinstance(shipments, list) else 0
    print(f"Verification summary: payments={pay_count}, shipments={ship_count}")


def main():
    print("Starting seed_all.py ...")
    books = create_books()
    create_managers_and_staff()
    customers = create_customers()
    add_items_to_carts(customers, books)
    create_orders(customers, books)
    verify_payments_and_shipments()
    print("\nSeeding completed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSeeding interrupted by user.")
        sys.exit(1)
