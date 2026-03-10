import os
from urllib.parse import quote_plus

import requests
from django.shortcuts import redirect, render
from rest_framework.response import Response
from rest_framework.views import APIView

IDENTITY_OPTIONS = [
    {"key": "manager-1", "label": "Manager (ID 1)", "role": "manager", "user_id": 1},
    {"key": "staff-1", "label": "Staff (ID 1)", "role": "staff", "user_id": 1},
    {"key": "customer-1", "label": "Customer (ID 1)", "role": "customer", "user_id": 1},
    {"key": "customer-2", "label": "Customer (ID 2)", "role": "customer", "user_id": 2},
    {"key": "customer-3", "label": "Customer (ID 3)", "role": "customer", "user_id": 3},
]


def _safe_get(url, headers=None, default=None):
    if default is None:
        default = []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return default
    return default


def _safe_post(url, payload, headers=None):
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code in (200, 201):
            try:
                return response.json(), None
            except ValueError:
                return {}, "Upstream service returned non-JSON success response."

        detail = None
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if detail:
            return None, detail
        return None, f"Upstream service returned status {response.status_code}."
    except requests.RequestException as exc:
        return None, f"Service request failed: {exc}"


def _find_customer_cart(customer_id, cart_service, headers=None):
    carts = _safe_get(f"{cart_service}/carts/", headers=headers)
    if not isinstance(carts, list):
        return None
    for cart in carts:
        if cart.get("customer_id") == customer_id:
            return cart
    return None


def _identity_lookup(key):
    return next((item for item in IDENTITY_OPTIONS if item["key"] == key), None)


def _get_identity(request):
    key = request.session.get("actor_key", "customer-1")
    found = _identity_lookup(key)
    return found or _identity_lookup("customer-1")


def _set_identity(request, item):
    request.session["actor_key"] = item["key"]
    request.session["actor_role"] = item["role"]
    request.session["actor_id"] = item["user_id"]


def _actor_headers(identity):
    return {
        "X-Actor-Role": identity["role"],
        "X-Actor-Id": str(identity["user_id"]),
    }


def _base_context(identity):
    return {
        "identity_options": IDENTITY_OPTIONS,
        "current_identity": identity,
    }


def _require_customer(identity):
    return identity["role"] == "customer"


def _require_staff(identity):
    return identity["role"] == "staff"


def _require_manager(identity):
    return identity["role"] == "manager"


def _safe_patch(url, payload, headers=None):
    try:
        response = requests.patch(url, json=payload, headers=headers, timeout=5)
        if response.status_code in (200, 201):
            try:
                return response.json(), None
            except ValueError:
                return {}, "Upstream service returned non-JSON success response."

        detail = None
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if detail:
            return None, detail
        return None, f"Upstream service returned status {response.status_code}."
    except requests.RequestException as exc:
        return None, f"Service request failed: {exc}"


def _safe_delete(url, headers=None):
    try:
        response = requests.delete(url, headers=headers, timeout=5)
        if response.status_code in (200, 201, 204):
            return True, None
        return False, f"Upstream service returned status {response.status_code}."
    except requests.RequestException as exc:
        return False, f"Service request failed: {exc}"


def _comment_endpoints(comment_service):
    return [f"{comment_service}/comments/", f"{comment_service}/comments-rates/"]


def _fetch_comments(comment_service, headers=None):
    for endpoint in _comment_endpoints(comment_service):
        comments = _safe_get(endpoint, headers=headers, default=None)
        if isinstance(comments, list):
            return comments
    return []


def _post_comment(comment_service, payload, headers=None):
    last_err = None
    for endpoint in _comment_endpoints(comment_service):
        data, err = _safe_post(endpoint, payload, headers=headers)
        if not err:
            return data, None
        last_err = err
    return None, last_err or "Unable to submit review to comment-rate service."


