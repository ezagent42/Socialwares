"use client";

import { useState, useRef, useEffect } from "react";
import type { Room, TaskStatus } from "@/types";
import { agentsApi, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { TaskStatusBadge } from "./task-status";
import { Send, Bot, User } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  room: Room;
  token: string;
}

export function AgentChat({ room, token }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | undefined>();
  const [taskStatus, setTaskStatus] = useState<TaskStatus>("open");
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const prompt = input.trim();
    if (!prompt || loading) return;

    setInput("");
    setError("");
    setMessages((prev) => [...prev, { role: "user", content: prompt }]);
    setLoading(true);

    try {
      const response = await agentsApi.invoke(token, {
        room_id: room.id,
        prompt,
        task_id: taskId,
        history: messages.map((m) => ({ role: m.role, content: m.content })),
      });

      setMessages((prev) => [...prev, { role: "assistant", content: response.content }]);
      setTaskId(response.task_id);
      setTaskStatus(response.task_status as TaskStatus);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to get response");
      setMessages((prev) => prev.slice(0, -1)); // remove optimistic user message
      setInput(prompt);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Task status bar */}
      {taskId && (
        <div className="px-4 py-2 border-b flex items-center gap-2 text-xs text-muted-foreground">
          <span>Task:</span>
          <TaskStatusBadge status={taskStatus} />
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
            <Bot className="h-8 w-8 mb-2 opacity-40" />
            <p className="text-sm">Start a conversation with the agent</p>
            <p className="text-xs mt-1">Scope: {room.name}</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className="shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center">
              {msg.role === "user" ? (
                <User className="h-4 w-4" />
              ) : (
                <Bot className="h-4 w-4" />
              )}
            </div>
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center">
              <Bot className="h-4 w-4" />
            </div>
            <div className="bg-muted rounded-lg px-3 py-2 text-sm text-muted-foreground">
              Thinking...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t p-4">
        {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a message... (Enter to send, Shift+Enter for newline)"
            rows={1}
            className="flex-1 px-3 py-2 border border-input rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <Button size="icon" onClick={handleSend} disabled={loading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
