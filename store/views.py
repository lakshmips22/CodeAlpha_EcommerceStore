from functools import wraps
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CheckoutForm, RegistrationForm
from .models import Cart, CartItem, Order, OrderItem, Product


def home(request):
    products = Product.objects.filter(is_available=True).order_by("pk")
    return render(request, "store/home.html", {"products": products})


def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    return render(request, "store/product_detail.html", {"product": product})


def register(request):
    if request.user.is_authenticated:
        return redirect("account")

    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        return redirect("account")

    return render(request, "store/register.html", {"form": form})


@login_required
def account(request):
    return render(request, "store/account.html")


@require_POST
def logout_user(request):
    auth_logout(request)
    return redirect("home")


def _cart_return_url(request):
    candidate = request.POST.get("next", "") or request.META.get("HTTP_REFERER", "")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse("home")


def cart_login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to use your cart. Your cart was not changed.")
            return redirect_to_login(_cart_return_url(request))
        return view(request, *args, **kwargs)

    return wrapped


@require_POST
@cart_login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if not product.is_available:
        messages.warning(request, "This product is currently unavailable and was not added.")
        return redirect(_cart_return_url(request))

    with transaction.atomic():
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart = Cart.objects.select_for_update().get(pk=cart.pk)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": 1},
        )
        if not created:
            updated = CartItem.objects.filter(
                pk=item.pk,
                quantity__lt=CartItem.MAX_QUANTITY,
            ).update(quantity=F("quantity") + 1)
            if not updated:
                messages.warning(request, "You have reached the maximum quantity for this product.")

    return redirect(_cart_return_url(request))


@require_POST
@cart_login_required
def cart_update(request, item_id):
    with transaction.atomic():
        cart = get_object_or_404(Cart.objects.select_for_update(), user=request.user)
        item = get_object_or_404(
            CartItem.objects.select_for_update(),
            pk=item_id,
            cart=cart,
        )
        action = request.POST.get("action")
        if action == "increase":
            updated = CartItem.objects.filter(
                pk=item.pk,
                quantity__lt=CartItem.MAX_QUANTITY,
            ).update(quantity=F("quantity") + 1)
            if not updated:
                messages.warning(request, "You have reached the maximum quantity for this product.")
        elif action == "decrease":
            updated = CartItem.objects.filter(pk=item.pk, quantity__gt=1).update(
                quantity=F("quantity") - 1
            )
            if not updated:
                messages.info(request, "Quantity is already at its minimum. Use Remove to delete the item.")
        else:
            messages.error(request, "That cart quantity action is not valid.")

    return redirect(_cart_return_url(request))


@require_POST
@cart_login_required
def cart_remove(request, item_id):
    with transaction.atomic():
        cart = get_object_or_404(Cart.objects.select_for_update(), user=request.user)
        item = get_object_or_404(
            CartItem.objects.select_for_update(),
            pk=item_id,
            cart=cart,
        )
        item.delete()
    return redirect(_cart_return_url(request))


@login_required
def checkout(request):
    form = CheckoutForm(request.POST or None)
    if request.method == "GET":
        return render(request, "store/checkout.html", {"form": form})

    if not CartItem.objects.filter(cart__user=request.user).exists():
        form.add_error(None, "Your cart is empty. Add an available product before checking out.")
        return render(request, "store/checkout.html", {"form": form}, status=400)

    if not form.is_valid():
        return render(request, "store/checkout.html", {"form": form}, status=400)

    with transaction.atomic():
        cart = Cart.objects.select_for_update().filter(user=request.user).first()
        if cart is None:
            form.add_error(None, "Your cart is empty. Add an available product before checking out.")
            return render(request, "store/checkout.html", {"form": form}, status=400)

        items = list(
            CartItem.objects.select_for_update()
            .filter(cart=cart)
            .order_by("pk")
        )
        if not items:
            form.add_error(None, "Your cart is empty. Add an available product before checking out.")
            return render(request, "store/checkout.html", {"form": form}, status=400)

        products = {
            product.pk: product
            for product in Product.objects.select_for_update().filter(
                pk__in=[item.product_id for item in items]
            )
        }
        unavailable = [
            item.product_id
            for item in items
            if item.product_id not in products or not products[item.product_id].is_available
        ]
        invalid_quantities = [
            item for item in items
            if item.quantity < 1 or item.quantity > CartItem.MAX_QUANTITY
        ]
        if unavailable or invalid_quantities:
            names = [
                products[item.product_id].name
                for item in items
                if item.product_id in unavailable and item.product_id in products
            ]
            detail = f" Unavailable products: {', '.join(names)}." if names else ""
            form.add_error(
                None,
                "Your cart changed or contains an unavailable item. Review it and try again." + detail,
            )
            return render(request, "store/checkout.html", {"form": form}, status=400)

        total = sum(
            (products[item.product_id].price * item.quantity for item in items),
            Decimal("0.00"),
        )
        order = Order.objects.create(
            user=request.user,
            total=total,
            **form.cleaned_data,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=products[item.product_id],
                    product_name=products[item.product_id].name,
                    unit_price=products[item.product_id].price,
                    quantity=item.quantity,
                )
                for item in items
            ]
        )
        CartItem.objects.filter(cart=cart).delete()

    return redirect("order_confirmation", reference=order.reference)


@login_required
def order_confirmation(request, reference):
    order = get_object_or_404(Order, reference=reference, user=request.user)
    return render(request, "store/order_confirmation.html", {"order": order})


@login_required
def order_history(request):
    orders = request.user.orders.order_by("-created_at", "-pk")
    return render(request, "store/order_history.html", {"orders": orders})


@login_required
def order_detail(request, reference):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        reference=reference,
        user=request.user,
    )
    return render(request, "store/order_detail.html", {"order": order})