def _apply_book_ratings(books, comments):
    if not isinstance(books, list):
        return books
    ratings = {}
    for comment in comments if isinstance(comments, list) else []:
        book_id = comment.get("book_id")
        rating = comment.get("rating")
        try:
            book_id = int(book_id)
            rating = float(rating)
        except (TypeError, ValueError):
            continue
        bucket = ratings.setdefault(book_id, [])
        bucket.append(rating)

    for book in books:
        bid = book.get("id")
        book_ratings = ratings.get(bid, [])
        if book_ratings:
            avg = sum(book_ratings) / len(book_ratings)
            book["avg_rating"] = round(avg, 1)
            book["rating_count"] = len(book_ratings)
        else:
            book["avg_rating"] = None
            book["rating_count"] = 0
    return books


def _extract_order_book_ids(order_obj):
    raw_ids = order_obj.get("ordered_book_ids", [])
    if isinstance(raw_ids, list):
        out = []
        for value in raw_ids:
            try:
                out.append(int(value))
            except (TypeError, ValueError):
                continue
        if out:
            return out

    marker = "|books:"
    shipping_address = order_obj.get("shipping_address", "")
    if marker in shipping_address:
        suffix = shipping_address.split(marker, 1)[1]
        values = []
        for token in suffix.split(","):
            token = token.strip()
            try:
                values.append(int(token))
            except (TypeError, ValueError):
                continue
        return values

    return []


class SwitchIdentityView(APIView):
    def post(self, request):
        key = request.POST.get("identity_key", "customer-1")
        item = _identity_lookup(key) or _identity_lookup("customer-1")
        _set_identity(request, item)
        return redirect(request.POST.get("next", "/"))


class HomePageView(APIView):
    def get(self, request):
        catalog_service = os.getenv("CATALOG_SERVICE_URL", "http://catalog:8000")
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")
        recommender_service = os.getenv("RECOMMENDER_SERVICE_URL", "http://recommender-ai:8000")
        comment_service = os.getenv("COMMENT_RATE_SERVICE_URL", "http://comment-rate:8000")
        identity = _get_identity(request)
        headers = _actor_headers(identity)

        categories = _safe_get(f"{catalog_service}/categories/", headers=headers)
        books = _safe_get(f"{book_service}/books/", headers=headers)
        recommendations = _safe_get(f"{recommender_service}/recommendations/", headers=headers)
        comments = _fetch_comments(comment_service, headers=headers)
        books = _apply_book_ratings(books, comments)

        # Fallback: derive categories from books when catalog service returns empty.
        if (not isinstance(categories, list) or not categories) and isinstance(books, list):
            category_ids = sorted({b.get("category_id") for b in books if isinstance(b, dict) and b.get("category_id") is not None})
            categories = [{"id": cid, "name": f"Category {cid}"} for cid in category_ids]

        # Fallback: suggest top-rated books if recommender returns empty.
        if (not isinstance(recommendations, list) or not recommendations) and isinstance(books, list):
            rated_books = [b for b in books if isinstance(b, dict) and b.get("avg_rating") is not None]
            rated_books.sort(key=lambda x: float(x.get("avg_rating", 0)), reverse=True)
            recommendations = [
                {
                    "recommended_book_id": b.get("id"),
                    "score": float(b.get("avg_rating", 0)) * 20,
                    "reason": f"Top rated in catalog ({b.get('avg_rating')}/5)",
                }
                for b in rated_books[:5]
            ]

        if isinstance(recommendations, list) and isinstance(books, list):
            title_by_id = {book.get("id"): book.get("title") for book in books if isinstance(book, dict)}
            for rec in recommendations:
                if not isinstance(rec, dict):
                    continue
                book_id = rec.get("recommended_book_id")
                title = title_by_id.get(book_id)
                rec["book_title"] = title
                rec["display_title"] = title or f"Book #{book_id}"

        selected_category = request.GET.get("category")
        selected_category_id = None
        if selected_category:
            try:
                selected_category_id = int(selected_category)
                if isinstance(books, list):
                    books = [b for b in books if b.get("category_id") == selected_category_id]
            except ValueError:
                selected_category_id = None

        context = _base_context(identity)
        context.update(
            {
                "categories": categories,
                "books": books,
                "recommendations": recommendations,
                "selected_category_id": selected_category_id,
                "is_customer": identity["role"] == "customer",
                "error": request.GET.get("error"),
            }
        )
        return render(request, "index.html", context)


