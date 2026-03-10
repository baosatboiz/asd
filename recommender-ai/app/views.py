import os
import re
from collections import Counter, defaultdict

import requests
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Recommendation
from .serializers import RecommendationSerializer


class RecommendationViewSet(viewsets.ModelViewSet):
    queryset = Recommendation.objects.all().order_by("-score", "-created_at")
    serializer_class = RecommendationSerializer

    def list(self, request, *args, **kwargs):
        """
        Dynamically generate recommendations based on:
        1. Recent successful orders (paid/shipped/completed)
        2. High ratings (rating > 4) from comment-rate service
        """
        order_service_url = os.getenv("ORDER_SERVICE_URL", "http://order:8000")
        comment_service_url = os.getenv("COMMENT_RATE_SERVICE_URL", "http://comment-rate:8000")
        actor_id = self._parse_actor_id(request.headers.get("X-Actor-Id"))

        # Fetch successful orders
        book_order_counts = Counter()
        customer_ordered_books = defaultdict(set)
        try:
            orders_response = requests.get(f"{order_service_url}/orders/", timeout=5)
            if orders_response.status_code == 200:
                orders = orders_response.json()
                for order in orders:
                    shipping_addr = order.get("shipping_address", "")
                    book_ids = self._extract_book_ids(shipping_addr)
                    customer_id = self._parse_actor_id(order.get("customer_id"))

                    for book_id in book_ids:
                        if customer_id is not None:
                            customer_ordered_books[customer_id].add(book_id)

                    order_status = order.get("status", "")
                    if order_status in ["paid", "shipped", "completed"]:
                        for book_id in book_ids:
                            book_order_counts[book_id] += 1
        except requests.RequestException:
            pass

        # Fetch high-rated comments (rating > 4)
        book_ratings = defaultdict(list)
        try:
            comments_response = requests.get(f"{comment_service_url}/comments-rates/", timeout=5)
            if comments_response.status_code == 200:
                comments = comments_response.json()
                for comment in comments:
                    rating = comment.get("rating", 0)
                    if rating > 4:
                        book_id = comment.get("book_id")
                        if book_id:
                            book_ratings[book_id].append(rating)
        except requests.RequestException:
            pass

        # Calculate scores: order_count * 10 + avg_rating * 20
        book_scores = {}
        all_book_ids = set(book_order_counts.keys()) | set(book_ratings.keys())
        for book_id in all_book_ids:
            order_score = book_order_counts.get(book_id, 0) * 10
            ratings = book_ratings.get(book_id, [])
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            rating_score = avg_rating * 20
            book_scores[book_id] = order_score + rating_score

        # Personalized output: avoid recommending books already successfully ordered by this user.
        recommendations = []
        already_owned = customer_ordered_books.get(actor_id, set()) if actor_id is not None else set()
        sorted_books = sorted(book_scores.items(), key=lambda x: x[1], reverse=True)
        filtered_books = [(book_id, score) for (book_id, score) in sorted_books if book_id not in already_owned]

        for idx, (book_id, score) in enumerate(filtered_books[:20]):  # Top 20
            order_count = book_order_counts.get(book_id, 0)
            avg_rating = (
                sum(book_ratings[book_id]) / len(book_ratings[book_id]) if book_id in book_ratings else 0
            )
            reason = (
                f"Trending ({order_count} recent successful orders), highly rated ({avg_rating:.1f}/5)"
                if order_count and avg_rating
                else f"Trending with {order_count} recent successful orders"
                if order_count
                else f"Highly rated by readers ({avg_rating:.1f}/5)"
            )
            recommendations.append(
                {
                    "id": idx + 1,
                    "customer_id": actor_id,
                    "recommended_book_id": book_id,
                    "score": round(score, 2),
                    "reason": reason,
                }
            )

        return Response(recommendations, status=status.HTTP_200_OK)

    def _parse_actor_id(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _extract_book_ids(self, shipping_address):
        """Extract book IDs from shipping_address marker like '|books:1,2,3'"""
        match = re.search(r"\|books:([\d,]+)", shipping_address)
        if match:
            book_ids_str = match.group(1)
            return [int(bid) for bid in book_ids_str.split(",") if bid.strip().isdigit()]
        return []
