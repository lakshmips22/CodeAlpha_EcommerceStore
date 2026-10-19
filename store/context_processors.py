from decimal import Decimal

from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Sum

from .models import Cart, CartItem


def cart_summary(request):
    if not request.user.is_authenticated:
        return {
            "cart_count": 0,
            "cart_subtotal": Decimal("0.00"),
            "cart_items": [],
        }

    cart = Cart.objects.filter(user=request.user).first()
    if cart is None:
        return {
            "cart_count": 0,
            "cart_subtotal": Decimal("0.00"),
            "cart_items": [],
        }

    items = CartItem.objects.filter(cart=cart).select_related("product")
    totals = items.aggregate(
        count=Sum("quantity"),
        subtotal=Sum(
            ExpressionWrapper(
                F("product__price") * F("quantity"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        ),
    )
    return {
        "cart_count": totals["count"] or 0,
        "cart_subtotal": totals["subtotal"] or Decimal("0.00"),
        "cart_items": items,
    }
