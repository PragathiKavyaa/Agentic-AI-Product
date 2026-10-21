document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("customer-chat-form");
  if (!form) return;
  const log = document.getElementById("chat-log");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = form.elements.message;
    const message = input.value.trim();
    if (!message) return;
    const userLine = document.createElement("p");
    userLine.className = "user";
    userLine.textContent = message;
    log.appendChild(userLine);
    input.value = "";
    const data = new FormData(form);
    data.set("message", message);
    const pending = document.createElement("p");
    pending.className = "bot";
    pending.textContent = "Checking with the AI assistant…";
    log.appendChild(pending);
    try {
      const response = await fetch(form.dataset.url, {
        method: "POST",
        body: data,
        headers: {"X-Requested-With": "XMLHttpRequest"}
      });
      const result = await response.json();
      pending.textContent = response.ok ? `${result.agent || "AI assistant"}: ${result.message}` : (result.error || "Sorry, I couldn't process that question.");
    } catch {
      pending.textContent = "Unable to reach the assistant. Please try again.";
    }
    log.scrollTop = log.scrollHeight;
  });
});
