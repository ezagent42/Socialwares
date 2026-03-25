const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  // Agent may use tools (read files, run commands) which can take minutes
  const timeout = path === "/chat" ? 600000 : 30000;
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `HTTP ${res.status}`);
    }
    return res.json();
  } finally {
    clearTimeout(timer);
  }
}

export async function getSession() {
  return request<{ active: boolean; role?: string; adapter?: string }>("/session");
}

export async function createSession(role: string, adapter: string, workspace?: string) {
  return request<{ status: string; role: string; adapter: string; workspace?: string }>("/session", {
    method: "POST",
    body: JSON.stringify({ role, adapter, workspace: workspace || null }),
  });
}

export async function deleteSession() {
  return request<{ status: string }>("/session", { method: "DELETE" });
}

export async function sendMessage(message: string) {
  return request<{ messages: { type: string; text: string }[] }>("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function getAdapters() {
  return request<{ adapters: { name: string; available: boolean }[] }>("/adapters");
}

export async function getRoles() {
  return request<{ roles: string[] }>("/roles");
}

export async function getWorkspaces() {
  return request<{ workspaces: { room: string; app: string; path: string; has_runtime: boolean }[] }>("/workspaces");
}
