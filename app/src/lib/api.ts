import type { AgentInvokeResponse, AgentTask, Room } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...rest } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(rest.headers ?? {}),
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, error.detail ?? "API error");
  }

  return res.json();
}

// Rooms
export const roomsApi = {
  list: (token: string) =>
    apiFetch<Room[]>("/rooms/", { token }),

  create: (token: string, data: { name: string; display_name: string }) =>
    apiFetch<Room>("/rooms/", { method: "POST", body: JSON.stringify(data), token }),

  get: (token: string, roomId: string) =>
    apiFetch<Room>(`/rooms/${roomId}`, { token }),

  delete: (token: string, roomId: string) =>
    apiFetch<void>(`/rooms/${roomId}`, { method: "DELETE", token }),
};

// Agents
export const agentsApi = {
  invoke: (
    token: string,
    data: { room_id: string; prompt: string; task_id?: string; history?: { role: string; content: string }[] }
  ) =>
    apiFetch<AgentInvokeResponse>("/agents/invoke", {
      method: "POST",
      body: JSON.stringify(data),
      token,
    }),

  listTasks: (token: string, roomId: string) =>
    apiFetch<AgentTask[]>(`/agents/tasks?room_id=${roomId}`, { token }),

  getTask: (token: string, taskId: string) =>
    apiFetch<AgentTask>(`/agents/tasks/${taskId}`, { token }),
};
