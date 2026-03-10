from django.urls import path

from .views import (
    AddBookView,
    AddToCartView,
    AggregateApiView,
    BookDetailView,
    CartView,
    CheckoutView,
    DeleteBookView,
    DashboardView,
    EditBookView,
    HomePageView,
    ManageBooksView,
    MarkOrderShippedView,
    StaffDashboardView,
    SubmitReviewView,
    SwitchIdentityView,
    SuccessView,
)

urlpatterns = [
    path("", HomePageView.as_view(), name="gateway-home"),
    path("switch-identity/", SwitchIdentityView.as_view(), name="gateway-switch-identity"),
    path("books/<int:book_id>/", BookDetailView.as_view(), name="gateway-book-detail"),
    path("add-to-cart/", AddToCartView.as_view(), name="gateway-add-to-cart"),
    path("cart/", CartView.as_view(), name="gateway-cart"),
    path("checkout/", CheckoutView.as_view(), name="gateway-checkout"),
    path("success/", SuccessView.as_view(), name="gateway-success"),
    path("submit-review/", SubmitReviewView.as_view(), name="gateway-submit-review"),
    path("dashboard/", DashboardView.as_view(), name="gateway-dashboard"),
    path("staff/dashboard/", StaffDashboardView.as_view(), name="gateway-staff-dashboard"),
    path("staff/mark-shipped/", MarkOrderShippedView.as_view(), name="gateway-mark-shipped"),
    path("staff/manage-books/", ManageBooksView.as_view(), name="gateway-manage-books"),
    path("staff/add-book/", AddBookView.as_view(), name="gateway-add-book"),
    path("staff/edit-book/<int:book_id>/", EditBookView.as_view(), name="gateway-edit-book"),
    path("staff/delete-book/<int:book_id>/", DeleteBookView.as_view(), name="gateway-delete-book"),
    path("aggregate/", AggregateApiView.as_view(), name="gateway-aggregate"),
]
