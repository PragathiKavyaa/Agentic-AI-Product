
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import Product, Order, OrderStatusHistory, Conversation, ApprovalRequest


# Customize the existing Django User admin
admin.site.unregister(User)

class CustomUserAdmin(UserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = ("is_staff", "is_active", "is_superuser")
    ordering = ("id",)

admin.site.register(User, CustomUserAdmin)


# Product Admin

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "sku", "category",
        "price", "stock", "active"
    )
    search_fields = ("name", "sku", "category")
    list_filter = ("category", "active")
    list_editable = ("price", "stock", "active")


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    fields = ("status", "updated_at", "updated_by")
    readonly_fields = ("status", "updated_at", "updated_by")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "product",
        "quantity",
        "total",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("customer_name", "customer_email")
    readonly_fields = ("created_at",)
    inlines = [OrderStatusHistoryInline]

    def save_model(self, request, obj, form, change):
        old_status = None

        if change:
            old_status = (
                Order.objects.filter(pk=obj.pk)
                .values_list("status", flat=True)
                .first()
            )

        super().save_model(request, obj, form, change)

        if not change or old_status != obj.status:
            OrderStatusHistory.objects.create(
                order=obj,
                status=obj.status,
                updated_by=request.user,
            )

# Conversation Admin
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "agent_name", "customer_name", "created_at"
    )


# Approval Admin
@admin.register(ApprovalRequest)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "id", "action_type", "status",
        "requested_by", "created_at"
    )
