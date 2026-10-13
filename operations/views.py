import json
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import F, Sum
from django.utils import timezone
from .models import Product, Order, Conversation, ApprovalRequest
from .agents import (
    SupervisorAgent,
    SalesAgent,
    InventoryAgent,
    SupportAgent,
    RecommendationAgent,
    AnalyticsAgent,
)

@ensure_csrf_cookie
def dashboard(request):
    return render(request, "dashboard.html")

def parse_body(request):
    try: return json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError): return None

def product_dict(p):
    return {"id":p.id,"name":p.name,"sku":p.sku,"category":p.category,"description":p.description,"price":str(p.price),"stock":p.stock,"reorder_level":p.reorder_level,"rating":str(p.rating),"image_url":p.image_url,"active":p.active}

@require_http_methods(["GET","POST"])
def products_api(request):
    if request.method == "GET":
        qs = Product.objects.filter(active=True).order_by("name")
        category = request.GET.get("category")
        q = request.GET.get("q")
        if category: qs = qs.filter(category__iexact=category)
        if q: qs = qs.filter(name__icontains=q) | qs.filter(category__icontains=q) | qs.filter(sku__icontains=q)
        return JsonResponse({"products":[product_dict(p) for p in qs]})
    body = parse_body(request)
    if body is None: return HttpResponseBadRequest("Invalid JSON")
    try:
        p = Product.objects.create(name=body["name"].strip(), sku=body["sku"].strip(), category=body["category"].strip(), description=body.get("description",""), price=Decimal(str(body["price"])), stock=int(body.get("stock",0)), reorder_level=int(body.get("reorder_level",5)), rating=Decimal(str(body.get("rating",4.5))), image_url=body.get("image_url",""))
    except (KeyError, ValueError, TypeError, InvalidOperation) as e:
        return JsonResponse({"error":f"Check required fields and numeric values: {e}"}, status=400)
    except Exception as e:
        return JsonResponse({"error":str(e)}, status=400)
    return JsonResponse({"product":product_dict(p)}, status=201)

@require_http_methods(["GET","PUT","DELETE"])
def product_detail_api(request, product_id):
    p = get_object_or_404(Product, pk=product_id)
    if request.method == "GET": return JsonResponse({"product":product_dict(p)})
    if request.method == "DELETE":
        p.active = False; p.save(update_fields=["active","updated_at"])
        return JsonResponse({"message":"Product archived"})
    body = parse_body(request)
    if body is None: return HttpResponseBadRequest("Invalid JSON")
    try:
        for key in ("name","sku","category","description","image_url"):
            if key in body: setattr(p,key,body[key])
        for key in ("price","rating"):
            if key in body: setattr(p,key,Decimal(str(body[key])))
        for key in ("stock","reorder_level"):
            if key in body: setattr(p,key,int(body[key]))
        p.save()
        return JsonResponse({"product":product_dict(p)})
    except Exception as e: return JsonResponse({"error":str(e)}, status=400)

@require_http_methods(["GET","POST"])
def orders_api(request):
    if request.method == "GET":
        qs = Order.objects.select_related("product").order_by("-created_at")[:50]
        return JsonResponse({"orders":[{"id":o.id,"customer_name":o.customer_name,"customer_email":o.customer_email,"product":o.product.name,"product_id":o.product_id,"quantity":o.quantity,"total":str(o.total),"status":o.status,"created_at":o.created_at.isoformat()} for o in qs]})
    body = parse_body(request)
    if body is None: return HttpResponseBadRequest("Invalid JSON")
    try:
        p = Product.objects.get(pk=int(body["product_id"]),active=True)
        qty = int(body.get("quantity",1))
        if qty < 1: raise ValueError("Quantity must be at least 1")
        if p.stock < qty: return JsonResponse({"error":"Insufficient stock"},status=409)
        order = Order.objects.create(customer_name=body["customer_name"].strip(),customer_email=body.get("customer_email",""),product=p,quantity=qty,total=p.price*qty,status="pending")
        approval = ApprovalRequest.objects.create(action_type="stock_update",payload={"product_id":p.id,"quantity":qty,"order_id":order.id},reason="Order created; stock deduction requires approval.")
        return JsonResponse({"order_id":order.id,"status":order.status,"approval_id":approval.id,"message":"Order request created and queued for review."},status=201)
    except (KeyError,ValueError,Product.DoesNotExist) as e: return JsonResponse({"error":str(e)},status=400)

@require_http_methods(["POST"])
def chat_api(request):
    body = parse_body(request)
    if body is None: return HttpResponseBadRequest("Invalid JSON")
    message = str(body.get("message","")).strip()
    if not message: return JsonResponse({"error":"Message is required"},status=400)
    result = SupervisorAgent().run(message)
    Conversation.objects.create(customer_name=str(body.get("customer_name","Website visitor"))[:120],user_message=message,agent_name=result.agent,response=result.message)
    return JsonResponse(result.as_dict())

def metrics_api(request):
    orders = Order.objects.all()
    value = orders.exclude(status="cancelled").aggregate(v=Sum("total"))["v"] or Decimal("0")
    return JsonResponse({
        "products":Product.objects.filter(active=True).count(),
        "orders":orders.count(),
        "revenue":str(value),
        "low_stock":Product.objects.filter(active=True,stock__lte=F("reorder_level")).count(),
        "pending_approvals":ApprovalRequest.objects.filter(status="pending").count(),
        "recent_conversations":Conversation.objects.count(),
    })

