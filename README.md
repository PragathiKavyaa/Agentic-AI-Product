# Orchestra AI — Multi-Agent E-Commerce Operations

A runnable Django + PostgreSQL website demonstrating a multi-agent e-commerce operations workflow. The frontend uses HTML, CSS, and vanilla JavaScript. It includes a dashboard, product catalog CRUD, order requests, human approval queue, specialist agents, product knowledge retrieval, and metrics.

## Included features

- Supervisor Agent routes questions to Sales, Inventory, Customer Support, Recommendation, and Analytics agents.
- PostgreSQL-backed product catalog and orders.
- Catalog search, add, edit, and archive from the browser.
- Inventory checks and reorder-level alerts.
- Recommendation agent ranks active, in-stock products by rating.
- Analytics agent reports order counts, order value, and low-stock counts.
- Database keyword retrieval as a simple RAG baseline.
- Human-in-the-loop approval workflow: stock deductions and order requests are not applied until approved.
- Django Admin at `/admin/`.
- Docker Compose for Django, PostgreSQL, and Redis.
- Optional integration points for GPT/Gemini/Llama, LangChain/LangGraph, vector DB, MCP, and Redis.

## Requirements

- Python 3.11 or newer (Python 3.12 recommended)
- PostgreSQL 14+ (or Docker Desktop)
- Git (optional)
- A modern browser

## Quick start on Windows PowerShell

### Option A — Docker (easiest)

Install and start Docker Desktop, then in this project directory run:

```powershell
docker compose up --build
```

Open `http://127.0.0.1:8000`. The container applies migrations and inserts demo products automatically. Stop with `Ctrl+C`; run `docker compose down` to stop services. Data persists in the Docker volume. To reset data, run `docker compose down -v` (this deletes the database volume).

### Option B — Local Python + PostgreSQL

1. Install PostgreSQL and create a database:

```sql
CREATE DATABASE ecommerce_agents;
```

2. Create a virtual environment and install packages:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Edit `.env` and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` to match your PostgreSQL setup. Set a new `DJANGO_SECRET_KEY` before deployment.
4. Run migrations and add sample data:

```powershell
python manage.py makemigrations operations
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

5. Visit `http://127.0.0.1:8000`. Admin: `http://127.0.0.1:8000/admin/`.

> The database settings intentionally use PostgreSQL. SQLite is not configured as a fallback.

## Demo agent prompts

Try these in the dashboard chat:

- `Check inventory and low stock`
- `Recommend the best products`
- `Show analytics and revenue insights`
- `Help with an order cancellation`
- `What is the Radiant Glow Serum?`
- `Can I buy lipsticks?`

The rule-based agent engine is deliberately the default so the demo works without a paid API key. It is a functional baseline, not a production-grade autonomous LLM agent.

## API reference

All API routes are served by Django. JSON request bodies are expected for POST/PUT requests.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/metrics/` | Dashboard metrics |
| GET | `/api/products/` | Active catalog |
| GET | `/api/products/?q=serum` | Search products |
| GET | `/api/products/?category=Skincare` | Filter category |
| POST | `/api/products/` | Create product |
| GET | `/api/products/<id>/` | Read product |
| PUT | `/api/products/<id>/` | Update product |
| DELETE | `/api/products/<id>/` | Archive product |
| GET | `/api/orders/` | Recent orders |
| POST | `/api/orders/` | Create pending order + approval request |
| POST | `/api/chat/` | Ask the supervisor agent |
| GET | `/api/approvals/` | List approval requests |
| POST | `/api/approvals/` | Approve/reject request |
| POST | `/api/approvals/create/` | Create a manual approval request |

### Example PowerShell chat request

```powershell
$body = @{ message = "Check inventory and low stock" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat/" -Method Post -ContentType "application/json" -Body $body
```

### Example create product request

```powershell
$body = @{
  name = "Daily Hydration Cream"
  sku = "SKN-007"
  category = "Skincare"
  description = "Daily moisturizing cream"
  price = 599
  stock = 20
  reorder_level = 5
  rating = 4.6
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/products/" -Method Post -ContentType "application/json" -Body $body
```

### Example create order request

```powershell
$body = @{ customer_name = "Demo Customer"; customer_email = "demo@example.com"; product_id = 1; quantity = 2 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/orders/" -Method Post -ContentType "application/json" -Body $body
```

## Architecture

```text
Browser (HTML/CSS/JavaScript)
            |
            v
       Django Views / JSON API
            |
            v
       Supervisor Agent
       /   /  |  \\   \\
   Sales Inventory Support Recommendations Analytics
            |
      PostgreSQL catalog / orders / conversations / approvals
            |
      Human reviewer approves sensitive business operations
```

## Production-hardening checklist

This is a development/demo project. Before public production use:
- Use Django authentication and permissions for catalog changes and approval endpoints.
- Replace `runserver` with Gunicorn/Uvicorn and configure HTTPS.
- Set `DEBUG=False`, a strong secret key, trusted hosts, secure cookies, and managed secrets.
- Add rate limits, audit logs, tests, backups, monitoring, and error reporting.
- Add policy validation and idempotency around order/stock updates.
- Do not let an LLM directly execute sensitive operations; validate tool arguments and require explicit authorization.
- Configure provider APIs, vector storage, MCP servers, and Redis caching/queues intentionally; packages and environment placeholders alone do not activate these integrations.

## LLM / LangGraph / vector search extension points

The demo's `operations/agents.py` is the clear integration seam. Replace or augment `SupervisorAgent.run()` with a LangGraph state graph and specialist nodes. Use a provider adapter for OpenAI, Gemini, or a locally hosted Llama model. For semantic RAG, embed product descriptions and store vectors in pgvector or another vector database, retrieve grounded product context, and pass only that context to the model. Add MCP tools as explicit, schema-validated capabilities and keep approval checks around stock, refunds, price changes, and order cancellations.

## Troubleshooting

- PostgreSQL connection refused: ensure PostgreSQL/Docker is running and `.env` host/port/password match.
- `No module named django`: activate `.venv`, then `pip install -r requirements.txt`.
- `relation does not exist`: run `python manage.py migrate`.
- Empty catalog: run `python manage.py seed_demo`.
- CSRF errors from API clients: use the same-origin website or send the `csrftoken` cookie plus `X-CSRFToken` header for unsafe requests.
