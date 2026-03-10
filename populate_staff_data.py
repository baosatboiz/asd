import requests
import json

print("Populating Staff Dashboard test data...")

# Update some books to have low stock (< 5)
low_stock_books = [
    {"id": 1, "stock": 3},
    {"id": 2, "stock": 2},
    {"id": 4, "stock": 4}
]

print("\n1. Updating books to low stock...")
for book in low_stock_books:
    response = requests.patch(
        f"http://localhost:8004/books/{book['id']}/",
        json={"stock": book['stock']}
    )
    if response.status_code == 200:
        print(f"  ✓ Book {book['id']} stock updated to {book['stock']}")

# Create pending orders (without auto-payment)
pending_orders = [
    {
        "customer_id": 1,
        "total_price": "45.99",
        "shipping_address": "Campus Dorm B, Room 101"
    },
    {
        "customer_id": 2,
        "total_price": "89.50",
        "shipping_address": "Student Housing, Block C"
    },
    {
        "customer_id": 3,
        "total_price": "125.00",
        "shipping_address": "Faculty Apartments, Unit 5A"
    }
]

print("\n2. Creating pending orders...")
created_orders = []
for order in pending_orders:
    response = requests.post(
        "http://localhost:8006/orders/",
        json=order
    )
    if response.status_code == 201:
        order_data = response.json()
        created_orders.append(order_data)
        print(f"  ✓ Order {order_data['id']} created (status: {order_data['status']})")

# Now update orders back to pending if they were auto-paid
print("\n3. Checking if orders need status update...")
for order_data in created_orders:
    if order_data.get('status') != 'pending':
        response = requests.patch(
            f"http://localhost:8006/orders/{order_data['id']}/",
            json={"status": "pending"}
        )
        if response.status_code == 200:
            print(f"  ✓ Order {order_data['id']} status changed to pending")
        else:
            print(f"  ✗ Failed to update Order {order_data['id']}: {response.status_code}")

print("\n✅ Staff Dashboard now has:")
print(f"   - {len(low_stock_books)} books with low stock (< 5)")
print(f"   - {len(created_orders)} pending orders ready to ship")
print("\nVisit http://localhost:8011/staff/dashboard/ (with Staff identity)")
