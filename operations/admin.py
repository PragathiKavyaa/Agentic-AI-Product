
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import Product, Order, Conversation, ApprovalRequest


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


# Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer_name", "product",
        "quantity", "total", "status", "created_at"
    )
    list_filter = ("status",)


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
