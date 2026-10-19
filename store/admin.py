from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_available")
    list_filter = ("is_available",)
    search_fields = ("name", "description")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("product", "quantity")
    can_delete = False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    inlines = (CartItemInline,)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product_name", "product", "quantity", "unit_price", "subtotal")
    readonly_fields = fields
    can_delete = False

    @admin.display(description="Line total")
    def subtotal(self, obj):
        return obj.subtotal

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "full_name", "status", "created_at", "total")
    list_filter = ("status", "created_at", "state")
    search_fields = ("reference", "user__username", "full_name", "phone")
    readonly_fields = (
        "reference",
        "user",
        "full_name",
        "phone",
        "address_line",
        "city",
        "state",
        "postal_code",
        "total",
        "created_at",
    )
    inlines = (OrderItemInline,)

    def has_add_permission(self, request):
        return False


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "quantity", "unit_price")
    search_fields = ("order__reference", "product_name")
    readonly_fields = ("order", "product", "product_name", "unit_price", "quantity")

    def has_add_permission(self, request):
        return False
