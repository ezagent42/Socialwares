import { create } from "zustand";
import type { User, Message, StructuredData, EntityStore } from "./types";
import type { UIAction, TargetItem } from "./ui-action";
import { serializeUIAction, formatUIActionDisplay } from "./ui-action";
import { updateEntities } from "./entity-updater";

interface ChatStore {
  user: User | null;
  messages: Message[];
  entities: EntityStore;
  selected: TargetItem[];
  session: { connected: boolean; loading: boolean };

  setUser: (user: User | null) => void;
  sendMessage: (content: string, source: "chat" | "ui_action", displayText?: string) => Promise<void>;
  sendUIAction: (action: UIAction) => Promise<void>;
  toggleSelect: (item: TargetItem) => void;
  clearSelection: () => void;
  checkAuth: () => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  user: null,
  messages: [],
  entities: { agents: {}, roles: {}, skills: {} },
  selected: [],
  session: { connected: false, loading: false },

  setUser: (user) => set({ user }),

  checkAuth: async () => {
    try {
      const res = await fetch("/api/auth/me");
      if (res.ok) {
        const user = await res.json();
        set({ user });
      } else {
        set({ user: null });
      }
    } catch {
      set({ user: null });
    }
  },

  toggleSelect: (item) => {
    const { selected } = get();
    const exists = selected.some((s) => s.id === item.id);
    set({
      selected: exists
        ? selected.filter((s) => s.id !== item.id)
        : [...selected, item],
    });
  },

  clearSelection: () => set({ selected: [] }),

  sendUIAction: async (action: UIAction) => {
    const serialized = serializeUIAction(action);
    const displayText = formatUIActionDisplay(action);
    await get().sendMessage(serialized, "ui_action", displayText);
    get().clearSelection();
  },

  sendMessage: async (content: string, source: "chat" | "ui_action", displayText?: string) => {
    const { messages } = get();

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: displayText ?? content,
      rawContent: content,
      timestamp: Date.now(),
      source,
    };
    set({
      messages: [...messages, userMsg],
      session: { connected: true, loading: true },
    });

    try {
      const response = await fetch("/api/chat/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content }),
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`Chat send failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let assistantContent = "";
      let assistantStructured: StructuredData | undefined;
      const assistantId = crypto.randomUUID();

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            continue;
          }
          if (line.startsWith("data:")) {
            const dataStr = line.slice(5).trim();
            if (!dataStr) continue;
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.content) {
                assistantContent += parsed.content;
              }
              if (parsed.type && parsed.action) {
                assistantStructured = parsed;
                const entities = updateEntities(get().entities, parsed);
                set({ entities });
              }
            } catch {
              // skip malformed data
            }
          }
        }

        // Update assistant message progressively
        const currentMessages = get().messages.filter((m) => m.id !== assistantId);
        const assistantMsg: Message = {
          id: assistantId,
          role: "assistant",
          content: assistantContent,
          structured: assistantStructured,
          timestamp: Date.now(),
          source: "chat",
        };
        set({ messages: [...currentMessages, assistantMsg] });
      }
    } catch (error) {
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
        timestamp: Date.now(),
        source: "chat",
      };
      set({ messages: [...get().messages, errorMsg] });
    } finally {
      set({ session: { connected: true, loading: false } });
    }
  },
}));