@require_http_methods(["POST"])
def agent_run_api(request, agent_name):
    body = parse_body(request)

    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    message = str(body.get("message", "")).strip()

    if not message:
        return JsonResponse(
            {"error": "Message is required"},
            status=400
        )

    agent_classes = {
        "supervisor": SupervisorAgent,
        "sales": SalesAgent,
        "inventory": InventoryAgent,
        "support": SupportAgent,
        "recommendation": RecommendationAgent,
        "analytics": AnalyticsAgent,
    }

    agent_class = agent_classes.get(agent_name.lower())

    if agent_class is None:
        return JsonResponse(
            {"error": "Unknown agent"},
            status=404
        )

    agent = agent_class()
    result = agent.run(message)

    if result is None:
        return JsonResponse({
            "agent": agent.name,
            "message": (
                "This agent could not match the request. "
                "Try a question related to its specialty."
            ),
            "data": {},
            "actions": [],
        })

    Conversation.objects.create(
        customer_name="Dashboard operator",
        user_message=message,
        agent_name=result.agent,
        response=result.message,
    )

    return JsonResponse(result.as_dict())

@require_http_methods(["GET", "POST"])
def approvals_api(request):
    if request.method == "GET":
        qs = ApprovalRequest.objects.order_by("-created_at")[:50]
        return JsonResponse({
            "approvals": [
                {
                    "id": a.id,
                    "action_type": a.action_type,
                    "payload": a.payload,
                    "reason": a.reason,
                    "status": a.status,
                    "created_at": a.created_at.isoformat()
                }
                for a in qs
            ]
        })

    body = parse_body(request)
    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    try:
        approval = ApprovalRequest.objects.get(
            pk=int(body["id"]),
            status="pending"
        )
    except (KeyError, ValueError, TypeError, ApprovalRequest.DoesNotExist):
        return JsonResponse(
            {"error": "Pending approval not found"},
            status=404
        )

    decision = body.get("decision")
    if decision not in ("approve", "reject"):
        return JsonResponse(
            {"error": "decision must be approve or reject"},
            status=400
        )

    if decision == "approve":
        payload = approval.payload

        if not isinstance(payload, dict):
            return JsonResponse(
                {"error": "Invalid approval payload"},
                status=400
            )

        # Handle accidentally nested payloads
        if isinstance(payload.get("payload"), dict):
            payload = payload["payload"]

        if approval.action_type == "stock_update":
            if "product_id" not in payload or "quantity" not in payload:
                return JsonResponse({
                    "error": "Approval payload must contain product_id and quantity",
                    "payload": payload
                }, status=400)

            try:
                p = Product.objects.get(pk=int(payload["product_id"]))
                qty = int(payload["quantity"])
            except (Product.DoesNotExist, ValueError, TypeError):
                return JsonResponse({
                    "error": "Invalid product_id or quantity"
                }, status=400)

            if qty < 1:
                return JsonResponse({
                    "error": "Quantity must be at least 1"
                }, status=400)

            if p.stock < qty:
                return JsonResponse({
                    "error": "Not enough stock to approve this request",
                    "available_stock": p.stock,
                    "requested_quantity": qty
                }, status=409)

            p.stock -= qty
            p.save(update_fields=["stock", "updated_at"])

            if payload.get("order_id"):
                Order.objects.filter(
                    pk=payload["order_id"]
                ).update(status="approved")

        elif approval.action_type == "order_cancel":
            Order.objects.filter(
                pk=payload.get("order_id")
            ).update(status="cancelled")

        elif approval.action_type == "price_update":
            try:
                price = Decimal(str(payload["price"]))
                if price < 0:
                    raise ValueError
                Product.objects.filter(
                    pk=payload["product_id"]
                ).update(price=price)
            except (KeyError, ValueError, TypeError, InvalidOperation):
                return JsonResponse({
                    "error": "Valid product_id and price are required"
                }, status=400)

        approval.status = "approved"

    else:
        approval.status = "rejected"

        if (
            approval.action_type == "stock_update"
            and approval.payload.get("order_id")
        ):
            Order.objects.filter(
                pk=approval.payload["order_id"]
            ).update(status="cancelled")

    approval.reviewed_by = str(
        body.get("reviewed_by", "Dashboard reviewer")
    )[:120]
    approval.reviewed_at = timezone.now()
    approval.save()

    return JsonResponse({
        "message": f"Request {approval.status}",
        "status": approval.status
    })



@require_http_methods(["POST"])
def create_approval_api(request):
    body = parse_body(request)

    if body is None:
        return HttpResponseBadRequest("Invalid JSON")

    action_type = body.get("action_type")

    if action_type not in ("stock_update", "order_cancel", "price_update"):
        return JsonResponse({"error": "Unsupported action_type"}, status=400)

    payload = body.get("payload", {})

    # Fix accidentally nested payload data
    if isinstance(payload, dict) and isinstance(payload.get("payload"), dict):
        payload = payload["payload"]

    if not isinstance(payload, dict):
        return JsonResponse({"error": "payload must be a JSON object"}, status=400)

    if action_type == "stock_update":
        if "product_id" not in payload or "quantity" not in payload:
            return JsonResponse(
                {"error": "Stock update requires product_id and quantity"},
                status=400
            )

    approval = ApprovalRequest.objects.create(
        action_type=action_type,
        payload=payload,
        reason=body.get("reason", "Created from dashboard"),
        requested_by=body.get("requested_by", "AI Supervisor")
    )

    return JsonResponse(
        {"id": approval.id, "status": approval.status},
        status=201
    )

