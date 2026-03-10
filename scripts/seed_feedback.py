import random

import requests

COMMENT_SERVICE_URL = "http://comment-rate:8000/comments/"

SAMPLE_COMMENTS = [
    "Excellent clarity and examples.",
    "Good book for beginners.",
    "Useful for my assignment prep.",
    "Covers concepts in a practical way.",
    "Well structured and easy to follow.",
    "Strong content, but could be shorter.",
    "Very relevant for microservices coursework.",
    "Great value for the price.",
    "Solid reference material.",
    "Engaging writing style and pacing.",
]


def main():
    created = 0
    for _ in range(8):
        payload = {
            "book_id": random.randint(1, 5),
            "customer_id": random.randint(1, 3),
            "rating": random.randint(1, 5),
            "comment": random.choice(SAMPLE_COMMENTS),
        }
        try:
            response = requests.post(COMMENT_SERVICE_URL, json=payload, timeout=8)
            if response.status_code in (200, 201):
                created += 1
                print(f"[OK] {payload}")
            else:
                print(f"[FAIL] status={response.status_code} payload={payload} body={response.text[:160]}")
        except requests.RequestException as exc:
            print(f"[FAIL] request error={exc} payload={payload}")

    print(f"Created {created} feedback records")


if __name__ == "__main__":
    main()
