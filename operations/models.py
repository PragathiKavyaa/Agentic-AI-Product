from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=180)
    sku = models.CharField(max_length=60, unique=True)
    category = models.CharField(max_length=80, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=4.5)
    image_url = models.URLField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.name} ({self.sku})"

class Order(models.Model):
    STATUS_CHOICES = [("pending","Pending"),("approved","Approved"),("processing","Processing"),("shipped","Shipped"),("delivered","Delivered"),("cancelled","Cancelled")]
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField(blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="orders")
    quantity = models.PositiveIntegerField(default=1)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Order #{self.pk} - {self.customer_name}"

class Conversation(models.Model):
    customer_name = models.CharField(max_length=120, default="Website visitor")
    user_message = models.TextField()
    agent_name = models.CharField(max_length=80)
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ApprovalRequest(models.Model):
    ACTION_CHOICES = [("stock_update","Stock update"),("order_cancel","Cancel order"),("price_update","Price update")]
    STATUS_CHOICES = [("pending","Pending"),("approved","Approved"),("rejected","Rejected")]
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    payload = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_by = models.CharField(max_length=120, default="AI Supervisor")
    reviewed_by = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
