const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

function getToken() {
  return localStorage.getItem("fraudshield_token");
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
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
  me: () => request("/auth/me"),
  analyze: (data) => request("/transactions/analyze", { method: "POST", body: JSON.stringify(data) }),
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
};

export async function downloadCsv() {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}/transactions/export.csv`, { headers });
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
