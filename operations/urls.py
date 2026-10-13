from django.urls import path
from . import views
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/products/", views.products_api, name="products_api"),
    path("api/products/<int:product_id>/", views.product_detail_api, name="product_detail_api"),
    path("api/orders/", views.orders_api, name="orders_api"),
    path("api/chat/", views.chat_api, name="chat_api"),
    path("api/agents/<str:agent_name>/", views.agent_run_api, name="agent_run_api",),
    path("api/metrics/", views.metrics_api, name="metrics_api"),
    path("api/approvals/", views.approvals_api, name="approvals_api"),
    path("api/approvals/create/", views.create_approval_api, name="create_approval_api"),
    path("api/agents/<str:agent_name>/", views.agent_run_api, name="agent_run_api",),
]
