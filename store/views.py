import json
import re
from django.db.models import Q
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from operations.models import Conversation, Product, Order
from operations.agents import SupervisorAgent

def home(request):
    products = Product.objects.filter(active=True).order_by("name")

    search_query = request.GET.get("q", "").strip()

    # Search by product name, category, description, or SKU
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(sku__icontains=search_query)
        )

    category = request.GET.get("category", "").strip()
    if category:
        products = products.filter(category__iexact=category)

    categories = (
        Product.objects.filter(active=True)
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    return render(
        request,
        "store/home.html",
        {
            "products": products,
            "categories": categories,
            "search_query": search_query,
        },
    )

def cart(request):
    cart_data = request.session.get("cart", {})
    cart_items = []
    total = Decimal("0.00")

    for product_id, quantity in cart_data.items():
        try:
            product = Product.objects.get(
                pk=int(product_id),
                active=True
            )
            quantity = int(quantity)

            if quantity < 1:
                continue

            subtotal = product.price * quantity

            cart_items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal,
            })

            total += subtotal

        except (Product.DoesNotExist, ValueError, TypeError):
            continue

    return render(request, "store/cart.html", {
        "rows": cart_items,
        "total": total,
    })


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(
        Product,
        pk=product_id,
        active=True,
    )

    cart_data = request.session.get("cart", {})
    key = str(product.id)

    try:
        quantity = int(cart_data.get(key, 0))
    except (ValueError, TypeError):
        quantity = 0

    if product.stock <= quantity:
        messages.error(request, "No more stock is available.")
    else:
        cart_data[key] = quantity + 1
        request.session["cart"] = cart_data
        request.session.modified = True
        messages.success(
            request,
            f"{product.name} added to your cart.",
        )

    return redirect("store:cart")


@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, active=True)

    cart_data = request.session.get("cart", {})

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        messages.error(request, "Please enter a valid quantity.")
        return redirect("store:cart")

    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
    elif quantity > product.stock:
        messages.error(
            request,
            f"Only {product.stock} units of {product.name} are available."
        )
    else:
        cart_data[str(product.id)] = quantity
        request.session["cart"] = cart_data
        request.session.modified = True
        messages.success(request, "Cart quantity updated.")

    return redirect("store:cart")

@require_POST
def remove_from_cart(request, product_id):
    cart_data = request.session.get("cart", {})
    cart_data.pop(str(product_id), None)
    request.session["cart"] = cart_data
    return redirect("store:cart")


@login_required
def checkout(request):
    cart_data = request.session.get("cart", {})
    cart_items = []
    total = Decimal("0.00")

    for product_id, quantity in cart_data.items():
        try:
            product = Product.objects.get(
                pk=int(product_id),
                active=True
            )
            quantity = int(quantity)

            if quantity < 1:
                continue

            subtotal = product.price * quantity
            cart_items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal,
            })
            total += subtotal

        except (Product.DoesNotExist, ValueError, TypeError):
            continue

    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect("store:cart")

    if request.method == "POST":
        
        name = request.POST.get("customer_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        if not name or not phone or not address:
            messages.error(request, "Please fill in all delivery details.")
        else:
            try:
                with transaction.atomic():
                    # Lock product rows and validate stock before creating orders.
                    for item in cart_items:
                        product = Product.objects.select_for_update().get(
                            pk=item["product"].pk
                        )
                        if (
                            not product.active
                            or product.stock < item["quantity"]
                        ):
                            raise ValueError(
                                f"Insufficient stock for {product.name}."
                            )

                    for item in cart_items:
                        product = Product.objects.select_for_update().get(
                            pk=item["product"].pk
                        )

                        Order.objects.create(
                            customer=request.user,
                            customer_name=name,
                            customer_email=request.user.email,
                            customer_phone=phone,
                            shipping_address=address,
                            payment_method="cod",
                            product=product,
                            quantity=item["quantity"],
                            total=item["subtotal"],
                            status="pending",
                        )

                        # Reserve stock now; don't deduct it again when
                        # an order is approved in the operations workflow.
                        product.stock -= item["quantity"]
                        product.save(update_fields=["stock"])

                request.session["cart"] = {}
                messages.success(
                    request,
                    "Your order has been placed successfully."
                )
                return redirect("store:orders")

            except ValueError as exc:
                messages.error(request, str(exc))
            except Product.DoesNotExist:
                messages.error(
                    request,
                    "A product in your cart is no longer available."
                )

    return render(request, "store/checkout.html", {
        "cart_items": cart_items,
        "total": total,
    })


@login_required
def orders(request):
    customer_orders = (
        Order.objects.filter(customer=request.user)
        .select_related("product")
        .prefetch_related("status_history")
        .order_by("-created_at")
    )

    return render(
        request,
        "store/orders.html",
        {"orders": customer_orders},
    )

def register(request):
    from django.contrib.auth.forms import UserCreationForm
    from django.contrib.auth import login

    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("store:home")
    else:
        form = UserCreationForm()

    return render(
        request,
        "store/auth.html",
        {
            "form": form,
            "mode": "register",
        },
    )


def login_view(request):
    from django.contrib.auth.forms import AuthenticationForm
    from django.contrib.auth import login

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            return redirect("store:home")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "store/auth.html",
        {
            "form": form,
            "mode": "login",
        },
    )


