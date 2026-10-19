from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from django.urls import reverse

from .models import Cart, CartItem, Order, OrderItem, Product


class DatabaseCartTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user_a = user_model.objects.create_user(
            username="cart-user-a",
            password="test-password-123",
        )
        self.user_b = user_model.objects.create_user(
            username="cart-user-b",
            password="test-password-123",
        )
        self.headphones = Product.objects.create(
            name="Test headphones",
            description="Test item",
            price=Decimal("1499.00"),
            image_path="store/images/test-headphones.jpg",
        )
        self.watch = Product.objects.create(
            name="Test watch",
            description="Test item",
            price=Decimal("2499.50"),
            image_path="store/images/test-watch.jpg",
        )
        self.client.force_login(self.user_a)

    def test_add_uses_database_price_merges_duplicate_items_and_renders_totals(self):
        add_url = reverse("cart_add", args=[self.headphones.pk])
        self.client.post(add_url, {"next": "/", "price": "0.01"})
        self.client.post(add_url, {"next": "/", "price": "0.01"})

        cart = Cart.objects.get(user=self.user_a)
        self.assertEqual(CartItem.objects.filter(cart=cart, product=self.headphones).count(), 1)
        item = CartItem.objects.get(cart=cart, product=self.headphones)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.subtotal, Decimal("2998.00"))

        response = self.client.get(reverse("home"))
        self.assertContains(response, "Cart (<span id=\"cart-count\" aria-live=\"polite\">2</span>)")
        self.assertContains(response, "₹2998.00")

    def test_quantity_controls_and_remove_change_only_current_cart(self):
        self.client.post(reverse("cart_add", args=[self.headphones.pk]), {"next": "/"})
        item_a = CartItem.objects.get(cart__user=self.user_a, product=self.headphones)

        client_b = Client()
        client_b.force_login(self.user_b)
        client_b.post(reverse("cart_add", args=[self.watch.pk]), {"next": "/"})
        item_b = CartItem.objects.get(cart__user=self.user_b, product=self.watch)

        response = client_b.post(
            reverse("cart_remove", args=[item_a.pk]),
            {"next": "/"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=item_a.pk).exists())

        update_url = reverse("cart_update", args=[item_b.pk])
        client_b.post(update_url, {"action": "increase", "next": "/"})
        item_b.refresh_from_db()
        self.assertEqual(item_b.quantity, 2)
        client_b.post(update_url, {"action": "decrease", "next": "/"})
        item_b.refresh_from_db()
        self.assertEqual(item_b.quantity, 1)
        client_b.post(reverse("cart_remove", args=[item_b.pk]), {"next": "/"})

        self.assertFalse(CartItem.objects.filter(cart__user=self.user_b).exists())
        self.assertTrue(CartItem.objects.filter(cart__user=self.user_a, pk=item_a.pk).exists())

    def test_cart_changes_require_login_and_csrf(self):
        guest = Client(enforce_csrf_checks=True)
        add_url = reverse("cart_add", args=[self.headphones.pk])
        response = guest.post(add_url, {"next": "/"})
        self.assertEqual(response.status_code, 403)

        guest.get(reverse("home"))
        csrf_token = guest.cookies["csrftoken"].value
        response = guest.post(
            add_url,
            {"next": "/"},
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        login_page = guest.get(response.url)
        self.assertContains(login_page, "Please log in to use your cart")
        self.assertFalse(Cart.objects.filter(user=self.user_a).exists())


class CheckoutRegressionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user_a = user_model.objects.create_user(
            username="checkout-user-a",
            password="test-password-123",
        )
        self.user_b = user_model.objects.create_user(
            username="checkout-user-b",
            password="test-password-123",
        )
        self.product = Product.objects.create(
            name="Checkout headphones",
            description="Test item",
            price=Decimal("1799.50"),
            image_path="store/images/test-headphones.jpg",
        )
        self.cart = Cart.objects.create(user=self.user_a)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )
        self.client.force_login(self.user_a)
        self.delivery = {
            "full_name": "Asha Example",
            "phone": "+919876543210",
            "address_line": "12 Sample Road",
            "city": "Pune",
            "state": "Maharashtra",
            "postal_code": "411001",
        }

    def test_checkout_uses_database_prices_snapshots_items_and_clears_cart(self):
        response = self.client.post(
            reverse("checkout"),
            {**self.delivery, "total": "0.01", "unit_price": "0.01"},
        )
        order = Order.objects.get(user=self.user_a)
        order_item = OrderItem.objects.get(order=order)

        self.assertRedirects(
            response,
            reverse("order_confirmation", args=[order.reference]),
        )
        self.assertEqual(order.total, Decimal("3599.00"))
        self.assertEqual(order_item.product_name, "Checkout headphones")
        self.assertEqual(order_item.unit_price, Decimal("1799.50"))
        self.assertEqual(order_item.quantity, 2)
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())

        self.product.name = "Renamed headphones"
        self.product.price = Decimal("9999.00")
        self.product.save(update_fields=["name", "price"])
        order_item.refresh_from_db()
        self.assertEqual(order_item.product_name, "Checkout headphones")
        self.assertEqual(order_item.unit_price, Decimal("1799.50"))
        self.assertEqual(order_item.subtotal, Decimal("3599.00"))
        self.assertContains(self.client.get(response.url), "Checkout headphones")

    def test_empty_cart_and_invalid_delivery_details_do_not_create_orders(self):
        CartItem.objects.filter(cart=self.cart).delete()
        empty = self.client.post(reverse("checkout"), self.delivery)
        self.assertEqual(empty.status_code, 400)
        self.assertContains(empty, "Your cart is empty", status_code=400)
        self.assertFalse(Order.objects.exists())

        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)
        invalid = self.client.post(
            reverse("checkout"),
            {**self.delivery, "phone": "123", "postal_code": "abc"},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertContains(invalid, "Enter a valid phone number", status_code=400)
        self.assertContains(invalid, "valid 6-digit Indian PIN code", status_code=400)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 1)

    def test_checkout_revalidates_product_availability(self):
        self.product.is_available = False
        self.product.save(update_fields=["is_available"])
        response = self.client.post(reverse("checkout"), self.delivery)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "unavailable item", status_code=400)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())

    def test_confirmation_is_private_and_checkout_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user_a)
        csrf_client.get(reverse("checkout"))
        response = csrf_client.post(reverse("checkout"), self.delivery)
        self.assertEqual(response.status_code, 403)
        response = csrf_client.post(
            reverse("checkout"),
            self.delivery,
            HTTP_X_CSRFTOKEN=csrf_client.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user_a)

        client_b = Client()
        client_b.force_login(self.user_b)
        response = client_b.get(reverse("order_confirmation", args=[order.reference]))
        self.assertEqual(response.status_code, 404)

    def test_failed_order_item_creation_rolls_back_order_and_preserves_cart(self):
        with patch(
            "store.views.OrderItem.objects.bulk_create",
            side_effect=RuntimeError("test failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("checkout"), self.delivery)

        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())


class OrderHistoryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user_a = user_model.objects.create_user(
            username="history-user-a",
            password="test-password-123",
        )
        self.user_b = user_model.objects.create_user(
            username="history-user-b",
            password="test-password-123",
        )
        self.product = Product.objects.create(
            name="Saved headphones",
            description="Test product",
            price=Decimal("1200.00"),
            image_path="store/images/test-headphones.jpg",
        )

    def create_order(self, user, *, created_at=None):
        order = Order.objects.create(
            user=user,
            full_name="Ravi Buyer",
            phone="9876543210",
            address_line="45 Example Street",
            city="Jaipur",
            state="Rajasthan",
            postal_code="302001",
            total=Decimal("2400.00"),
        )
        if created_at is not None:
            Order.objects.filter(pk=order.pk).update(created_at=created_at)
            order.refresh_from_db()
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name="Headphones at purchase",
            unit_price=Decimal("1200.00"),
            quantity=2,
        )
        return order

    def test_order_list_is_newest_first_and_scoped_to_signed_in_user(self):
        older = self.create_order(
            self.user_a,
            created_at=timezone.now() - timedelta(days=2),
        )
        newer = self.create_order(self.user_a)
        other_user_order = self.create_order(self.user_b)
        self.client.force_login(self.user_a)

        response = self.client.get(reverse("order_history"))

        self.assertEqual(response.status_code, 200)
        orders = list(response.context["orders"])
        self.assertEqual([order.pk for order in orders], [newer.pk, older.pk])
        self.assertNotContains(response, str(other_user_order.reference))
        self.assertContains(response, str(newer.reference))
        self.assertContains(response, "₹2400.00")
        self.assertContains(response, "Placed")

    def test_order_detail_uses_saved_item_and_delivery_snapshots(self):
        order = self.create_order(self.user_a)
        self.client.force_login(self.user_a)

        response = self.client.get(reverse("order_detail", args=[order.reference]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Headphones at purchase")
        self.assertContains(response, "2 × ₹1200.00 each")
        self.assertContains(response, "₹2400.00")
        self.assertContains(response, "Ravi Buyer")
        self.assertContains(response, "45 Example Street")
        self.assertContains(response, "Jaipur, Rajasthan 302001")

    def test_order_history_and_detail_require_login(self):
        order = self.create_order(self.user_a)
        guest = Client()

        history = guest.get(reverse("order_history"))
        detail = guest.get(reverse("order_detail", args=[order.reference]))

        self.assertEqual(history.status_code, 302)
        self.assertIn(reverse("login"), history.url)
        self.assertEqual(detail.status_code, 302)
        self.assertIn(reverse("login"), detail.url)

    def test_users_cannot_view_each_others_order_details(self):
        order = self.create_order(self.user_a)
        self.client.force_login(self.user_b)

        response = self.client.get(reverse("order_detail", args=[order.reference]))

        self.assertEqual(response.status_code, 404)
