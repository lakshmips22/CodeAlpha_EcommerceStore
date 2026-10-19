from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),
    path("accounts/register/", views.register, name="register"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="store/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("accounts/logout/", views.logout_user, name="logout"),
    path("accounts/", views.account, name="account"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/items/<int:item_id>/update/", views.cart_update, name="cart_update"),
    path("cart/items/<int:item_id>/remove/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path(
        "orders/<uuid:reference>/confirmation/",
        views.order_confirmation,
        name="order_confirmation",
    ),
    path("orders/", views.order_history, name="order_history"),
    path("orders/<uuid:reference>/", views.order_detail, name="order_detail"),
]
