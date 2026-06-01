export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function getToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("access_token");
}

export function setSession(payload) {
  window.localStorage.setItem("access_token", payload.access_token);
  window.localStorage.setItem("token_type", payload.token_type || "bearer");
  window.localStorage.setItem("user", JSON.stringify(payload.user || {}));
}

export function clearSession() {
  window.localStorage.removeItem("access_token");
  window.localStorage.removeItem("token_type");
  window.localStorage.removeItem("user");
}

export function currentUser() {
  if (typeof window === "undefined") return null;
  try {
    return JSON.parse(window.localStorage.getItem("user") || "null");
  } catch {
    return null;
  }
}

export async function apiFetch(path, options = {}) {
  const headers = {"Content-Type": "application/json", ...(options.headers || {})};
  const token = options.token === undefined ? getToken() : options.token;
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {...options, headers});
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof body === "object" ? body.detail || JSON.stringify(body) : body;
    const error = new Error(message || `Request failed with ${response.status}`);
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}
