"use client";

import { useState, useRef, useEffect } from "react";
import MessageBubble from "./message-bubble";
import SessionBar from "./session-bar";
import { createSession, deleteSession, sendMessage, getAdapters } from "@/lib/api";

type Message = {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
};

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [sessionRole, setSessionRole] = useState<string>();
  const [sessionAdapter, setSessionAdapter] = useState<string>();
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (role: Message["role"], content: string) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString() + Math.random(), role, content },
    ]);
  };

  const handleConnect = async (cmd: string) => {
    const role = cmd;
    addMessage("system", `Connecting to ${role}...`);
    try {
      const { adapters } = await getAdapters();
      const available = adapters.filter((a) => a.available);
      if (available.length === 0) {
        addMessage("system", "No runtime found. Install Claude Code, Codex, or Kimi Code.");
        return;
      }
      const adapterName = available[0].name;
      addMessage("system", `Runtime detected: ${adapterName}`);
      await createSession(role, adapterName);
      setConnected(true);
      setSessionRole(role);
      setSessionAdapter(adapterName);
      addMessage("system", `Connected to ${role} via ${adapterName}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addMessage("system", `Connection failed: ${msg}`);
    }
  };

  const handleDisconnect = async () => {
    try { await deleteSession(); } catch {}
    setConnected(false);
    setSessionRole(undefined);
    setSessionAdapter(undefined);
    addMessage("system", "Session closed.");
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");

    if (text.startsWith("/")) {
      const cmd = text.slice(1).split(" ")[0];
      if (cmd === "disconnect") {
        await handleDisconnect();
        return;
      }
      addMessage("user", text);
      await handleConnect(cmd);
      return;
    }

    addMessage("user", text);

    if (!connected) {
      addMessage("system", "No agent connected. Type /agentforge to start.");
      return;
    }

    setLoading(true);
    try {
      const { messages: replies } = await sendMessage(text);
      for (const msg of replies) {
        if (msg.type === "text" && msg.text) {
          addMessage("agent", msg.text);
        }
      }
      if (replies.length === 0) {
        addMessage("system", "Agent returned no response.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addMessage("system", `Error: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  // Slash command suggestions
  const COMMANDS = [
    { cmd: "/agentforge", desc: "Connect to AgentForge agent" },
    { cmd: "/default", desc: "Connect to default agent" },
    { cmd: "/dev", desc: "Connect to dev agent" },
    { cmd: "/disconnect", desc: "Disconnect current session" },
  ];

  const showSuggestions = input.startsWith("/") && !connected
    ? COMMANDS.filter((c) => c.cmd.startsWith(input.toLowerCase()))
    : input === "/disconnect" && connected
    ? [COMMANDS[3]]
    : input === "/"
    ? (connected ? [COMMANDS[3]] : COMMANDS.filter((c) => c.cmd !== "/disconnect"))
    : [];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === "Tab" && showSuggestions.length > 0) {
      e.preventDefault();
      setInput(showSuggestions[0].cmd);
    }
  };

  return (
    <div className="flex flex-col h-screen" style={{ background: "var(--bg-primary)" }}>
      <SessionBar
        connected={connected}
        role={sessionRole}
        adapter={sessionAdapter}
        onDisconnect={handleDisconnect}
      />

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full pt-32">
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold mb-6"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                S
              </div>
              <h1
                className="text-2xl font-semibold mb-2 tracking-tight"
                style={{ color: "var(--text-primary)" }}
              >
                Socialware Chat
              </h1>
              <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
                Agent interaction, visualized.
              </p>
              <div
                className="px-4 py-2 rounded-lg text-sm font-mono"
                style={{
                  background: "var(--bg-tertiary)",
                  border: "1px solid var(--border)",
                  color: "var(--text-secondary)",
                }}
              >
                Type{" "}
                <span style={{ color: "var(--accent)" }}>/agentforge</span>
                {" "}to connect an Agent
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
          ))}

          {loading && (
            <div className="flex items-center gap-3 mb-3 animate-fade-in-up">
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-semibold shrink-0"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                A
              </div>
              <span className="thinking-shimmer text-sm font-medium">
                Thinking...
              </span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input area */}
      <div style={{ background: "var(--bg-secondary)", borderTop: "1px solid var(--border-subtle)" }}>
        <div className="max-w-3xl mx-auto px-4 py-4">
          {/* Slash command suggestions */}
          {showSuggestions.length > 0 && (
            <div
              className="mb-2 rounded-lg overflow-hidden"
              style={{ background: "var(--bg-tertiary)", border: "1px solid var(--border)" }}
            >
              {showSuggestions.map((s) => (
                <button
                  key={s.cmd}
                  onClick={() => { setInput(s.cmd); }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors duration-100 cursor-pointer"
                  style={{ background: "transparent" }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-elevated)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                >
                  <span className="text-sm font-mono font-medium" style={{ color: "var(--accent)" }}>
                    {s.cmd}
                  </span>
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {s.desc}
                  </span>
                </button>
              ))}
            </div>
          )}

          <div
            className="flex items-center gap-2 rounded-xl px-4 py-1 transition-all duration-200"
            style={{
              background: "var(--bg-tertiary)",
              border: "1px solid var(--border)",
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={connected ? "Send a message..." : "Type /agentforge to connect"}
              disabled={loading}
              className="flex-1 bg-transparent py-3 text-sm outline-none placeholder-opacity-40"
              style={{
                color: "var(--text-primary)",
                fontFamily: "'Outfit', sans-serif",
              }}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="p-2 rounded-lg transition-all duration-200 disabled:opacity-20 cursor-pointer"
              style={{
                background: input.trim() ? "var(--accent)" : "transparent",
                color: input.trim() ? "#fff" : "var(--text-muted)",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