class BookDetailView(APIView):
    def get(self, request, book_id):
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")
        comment_service = os.getenv("COMMENT_RATE_SERVICE_URL", "http://comment-rate:8000")
        identity = _get_identity(request)
        headers = _actor_headers(identity)

        book = _safe_get(f"{book_service}/books/{book_id}/", headers=headers, default={})
        all_comments = _fetch_comments(comment_service, headers=headers)
        book_comments = []
        for item in all_comments:
            try:
                if int(item.get("book_id")) == int(book_id):
                    book_comments.append(item)
            except (TypeError, ValueError):
                continue

        books_for_rating = _apply_book_ratings([book] if isinstance(book, dict) and book else [], book_comments)
        book_with_rating = books_for_rating[0] if books_for_rating else book

        context = _base_context(identity)
        context.update(
            {
                "book": book_with_rating,
                "comments": book_comments,
                "is_customer": _require_customer(identity),
                "error": request.GET.get("error"),
                "message": request.GET.get("message"),
            }
        )
        return render(request, "book_detail.html", context)


class SubmitReviewView(APIView):
    def post(self, request):
        comment_service = os.getenv("COMMENT_RATE_SERVICE_URL", "http://comment-rate:8000")
        order_service = os.getenv("ORDER_SERVICE_URL", "http://order:8000")
        identity = _get_identity(request)
        headers = _actor_headers(identity)

        if not _require_customer(identity):
            return redirect("/success/?order_id={}&error=Only+customers+can+submit+reviews".format(request.POST.get("order_id", "")))

        order_id = request.POST.get("order_id", "")
        book_id = request.POST.get("book_id")
        form_customer_id = request.POST.get("customer_id")
        rating = request.POST.get("rating")
        comment = request.POST.get("comment", "")

        try:
            order_id_int = int(order_id)
            book_id = int(book_id)
            form_customer_id = int(form_customer_id)
            rating = int(rating)
        except (TypeError, ValueError):
            return redirect(f"/success/?order_id={order_id}&error=Invalid+book+or+rating")

        order_obj = _safe_get(f"{order_service}/orders/{order_id_int}/", headers=headers, default={})
        if not isinstance(order_obj, dict) or not order_obj:
            return redirect(f"/success/?order_id={order_id}&error=Unable+to+load+order+details")

        try:
            order_customer_id = int(order_obj.get("customer_id"))
        except (TypeError, ValueError):
            return redirect(f"/success/?order_id={order_id}&error=Order+customer+is+invalid")

        if order_customer_id != int(identity["user_id"]):
            return redirect(f"/success/?order_id={order_id}&error=Switch+to+the+customer+who+placed+this+order")
        if form_customer_id != order_customer_id:
            return redirect(f"/success/?order_id={order_id}&error=Review+payload+customer+mismatch")

        ordered_book_ids = _extract_order_book_ids(order_obj)
        if book_id not in ordered_book_ids:
            return redirect(f"/success/?order_id={order_id}&error=Select+a+book+from+this+order")

        payload = {
            "book_id": book_id,
            "customer_id": order_customer_id,
            "rating": rating,
            "comment": comment,
        }

        _, err = _post_comment(comment_service, payload, headers=headers)
        if err:
            return redirect(f"/success/?order_id={order_id}&error={quote_plus(err)}")
        return redirect(f"/success/?order_id={order_id}&message=Review+submitted+successfully")


