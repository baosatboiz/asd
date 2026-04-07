"""
Seed script for clothes service.
Run: python scripts/seed_clothes.py
Make sure the clothes service is running on port 8012.
"""
import requests

BASE_URL = "http://localhost:8012/clothes/"

CLOTHES_DATA = [
    {"name": "Classic White Tee", "brand": "Basics Co.", "size": "S", "color": "White", "price": "19.99", "stock": 50},
    {"name": "Classic White Tee", "brand": "Basics Co.", "size": "M", "color": "White", "price": "19.99", "stock": 40},
    {"name": "Classic White Tee", "brand": "Basics Co.", "size": "L", "color": "White", "price": "19.99", "stock": 30},
    {"name": "Slim Fit Jeans", "brand": "DenimLab", "size": "M", "color": "Blue", "price": "59.99", "stock": 25},
    {"name": "Slim Fit Jeans", "brand": "DenimLab", "size": "L", "color": "Blue", "price": "59.99", "stock": 20},
    {"name": "Slim Fit Jeans", "brand": "DenimLab", "size": "XL", "color": "Black", "price": "64.99", "stock": 15},
    {"name": "Floral Summer Dress", "brand": "SunWear", "size": "S", "color": "Pink", "price": "45.00", "stock": 18},
    {"name": "Floral Summer Dress", "brand": "SunWear", "size": "M", "color": "Pink", "price": "45.00", "stock": 12},
    {"name": "Floral Summer Dress", "brand": "SunWear", "size": "XL", "color": "Yellow", "price": "47.00", "stock": 8},
    {"name": "Wool Overcoat", "brand": "WinterEdge", "size": "M", "color": "Grey", "price": "129.99", "stock": 10},
    {"name": "Wool Overcoat", "brand": "WinterEdge", "size": "L", "color": "Grey", "price": "129.99", "stock": 8},
    {"name": "Wool Overcoat", "brand": "WinterEdge", "size": "XL", "color": "Charcoal", "price": "134.99", "stock": 5},
    {"name": "Athletic Shorts", "brand": "SportZone", "size": "S", "color": "Black", "price": "24.99", "stock": 60},
    {"name": "Athletic Shorts", "brand": "SportZone", "size": "M", "color": "Black", "price": "24.99", "stock": 55},
    {"name": "Athletic Shorts", "brand": "SportZone", "size": "L", "color": "Navy", "price": "24.99", "stock": 45},
    {"name": "Linen Button Shirt", "brand": "UrbanWave", "size": "M", "color": "Beige", "price": "49.99", "stock": 22},
    {"name": "Linen Button Shirt", "brand": "UrbanWave", "size": "L", "color": "Beige", "price": "49.99", "stock": 18},
    {"name": "Linen Button Shirt", "brand": "UrbanWave", "size": "XL", "color": "White", "price": "49.99", "stock": 14},
    {"name": "Graphic Hoodie", "brand": "StreetCore", "size": "M", "color": "Black", "price": "54.99", "stock": 30},
    {"name": "Graphic Hoodie", "brand": "StreetCore", "size": "L", "color": "Black", "price": "54.99", "stock": 28},
    {"name": "Graphic Hoodie", "brand": "StreetCore", "size": "XXL", "color": "Red", "price": "57.99", "stock": 3},
]


def seed():
    created = 0
    failed = 0
    for item in CLOTHES_DATA:
        try:
            resp = requests.post(BASE_URL, json=item, timeout=5)
            if resp.status_code in (200, 201):
                print(f"  [OK] {item['name']} ({item['size']}, {item['color']})")
                created += 1
            else:
                print(f"  [FAIL] {item['name']} ({item['size']}) -> HTTP {resp.status_code}: {resp.text[:80]}")
                failed += 1
        except requests.RequestException as exc:
            print(f"  [ERROR] {item['name']} ({item['size']}) -> {exc}")
            failed += 1

    print(f"\nDone: {created} created, {failed} failed.")


if __name__ == "__main__":
    print(f"Seeding clothes data to {BASE_URL} ...\n")
    seed()
