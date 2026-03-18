// Shared TypeScript types — mirrors API schemas

export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export interface Room {
  id: string;
  name: string;
  display_name: string;
  owner_id: string;
  workspace_path: string;
  created_at: string;
}

export type TaskStatus = "open" | "in_progress" | "submitted" | "completed" | "cancelled";

export interface AgentTask {
  id: string;
  room_id: string;
  created_by: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  assigned_agent: string | null;
  result: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentInvokeResponse {
  content: string;
  task_id: string;
  task_status: TaskStatus;
  agent_id: string;
}

// Auth.js session augmentation
declare module "next-auth" {
  interface Session {
    accessToken: string;
  }
  interface User {
    accessToken: string;
  }
}
