export interface User {
  id: string;
  github_login: string;
  github_name: string;
  github_avatar: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  rawContent?: string;
  structured?: StructuredData;
  timestamp: number;
  source: "chat" | "ui_action";
}

export interface StructuredData {
  type: "agent" | "role" | "skill" | "scope" | "commitment" | "deploy";
  action: "created" | "updated" | "deleted" | "listed" | "exported" | "confirm_required" | "editing" | "detailed";
  data: Record<string, any>;
}

export interface AgentData {
  id: string;
  name: string;
  description: string;
  roles?: Array<{ id: string; name: string }>;
  skills?: Array<{ id: string; name: string }>;
  roles_count?: number;
  skills_count?: number;
}

export interface EntityStore {
  agents: Record<string, AgentData>;
  roles: Record<string, any>;
  skills: Record<string, any>;
}
