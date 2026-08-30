const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function request(path, token, options = {}) {
  if (!token) {
    throw new Error("Your login session is not ready. Please refresh the page and sign in again.");
  }

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  const text = await response.text();
  let data;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }

  if (!response.ok) {
    throw new Error(data?.detail || data?.message || `Request failed (${response.status})`);
  }
  return data;
}

export const api = {
  url: API_URL,
  reports: (token) => request("/api/reports", token),
  report: (name, token) => request(`/api/reports/${encodeURIComponent(name)}`, token),
  stock: (symbol, token) => request(`/api/stocks/${encodeURIComponent(symbol)}`, token),
  subscription: (token) => request("/api/subscription", token),
};