def logout_view(request):
    logout(request)
    return redirect("store:home")

def product_detail(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        active=True
    )

    return render(
        request,
        "store/product_detail.html",
        {"product": product}
    )
    

def get_live_order_answer(user, message):
    """
    Answer order-status questions using the current database record.
    Customers can only retrieve their own orders.
    """
    text = message.lower()

    tracking_words = (
        "order", "track", "tracking", "status",
        "where is", "shipped", "delivered",
        "approved", "processing", "transit",
    )

    if not any(word in text for word in tracking_words):
        return None

    # Extract an order number from messages such as:
    # "Where is my order with order ID 25?"
    patterns = [
        r"order\s*(?:id|number|no\.?)\s*[:#-]?\s*(\d+)",
        r"order\s*#\s*(\d+)",
        r"#\s*(\d+)",
    ]

    order_id = None

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            order_id = int(match.group(1))
            break

    if order_id is None:
        return (
            "I'd be happy to check your order. "
            "Could you share your order ID?"
        )

    # Always scope the query to the currently logged-in customer.
    order = Order.objects.filter(
        pk=order_id,
        customer=user,
    ).select_related("product").first()

    if order is None:
        return (
            f"I couldn't find order #{order_id} in your account. "
            "Please check the order ID and try again."
        )

    status_messages = {
    "pending": "Your order has been placed and is awaiting approval.",
    "approved": "Your order has been approved and is awaiting packing.",
    "packed": "Your product has been packed.",
    "dispatched": "Your order has been dispatched from the warehouse.",
    "in_transit": "Your order is currently in transit.",
    "out_for_delivery": "Your order is out for delivery.",
    "delivered": "Your order has been delivered successfully.",
    "cancelled": "Your order has been cancelled.",
}

    status_text = status_messages.get(
        order.status,
        f"Your order status is {order.get_status_display()}.",
    )

    return (
        f"I checked the latest details for order #{order.pk}. "
        f"Your product is {order.product.name}. "
        f"Current status: {order.get_status_display()}. "
        f"{status_text}"
    )


@require_POST
def chat(request):
    message = request.POST.get("message", "").strip()

    if not message:
        return JsonResponse(
            {"error": "Please enter a message."},
            status=400,
        )

    try:
        # Check the actual order database first.
        live_answer = get_live_order_answer(
            request.user,
            message,
        )

        customer_name = (
            request.user.username
            if request.user.is_authenticated
            else "Website visitor"
        )

        if live_answer is not None:
            agent_name = "Order Tracking Agent"
            response_text = live_answer

            Conversation.objects.create(
                customer_name=customer_name,
                user_message=message,
                agent_name=agent_name,
                response=response_text,
            )

            return JsonResponse({
                "agent": agent_name,
                "message": response_text,
            })

        # Route other questions to the existing multi-agent system.
        result = SupervisorAgent().run(message)

        if result is None:
            return JsonResponse({
                "agent": "AI Assistant",
                "message": (
                    "I couldn't match that question. "
                    "Please try asking about products, orders, "
                    "or shopping assistance."
                ),
            })

        Conversation.objects.create(
            customer_name=customer_name,
            user_message=message,
            agent_name=result.agent,
            response=result.message,
        )

        return JsonResponse(result.as_dict())

    except Exception:
        return JsonResponse(
            {
                "error": (
                    "The AI assistant is temporarily unavailable. "
                    "Please try again."
                )
            },
            status=500,
        )

