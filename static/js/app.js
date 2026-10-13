const $ = (id) => document.getElementById(id);
let products = [];
let toastTimer;
function toast(message){const el=$("toast");el.textContent=message;el.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove("show"),2800)}
function escapeHtml(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function money(v){return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:2}).format(Number(v||0))}
function csrf(){const m=document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);return m?decodeURIComponent(m[1]):""}

async function api(url, options = {}) {
    const headers = { ...(options.headers || {}) };

    if (!(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    if (options.method && options.method !== "GET") {
        headers["X-CSRFToken"] = csrf();
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    const data = await response.json().catch(() => ({
        error: "Unexpected server response"
    }));

    if (!response.ok) {
        throw new Error(
            data.error || data.message || `Request failed (${response.status})`
        );
    }

    return data;
}

const productImageInput = document.getElementById("pImageFile");
const imagePreviewWrap = document.getElementById("imagePreviewWrap");
const imagePreview = document.getElementById("imagePreview");

let imagePreviewUrl = null;

productImageInput.addEventListener("change", () => {
    const file = productImageInput.files[0];

    if (imagePreviewUrl) {
        URL.revokeObjectURL(imagePreviewUrl);
        imagePreviewUrl = null;
    }

    if (!file) {
        imagePreviewWrap.hidden = true;
        imagePreview.removeAttribute("src");
        return;
    }

    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];

    if (!allowedTypes.includes(file.type)) {
        alert("Please select a JPG, PNG, or WebP image.");
        productImageInput.value = "";
        imagePreviewWrap.hidden = true;
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        alert("Image size must not exceed 5 MB.");
        productImageInput.value = "";
        imagePreviewWrap.hidden = true;
        return;
    }

    imagePreviewUrl = URL.createObjectURL(file);
    imagePreview.src = imagePreviewUrl;
    imagePreviewWrap.hidden = false;
});

function go(section){document.querySelectorAll(".page-section").forEach(x=>x.classList.add("hidden"));$(`${section}Section`).classList.remove("hidden");document.querySelectorAll(".nav-item").forEach(x=>x.classList.toggle("active",x.dataset.section===section));const labels={overview:"OVERVIEW",catalog:"PRODUCT CATALOG",orders:"ORDERS",approvals:"APPROVAL QUEUE",agents:"AI AGENT STUDIO"};$("crumb").textContent=labels[section];$("pageTitle").innerHTML=({overview:'Good morning, operator <span>✦</span>',catalog:"Product catalog",orders:"Order management",approvals:"Approval queue",agents:"AI agent studio"})[section];if(section==="catalog")loadProducts();if(section==="orders")loadOrders();if(section==="approvals")loadApprovals()}
document.querySelectorAll(".nav-item").forEach(b=>b.addEventListener("click",()=>go(b.dataset.section)));
document.querySelectorAll("[data-go]").forEach(b=>b.addEventListener("click",()=>go(b.dataset.go)));
$("jumpChat").addEventListener("click",()=>{$("chatPanel").scrollIntoView({behavior:"smooth",block:"center"});$("chatInput").focus()});
async function loadMetrics(){try{const m=await api("/api/metrics/");$("metricProducts").textContent=m.products;$("metricOrders").textContent=m.orders;$("metricRevenue").textContent=money(m.revenue);$("metricLow").textContent=m.low_stock;$("approvalBadge").textContent=m.pending_approvals;await loadLowStock()}catch(e){toast(e.message)}}
async function loadLowStock(){try{const d=await api("/api/products/");const low=d.products.filter(p=>p.stock<=p.reorder_level);$("lowStockTable").innerHTML=low.length?`<table><thead><tr><th>PRODUCT</th><th>SKU</th><th>AVAILABLE</th><th>REORDER AT</th><th>STATUS</th></tr></thead><tbody>${low.map(p=>`<tr><td><b>${escapeHtml(p.name)}</b></td><td>${escapeHtml(p.sku)}</td><td>${p.stock}</td><td>${p.reorder_level}</td><td><span class="status-pill">Restock review</span></td></tr>`).join("")}</tbody></table>`:'<p class="muted">No low-stock products. Your inventory looks healthy.</p>'}catch(e){}}
async function sendChat(message){if(!message.trim())return;appendMessage("user",message);$("chatInput").value="";const wait=appendMessage("assistant","Thinking…","Supervisor Agent");try{const d=await api("/api/chat/",{method:"POST",body:JSON.stringify({message})});wait.remove();appendMessage("assistant",d.message,d.agent,d.data);if(d.data?.recommendations){const rec=d.data.recommendations.map(p=>`${p.name} · ${money(p.price)} · ★ ${p.rating}`).join("\n");appendMessage("assistant",rec,"Recommended products")}await loadMetrics()}catch(e){wait.remove();appendMessage("assistant",e.message,"System")}}
function appendMessage(type,message,agent="Supervisor Agent",data={}){const wrap=document.createElement("div");wrap.className=type==="user"?"user-message":"assistant-message";wrap.innerHTML=`<div class="message-avatar">${type==="user"?"OP":"✳"}</div><div><b>${escapeHtml(agent)}</b><p>${escapeHtml(message)}</p>${type!=="user"?`<span class="agent-response-tag">${escapeHtml(agent)}</span>`:""}</div>`;$("chatMessages").appendChild(wrap);$("chatMessages").scrollTop=$("chatMessages").scrollHeight;return wrap}
$("chatForm").addEventListener("submit",e=>{e.preventDefault();sendChat($("chatInput").value)});
document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>sendChat(b.dataset.prompt)));