class AddToCartView(APIView):
    def post(self, request):
        cart_service = os.getenv("CART_SERVICE_URL", "http://cart:8000")
        identity = _get_identity(request)
        headers = _actor_headers(identity)

        if not _require_customer(identity):
            return redirect("/?error=Select+a+Customer+identity+to+add+items+to+cart")

        book_id = request.data.get("book_id") or request.POST.get("book_id")
        quantity = request.data.get("quantity") or request.POST.get("quantity", 1)
        customer_id = int(identity["user_id"])

        try:
            book_id = int(book_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            return redirect("/?error=book_id+and+quantity+must+be+valid+integers")

        cart = _find_customer_cart(customer_id, cart_service, headers=headers)
        if not cart:
            cart, err = _safe_post(f"{cart_service}/carts/", {"customer_id": customer_id}, headers=headers)
            if err or not cart:
                return redirect("/?error=Unable+to+create+customer+cart")

        cart_id = cart.get("id")
        if not cart_id:
            return redirect("/?error=Cart+response+missing+cart_id")

        _, err = _safe_post(
            f"{cart_service}/carts/{cart_id}/add-item/",
            {"customer_id": customer_id, "book_id": book_id, "quantity": quantity},
            headers=headers,
        )
        if err:
            return redirect("/?error=Failed+to+add+book+to+cart")

        return redirect("/cart/")


class CartView(APIView):
    def get(self, request):
        cart_service = os.getenv("CART_SERVICE_URL", "http://cart:8000")
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        error = request.GET.get("error")
        cart = None
        detailed_items = []
        customer_id = None

        if not _require_customer(identity):
            error = error or "Cart is available only for Customer identities."
        else:
            customer_id = int(identity["user_id"])
            cart = _find_customer_cart(customer_id, cart_service, headers=headers)
            if not cart:
                error = error or "No cart found for this customer. Add a book from Catalog first."

        items = cart.get("items", []) if cart else []
        for item in items:
            book_id = item.get("book_id")
            book_data = _safe_get(f"{book_service}/books/{book_id}/", headers=headers, default={})
            detailed_items.append(
                {
                    "book_id": book_id,
                    "quantity": item.get("quantity", 1),
                    "title": book_data.get("title", "Unknown book"),
                    "price": book_data.get("price", "0.00"),
                }
            )

        context = _base_context(identity)
        context.update(
            {
                "customer_id": customer_id,
                "cart": cart,
                "items": detailed_items,
                "error": error,
                "is_customer": _require_customer(identity),
            }
        )
        return render(request, "cart.html", context)


class CheckoutView(APIView):
    def post(self, request):
        cart_service = os.getenv("CART_SERVICE_URL", "http://cart:8000")
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")
        order_service = os.getenv("ORDER_SERVICE_URL", "http://order:8000")
        identity = _get_identity(request)
        headers = _actor_headers(identity)

        if not _require_customer(identity):
            return redirect("/cart/?error=Only+customers+can+place+orders")

        customer_id = int(identity["user_id"])
        cart = _find_customer_cart(customer_id, cart_service, headers=headers)
        if not cart:
            return redirect("/cart/?error=No+cart+found+for+customer")

        items = cart.get("items", [])
        if not items:
            return redirect("/cart/?error=Cart+is+empty")

        total_price = 0.0
        ordered_book_ids = []
        for item in items:
            book_id = item.get("book_id")
            quantity = item.get("quantity", 1)
            book_data = _safe_get(f"{book_service}/books/{book_id}/", headers=headers, default={})
            if isinstance(book_data, dict) and book_data.get("price") is not None:
                try:
                    total_price += float(book_data["price"]) * int(quantity)
                    ordered_book_ids.append(int(book_id))
                except (TypeError, ValueError):
                    continue

        if total_price <= 0 or not ordered_book_ids:
            return redirect("/cart/?error=Unable+to+compute+order+total")

        unique_book_ids = sorted(set(ordered_book_ids))
        book_marker = ",".join(str(bid) for bid in unique_book_ids)
        order_payload = {
            "customer_id": customer_id,
            "total_price": f"{total_price:.2f}",
            "shipping_address": f"Customer {customer_id} default address |books:{book_marker}",
        }
        order_data, err = _safe_post(f"{order_service}/orders/", order_payload, headers=headers)
        if err or not order_data:
            return redirect("/cart/?error=Failed+to+create+order")

        # Clear cart after successful order creation
        _safe_post(f"{cart_service}/carts/{cart['id']}/clear-items/", {}, headers=headers)

        return redirect(f"/success/?order_id={order_data.get('id')}")


class SuccessView(APIView):
    def get(self, request):
        order_id_raw = request.GET.get("order_id")
        order_service = os.getenv("ORDER_SERVICE_URL", "http://order:8000")
        pay_service = os.getenv("PAY_SERVICE_URL", "http://pay:8000")
        ship_service = os.getenv("SHIP_SERVICE_URL", "http://ship:8000")
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")
        identity = _get_identity(request)
        headers = _actor_headers(identity)

        try:
            order_id = int(order_id_raw)
        except (TypeError, ValueError):
            return Response({"detail": "order_id query parameter is required."}, status=400)

        payments = _safe_get(f"{pay_service}/payments/", headers=headers)
        shipments = _safe_get(f"{ship_service}/shipments/", headers=headers)

        payment_record = None
        shipment_record = None

        if isinstance(payments, list):
            payment_record = next((p for p in payments if p.get("order_id") == order_id), None)
        if isinstance(shipments, list):
            shipment_record = next((s for s in shipments if s.get("order_id") == order_id), None)

        order_obj = _safe_get(f"{order_service}/orders/{order_id}/", headers=headers, default={})
        ordered_book_ids = _extract_order_book_ids(order_obj) if isinstance(order_obj, dict) else []
        books = _safe_get(f"{book_service}/books/", headers=headers)
        purchased_books = []
        if isinstance(books, list):
            purchased_books = [
                b for b in books if isinstance(b, dict) and b.get("id") in ordered_book_ids
            ]

        order_customer_id = None
        if isinstance(order_obj, dict):
            try:
                order_customer_id = int(order_obj.get("customer_id"))
            except (TypeError, ValueError):
                order_customer_id = None

        context = _base_context(identity)
        context.update(
            {
                "order_id": order_id,
                "order_customer_id": order_customer_id,
                "payment_status": payment_record.get("status") if payment_record else "not_found",
                "shipment_status": shipment_record.get("status") if shipment_record else "not_found",
                "payment_record": payment_record,
                "shipment_record": shipment_record,
                "books": purchased_books,
                "is_customer": _require_customer(identity),
                "error": request.GET.get("error"),
                "message": request.GET.get("message"),
            }
        )
        return render(request, "success.html", context)


class DashboardView(APIView):
    def get(self, request):
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        order_service = os.getenv("ORDER_SERVICE_URL", "http://order:8000")
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")
        customer_service = os.getenv("CUSTOMER_SERVICE_URL", "http://customer:8000")
        staff_service = os.getenv("STAFF_SERVICE_URL", "http://staff:8000")
        pay_service = os.getenv("PAY_SERVICE_URL", "http://pay:8000")

        context = _base_context(identity)

        if not (identity["role"] == "manager" and int(identity["user_id"]) == 1):
            context.update({
                "forbidden": True,
                "total_sales": "0.00",
                "total_books": 0,
                "total_orders": 0,
                "total_customers": 0,
                "total_staff": 0,
                "pending_orders": 0,
                "avg_order_value": "0.00",
                "low_stock_books": 0,
                "completed_payments": 0,
                "recent_orders": [],
            })
            return render(request, "dashboard.html", context, status=403)

        orders = _safe_get(f"{order_service}/orders/", headers=headers)
        books = _safe_get(f"{book_service}/books/", headers=headers)
        customers = _safe_get(f"{customer_service}/customers/", headers=headers)
        staff = _safe_get(f"{staff_service}/staffs/", headers=headers)
        payments = _safe_get(f"{pay_service}/payments/", headers=headers)

        total_sales = 0.0
        pending_orders_count = 0
        completed_payments_count = 0
        recent_orders_list = []

        if isinstance(orders, list):
            for order in orders:
                try:
                    total_sales += float(order.get("total_price", 0))
                except (TypeError, ValueError):
                    continue
                if order.get("status") == "pending":
                    pending_orders_count += 1
                recent_orders_list.append(order)

        # Sort recent orders by created_at (most recent first) and limit to 5
        recent_orders_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        recent_orders_list = recent_orders_list[:5]

        if isinstance(payments, list):
            completed_payments_count = len([p for p in payments if p.get("status") == "completed"])

        avg_order_value = 0.0
        if isinstance(orders, list) and len(orders) > 0:
            avg_order_value = total_sales / len(orders)

        low_stock_books_count = 0
        if isinstance(books, list):
            low_stock_books_count = len([b for b in books if isinstance(b.get("stock"), int) and b.get("stock") < 5])

        context.update(
            {
                "forbidden": False,
                "total_sales": f"{total_sales:.2f}",
                "total_books": len(books) if isinstance(books, list) else 0,
                "total_orders": len(orders) if isinstance(orders, list) else 0,
                "total_customers": len(customers) if isinstance(customers, list) else 0,
                "total_staff": len(staff) if isinstance(staff, list) else 0,
                "pending_orders": pending_orders_count,
                "avg_order_value": f"{avg_order_value:.2f}",
                "low_stock_books": low_stock_books_count,
                "completed_payments": completed_payments_count,
                "recent_orders": recent_orders_list,
            }
        )
        return render(request, "dashboard.html", context)


class StaffDashboardView(APIView):
    def get(self, request):
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        order_service = os.getenv("ORDER_SERVICE_URL", "http://order:8000")
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")

        context = _base_context(identity)

        if not _require_staff(identity):
            context.update({"forbidden": True, "pending_orders": [], "low_stock_books": []})
            return render(request, "staff_dashboard.html", context, status=403)

        orders = _safe_get(f"{order_service}/orders/", headers=headers)
        books = _safe_get(f"{book_service}/books/", headers=headers)

        pending_orders = []
        if isinstance(orders, list):
            pending_orders = [o for o in orders if o.get("status") == "pending"]

        low_stock_books = []
        if isinstance(books, list):
            low_stock_books = [b for b in books if isinstance(b.get("stock"), int) and b.get("stock") < 5]

        context.update(
            {
                "forbidden": False,
                "pending_orders": pending_orders,
                "low_stock_books": low_stock_books,
                "success": request.GET.get("success"),
                "error": request.GET.get("error"),
            }
        )
        return render(request, "staff_dashboard.html", context)


class MarkOrderShippedView(APIView):
    def post(self, request):
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        order_service = os.getenv("ORDER_SERVICE_URL", "http://order:8000")

        if not _require_staff(identity):
            return redirect("/staff/dashboard/?error=Only+staff+can+mark+orders+as+shipped")

        order_id = request.POST.get("order_id")
        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            return redirect("/staff/dashboard/?error=Invalid+order+ID")

        try:
            response = requests.patch(
                f"{order_service}/orders/{order_id}/",
                json={"status": "shipped"},
                headers=headers,
                timeout=5,
            )
            if response.status_code in (200, 201):
                return redirect(f"/staff/dashboard/?success=Order+{order_id}+marked+as+shipped")
            else:
                return redirect(f"/staff/dashboard/?error=Failed+to+update+order+{order_id}")
        except requests.RequestException:
            return redirect(f"/staff/dashboard/?error=Order+service+unavailable")


class ManageBooksView(APIView):
    def get(self, request):
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")

        context = _base_context(identity)

        if not _require_staff(identity):
            context.update({"forbidden": True, "books": []})
            return render(request, "manage_books.html", context, status=403)

        books = _safe_get(f"{book_service}/books/", headers=headers)

        context.update(
            {
                "forbidden": False,
                "books": books if isinstance(books, list) else [],
                "success": request.GET.get("success"),
                "error": request.GET.get("error"),
            }
        )
        return render(request, "manage_books.html", context)


class AddBookView(APIView):
    def get(self, request):
        identity = _get_identity(request)
        context = _base_context(identity)

        if not _require_staff(identity):
            context.update({"forbidden": True})
            return render(request, "add_edit_book.html", context, status=403)

        context.update({"forbidden": False, "book": None, "is_edit": False})
        return render(request, "add_edit_book.html", context)

    def post(self, request):
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")

        if not _require_staff(identity):
            return redirect("/staff/manage-books/?error=Only+staff+can+add+books")

        title = request.POST.get("title", "").strip()
        author = request.POST.get("author", "").strip()
        isbn = request.POST.get("isbn", "").strip()
        price = request.POST.get("price", "").strip()
        stock = request.POST.get("stock", "0").strip()
        category_id = request.POST.get("category_id", "").strip()

        if not title or not author or not isbn or not price:
            return redirect("/staff/add-book/?error=Title,+author,+ISBN,+and+price+are+required")

        try:
            price = float(price)
            stock = int(stock)
            category_id = int(category_id) if category_id else None
        except ValueError:
            return redirect("/staff/add-book/?error=Price+must+be+a+number+and+stock+must+be+an+integer")

        payload = {
            "title": title,
            "author": author,
            "isbn": isbn,
            "price": f"{price:.2f}",
            "stock": stock,
        }
        if category_id:
            payload["category_id"] = category_id

        data, err = _safe_post(f"{book_service}/books/", payload, headers=headers)
        if err:
            return redirect(f"/staff/add-book/?error={quote_plus(err)}")

        return redirect(f"/staff/manage-books/?success=Book+added+successfully")


class EditBookView(APIView):
    def get(self, request, book_id):
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")

        context = _base_context(identity)

        if not _require_staff(identity):
            context.update({"forbidden": True, "book": None})
            return render(request, "add_edit_book.html", context, status=403)

        book = _safe_get(f"{book_service}/books/{book_id}/", headers=headers, default={})

        context.update(
            {
                "forbidden": False,
                "book": book if isinstance(book, dict) else {},
                "is_edit": True,
                "error": request.GET.get("error"),
            }
        )
        return render(request, "add_edit_book.html", context)

    def post(self, request, book_id):
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")

        if not _require_staff(identity):
            return redirect("/staff/manage-books/?error=Only+staff+can+edit+books")

        title = request.POST.get("title", "").strip()
        author = request.POST.get("author", "").strip()
        isbn = request.POST.get("isbn", "").strip()
        price = request.POST.get("price", "").strip()
        stock = request.POST.get("stock", "0").strip()
        category_id = request.POST.get("category_id", "").strip()

        if not title or not author or not isbn or not price:
            return redirect(f"/staff/edit-book/{book_id}/?error=Title,+author,+ISBN,+and+price+are+required")

        try:
            price = float(price)
            stock = int(stock)
            category_id = int(category_id) if category_id else None
        except ValueError:
            return redirect(f"/staff/edit-book/{book_id}/?error=Price+must+be+a+number+and+stock+must+be+an+integer")

        payload = {
            "title": title,
            "author": author,
            "isbn": isbn,
            "price": f"{price:.2f}",
            "stock": stock,
        }
        if category_id:
            payload["category_id"] = category_id

        data, err = _safe_patch(f"{book_service}/books/{book_id}/", payload, headers=headers)
        if err:
            return redirect(f"/staff/edit-book/{book_id}/?error={quote_plus(err)}")

        return redirect(f"/staff/manage-books/?success=Book+updated+successfully")


class DeleteBookView(APIView):
    def post(self, request, book_id):
        identity = _get_identity(request)
        headers = _actor_headers(identity)
        book_service = os.getenv("BOOK_SERVICE_URL", "http://book:8000")

        if not _require_staff(identity):
            return redirect("/staff/manage-books/?error=Only+staff+can+delete+books")

        success, err = _safe_delete(f"{book_service}/books/{book_id}/", headers=headers)
        if not success:
            return redirect(f"/staff/manage-books/?error={quote_plus(err)}")

        return redirect(f"/staff/manage-books/?success=Book+deleted+successfully")


class AggregateApiView(APIView):
    def get(self, request):
        customer_service = os.getenv("CUSTOMER_SERVICE_URL", "http://customer:8000")
        order_service = os.getenv("ORDER_SERVICE_URL", "http://order:8000")
        pay_service = os.getenv("PAY_SERVICE_URL", "http://pay:8000")
        comment_service = os.getenv("COMMENT_RATE_SERVICE_URL", "http://comment-rate:8000")
        identity = _get_identity(request)
        headers = _actor_headers(identity)

        data = {
            "customers": _safe_get(f"{customer_service}/customers/", headers=headers),
            "orders": _safe_get(f"{order_service}/orders/", headers=headers),
            "payments": _safe_get(f"{pay_service}/payments/", headers=headers),
            "comments": _fetch_comments(comment_service, headers=headers),
        }
        return Response(data)
