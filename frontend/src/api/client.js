const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload.detail || "Request failed";
    throw new Error(message);
  }

  return payload;
}

export const api = {
  login: (data) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  register: (data) => request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),
  analyze: (data) => request("/transactions/analyze", { method: "POST", body: JSON.stringify(data) }),
  createPaymentIntent: (data, idempotencyKey) =>
    request("/payments/intents", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(data),
    }),
  confirmPaymentIntent: (intentId) => request(`/payments/intents/${intentId}/sandbox-confirm`, { method: "POST" }),
  requestOtp: (intentId) => request(`/payments/intents/${intentId}/request-otp`, { method: "POST" }),
  verifyOtp: (intentId, otp) =>
    request(`/payments/intents/${intentId}/verify-otp`, {
      method: "POST",
      body: JSON.stringify({ otp }),
    }),
  paymentIntents: () => request("/payments/intents"),
  clearTransactions: () => request("/transactions", { method: "DELETE" }),
  transactions: (params = {}) => {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") search.set(key, value);
    });
    const suffix = search.toString() ? `?${search.toString()}` : "";
    return request(`/transactions${suffix}`);
  },
  summary: () => request("/analytics/summary"),
  riskBreakdown: () => request("/analytics/risk-breakdown"),
  modelMetrics: () => request("/analytics/model-metrics"),
  listBlocklist: () => request("/rules/blocklist"),
  addBlocklist: (data) => request("/rules/blocklist", { method: "POST", body: JSON.stringify(data) }),
  deleteBlocklist: (id) => request(`/rules/blocklist/${id}`, { method: "DELETE" }),
  submitFeedback: (txId, data) => request(`/transactions/${txId}/feedback`, { method: "POST", body: JSON.stringify(data) }),
  retrainModel: () => request("/analytics/retrain", { method: "POST" }),
};


export async function downloadCsv() {
  const response = await fetch(`${API_URL}/transactions/export.csv`, { credentials: "include" });
  if (!response.ok) throw new Error("Could not export report");

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "fraudshield-report.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function downloadPdf() {
  const response = await fetch(`${API_URL}/transactions/export.pdf`, { credentials: "include" });
  if (!response.ok) throw new Error("Could not export PDF report");

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "fraudshield-executive-report.pdf";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