async function runAgentFromCard(agentName, message) {
    const output = $("agentRunOutput");

    if (!output) {
        console.error("Agent output panel not found in dashboard.html");
        toast("Agent output panel is missing. Check dashboard.html.");
        return;
    }

    output.classList.remove("hidden");
    output.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });

    $("agentRunTitle").textContent =
        agentName.charAt(0).toUpperCase() + agentName.slice(1)
        + " Agent";

    $("agentRunStatus").textContent = "Running agent...";
    $("agentRunMessage").textContent = "";
    $("agentRunData").textContent = "";

    try {
        const result = await api(
            `/api/agents/${encodeURIComponent(agentName)}/`,
            {
                method: "POST",
                body: JSON.stringify({ message })
            }
        );

        $("agentRunStatus").textContent = "Agent completed";
        $("agentRunMessage").textContent = result.message || "No message returned.";

        if (result.data && Object.keys(result.data).length > 0) {
            $("agentRunData").textContent =
                JSON.stringify(result.data, null, 2);
        }

        await loadMetrics();

    } catch (error) {
        $("agentRunStatus").textContent = "Agent request failed";
        $("agentRunMessage").textContent =
            error.message || "Unknown error. Check the browser console.";

        console.error("Agent API error:", error);
    }
}

document.querySelectorAll(".agent-clickable[data-agent]")
    .forEach(card => {
        const execute = () => {
            runAgentFromCard(
                card.dataset.agent,
                card.dataset.agentPrompt || ""
            );
        };

        card.addEventListener("click", execute);

        card.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                execute();
            }
        });
    });

