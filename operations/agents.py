"""
Deterministic agent layer for a fully runnable local demo.
The interface is intentionally provider-agnostic; optional LLM providers can be
plugged into answer_with_llm() without making the core app depend on API keys.
"""
from decimal import Decimal
from django.db.models import Sum, Count, F
from .models import Product, Order, ApprovalRequest

class AgentResult:
    def __init__(self, agent, message, data=None, actions=None):
        self.agent, self.message = agent, message
        self.data, self.actions = data or {}, actions or []
    def as_dict(self):
        return {"agent": self.agent, "message": self.message, "data": self.data, "actions": self.actions}

class InventoryAgent:
    name = "Inventory Agent"
    def run(self, query):
        low = Product.objects.filter(active=True, stock__lte=F("reorder_level")).order_by("stock")
        products = list(low.values("id","name","sku","stock","reorder_level")[:10])
        if any(w in query.lower() for w in ("stock", "inventory", "low", "reorder", "available")):
            if products:
                lines = ", ".join(f'{p["name"]}: {p["stock"]} left' for p in products)
                return AgentResult(self.name, f"Inventory check: {lines}. Items at or below their reorder level are flagged for review.", {"low_stock": products})
            return AgentResult(self.name, "Inventory looks healthy: no active products are at or below their reorder level.", {"low_stock":[]})
        return None

class SalesAgent:
    name = "Sales Agent"
    def run(self, query):
        q = query.lower()
        if not any(w in q for w in ("order", "buy", "purchase", "sales", "checkout")):
            return None
        products = Product.objects.filter(active=True)
        matches = [p for p in products if p.name.lower() in q or p.category.lower() in q or p.sku.lower() in q]
        if matches:
            p = matches[0]
            if p.stock < 1:
                return AgentResult(self.name, f"{p.name} is currently out of stock. I can flag it for restock review.", {"product_id":p.id})
            return AgentResult(self.name, f"{p.name} is available at ₹{p.price}. There are {p.stock} units in stock. To protect customers, this demo does not place an order without a confirmed checkout.", {"product_id":p.id,"price":str(p.price),"stock":p.stock})
        return AgentResult(self.name, "I can help with product availability and order guidance. Ask about a product name, category, or existing order; use the catalog below to browse available items.")

class SupportAgent:
    name = "Customer Support Agent"
    def run(self, query):
        q = query.lower()
        if any(w in q for w in ("return","refund","cancel","delivery","shipping","track","support","complaint","order status")):
            return AgentResult(self.name, "I can help with order status, delivery, cancellation, and returns. For safety, cancellations and refunds require an authorized human review. Share an order ID for a status lookup, or ask the supervisor to create an approval request.")
        return None

class RecommendationAgent:
    name = "Recommendation Agent"
    def run(self, query):
        q = query.lower()
        if any(w in q for w in ("recommend","suggest","similar","best","popular","routine")):
            qs = Product.objects.filter(active=True, stock__gt=0).order_by("-rating","price")[:4]
            items = [{"id":p.id,"name":p.name,"category":p.category,"price":str(p.price),"rating":str(p.rating)} for p in qs]
            if items:
                return AgentResult(self.name, "Here are a few in-stock, highly rated options from the catalog.", {"recommendations":items})
            return AgentResult(self.name, "There are no active in-stock products to recommend yet. Add products in the admin dashboard.")
        return None

class AnalyticsAgent:
    name = "Analytics Agent"
    def run(self, query):
        if any(w in query.lower() for w in ("analytics","report","revenue","insight","performance","metrics","dashboard")):
            total = Order.objects.exclude(status="cancelled").aggregate(v=Sum("total"))["v"] or Decimal("0")
            count = Order.objects.count()
            low = Product.objects.filter(active=True, stock__lte=F("reorder_level")).count()
            return AgentResult(self.name, f"Operations snapshot: {count} orders recorded, ₹{total} in non-cancelled order value, and {low} products at/below reorder level.", {"orders":count,"order_value":str(total),"low_stock_count":low})
        return None

class SupervisorAgent:
    def __init__(self):
        self.agents = [InventoryAgent(), SalesAgent(), SupportAgent(), RecommendationAgent(), AnalyticsAgent()]
    def run(self, query):
        q = query.strip()
        if not q:
            return AgentResult("Supervisor Agent", "Please enter a question so I can route it to the right specialist.")
        # Keyword specialist routing makes the project work with no external LLM key.
        for agent in self.agents:
            result = agent.run(q)
            if result:
                result.data["supervisor"] = "Supervisor Agent"
                return result
        # Lightweight product knowledge retrieval (database-backed RAG baseline).
        terms = [t.strip(".,?!") for t in q.split() if len(t.strip(".,?!")) >= 3]
        matches = Product.objects.filter(active=True)
        for term in terms[:6]:
            found = matches.filter(name__icontains=term) | matches.filter(category__icontains=term) | matches.filter(description__icontains=term)
            if found.exists():
                p = found.first()
                return AgentResult("Product Knowledge (RAG)", f"{p.name} — {p.description or 'No description added yet'} Price: ₹{p.price}. Category: {p.category}. Stock: {p.stock}.", {"product_id":p.id,"sku":p.sku,"price":str(p.price),"stock":p.stock,"retrieval":"PostgreSQL catalog keyword retrieval","supervisor":"Supervisor Agent"})
        return AgentResult("Supervisor Agent", "I couldn't confidently match that request to a specialist or catalog item. Try asking about stock, sales, an order, returns, recommendations, analytics, or a product category.")