async function loadProducts(){try{const d=await api("/api/products/");products=d.products;renderProducts()}catch(e){toast(e.message)}}
function renderProducts(){const q=$("productSearch").value.toLowerCase();const list=products.filter(p=>`${p.name} ${p.category} ${p.sku}`.toLowerCase().includes(q));$("catalogCount").textContent=`${list.length} products`; $("productGrid").innerHTML=list.length?list.map(p=>`<article class="product-card"><div class="product-visual">${p.image_url?`<img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}" onerror="this.parentElement.innerHTML='✧'">`:"✧"}</div><div class="product-card-body"><span class="category-label">${escapeHtml(p.category)}</span><h3>${escapeHtml(p.name)}</h3><div class="product-card-meta"><strong>${money(p.price)}</strong><span>★ ${escapeHtml(p.rating)}</span></div><div class="stock-note">${p.stock} in stock · reorder at ${p.reorder_level}</div><div class="product-card-actions"><button class="small-btn" data-edit="${p.id}">Edit</button><button class="small-btn danger" data-archive="${p.id}">Archive</button></div></div></article>`).join(""):'<p class="muted">No products found. Add your first product.</p>';document.querySelectorAll("[data-edit]").forEach(b=>b.addEventListener("click",()=>editProduct(Number(b.dataset.edit))));document.querySelectorAll("[data-archive]").forEach(b=>b.addEventListener("click",()=>archiveProduct(Number(b.dataset.archive))))}
$("productSearch").addEventListener("input",renderProducts);
$("showProductForm").addEventListener("click",()=>{resetProductForm();$("productFormPanel").classList.remove("hidden");$("productFormPanel").scrollIntoView({behavior:"smooth",block:"start"})});
$("cancelProductForm").addEventListener("click",()=>$("productFormPanel").classList.add("hidden"));

function resetProductForm() {
    $("productForm").reset();
    $("productId").value = "";
    $("pStock").value = 0;
    $("pReorder").value = 5;
    $("pRating").value = 4.5;
    $("productFormTitle").textContent = "Add a product";

    if (imagePreviewUrl) {
        URL.revokeObjectURL(imagePreviewUrl);
        imagePreviewUrl = null;
    }

    imagePreview.removeAttribute("src");
    imagePreviewWrap.hidden = true;
}

function editProduct(id) {
    const p = products.find(x => x.id === id);
    if (!p) return;

    $("productId").value = p.id;
    $("pName").value = p.name;
    $("pSku").value = p.sku;
    $("pCategory").value = p.category;
    $("pPrice").value = p.price;
    $("pStock").value = p.stock;
    $("pReorder").value = p.reorder_level;
    $("pRating").value = p.rating;
    $("pImageUrl").value = p.image_url || "";
    $("pDescription").value = p.description || "";
    $("pImageFile").value = "";

    if (imagePreviewUrl) {
        URL.revokeObjectURL(imagePreviewUrl);
        imagePreviewUrl = null;
    }

    if (p.image_url) {
        imagePreview.src = p.image_url;
        imagePreviewWrap.hidden = false;
    } else {
        imagePreview.removeAttribute("src");
        imagePreviewWrap.hidden = true;
    }

    $("productFormTitle").textContent = "Edit product";
    $("productFormPanel").classList.remove("hidden");
    $("productFormPanel").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

$("productForm").addEventListener("submit", async e => {
    e.preventDefault();

    const id = $("productId").value;
    const file = $("pImageFile").files[0];

    if (file && file.size > 5 * 1024 * 1024) {
        alert("Image size must not exceed 5 MB.");
        return;
    }

    const formData = new FormData();

    formData.append("name", $("pName").value.trim());
    formData.append("sku", $("pSku").value.trim());
    formData.append("category", $("pCategory").value.trim());
    formData.append("price", $("pPrice").value);
    formData.append("stock", $("pStock").value);
    formData.append("reorder_level", $("pReorder").value);
    formData.append("rating", $("pRating").value);
    formData.append("image_url", $("pImageUrl").value.trim());
    formData.append("description", $("pDescription").value);

    if (file) {
        formData.append("image", file);
    }

    try {
        await api(
            id ? `/api/products/${id}/` : "/api/products/",
            {
                method: id ? "POST" : "POST",
                body: formData
            }
        );

        toast("Product saved successfully");
        $("productFormPanel").classList.add("hidden");
        resetProductForm();

        await loadProducts();
        await loadMetrics();
    } catch (err) {
        toast(err.message);
    }
});

async function archiveProduct(id){if(!confirm("Archive this product? It will be hidden from the active catalog."))return;try{await api(`/api/products/${id}/`,{method:"DELETE"});toast("Product archived");await loadProducts();await loadMetrics()}catch(e){toast(e.message)}}
async function loadOrders(){try{const d=await api("/api/orders/");$("ordersTable").innerHTML=d.orders.length?`<table><thead><tr><th>ORDER</th><th>CUSTOMER</th><th>PRODUCT</th><th>QTY</th><th>TOTAL</th><th>STATUS</th></tr></thead><tbody>${d.orders.map(o=>`<tr><td>#${o.id}</td><td>${escapeHtml(o.customer_name)}</td><td>${escapeHtml(o.product)}</td><td>${o.quantity}</td><td>${money(o.total)}</td><td><span class="status-pill status-${escapeHtml(o.status)}">${escapeHtml(o.status)}</span></td></tr>`).join("")}</tbody></table>`:'<p class="muted">No orders yet. Order requests created via the API will appear here.</p>'}catch(e){toast(e.message)}}
async function loadApprovals(){try{const d=await api("/api/approvals/");const pending=d.approvals.filter(a=>a.status==="pending");$("approvalBadge").textContent=pending.length;$("approvalsList").innerHTML=d.approvals.length?d.approvals.map(a=>`<article class="approval-card"><div class="agent-icon ${a.status==="pending"?"ana":a.status==="approved"?"sales":"cs"}">${a.status==="pending"?"⌛":a.status==="approved"?"✓":"×"}</div><div class="approval-main"><h4>${escapeHtml(a.action_type.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase()))} <span class="status-pill status-${a.status}">${escapeHtml(a.status)}</span></h4><p>${escapeHtml(a.reason||JSON.stringify(a.payload))}<br>Payload: ${escapeHtml(JSON.stringify(a.payload))}</p>${a.status==="pending"?`<div class="approval-actions"><button class="approve-btn" data-decision="approve" data-id="${a.id}">✓ Approve</button><button class="reject-btn" data-decision="reject" data-id="${a.id}">✕ Reject</button></div>`:""}</div></article>`).join(""):'<p class="muted">No approval requests. Create an order request to see the human-review workflow.</p>';document.querySelectorAll("[data-decision]").forEach(b=>b.addEventListener("click",()=>reviewApproval(Number(b.dataset.id),b.dataset.decision)))}catch(e){toast(e.message)}}
async function reviewApproval(id,decision){if(!confirm(`${decision==="approve"?"Approve":"Reject"} this business action?`))return;try{await api("/api/approvals/",{method:"POST",body:JSON.stringify({id,decision})});toast(`Request ${decision==="approve"?"approved":"rejected"}`);await loadApprovals();await loadMetrics();await loadOrders();await loadProducts()}catch(e){toast(e.message)}}
loadMetrics();loadProducts();
