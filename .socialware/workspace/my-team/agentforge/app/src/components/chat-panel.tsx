"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useChatStore } from "@/lib/chat-store";
import { MessageBubble } from "./message-bubble";

const COMMANDS = [
  { slash: "/create-agent", desc: "Create a new Agent" },
  { slash: "/list-agents", desc: "View all your Agents" },
  { slash: "/add-skill", desc: "Add a skill to an Agent" },
  { slash: "/find-skill", desc: "Search existing skills" },
  { slash: "/export-agent", desc: "Export Agent (multi-format)" },
  { slash: "/import-agent", desc: "Import Agent config" },
  { slash: "/delete-agent", desc: "Delete an Agent" },
];

export function ChatPanel() {
  const [input, setInput] = useState("");
  const [showCmd, setShowCmd] = useState(false);
  const messages = useChatStore((s) => s.messages);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const loading = useChatStore((s) => s.session.loading);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const filtered = useMemo(() => {
    if (!input.trim()) return COMMANDS;
    const q = input.toLowerCase();
    return COMMANDS.filter(c =>
      c.slash.toLowerCase().includes(q) || c.desc.toLowerCase().includes(q)
    );
  }, [input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setShowCmd(false);
    await sendMessage(msg, "chat");
  };

  return (
    <div className="flex flex-col h-full w-full" style={{ background: 'var(--bg-primary)' }}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full bg-grid">
            <div className="text-center anim-fade">
              <p className="text-lg font-medium mb-1" style={{ color: 'var(--text-primary)' }}>AgentForge Terminal</p>
              <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Type a command to get started</p>
            </div>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">
            {messages.map((msg, i) => (
              <div key={msg.id} className="anim-slide" style={{ animationDelay: `${Math.min(i * 30, 200)}ms` }}>
                <MessageBubble message={msg} />
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 py-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: 'var(--color-accent)', animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: 'var(--color-accent)', animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: 'var(--color-accent)', animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Command palette */}
      {showCmd && filtered.length > 0 && (
        <div className="max-w-2xl mx-auto w-full px-4">
          <div className="rounded-xl border overflow-hidden mb-1" style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-primary)', boxShadow: 'var(--shadow-lg)' }}>
            {filtered.slice(0, 6).map((cmd, i) => (
              <button
                key={i}
                onMouseDown={async (e) => {
                  e.preventDefault();
                  setInput("");
                  setShowCmd(false);
                  await sendMessage(cmd.slash, "chat");
                }}
                className="w-full text-left px-4 py-2.5 flex items-center gap-3 transition-colors"
                style={{ borderBottom: i < filtered.length - 1 ? '1px solid var(--border-secondary)' : 'none' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-tertiary)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <span className="text-sm font-medium" style={{ color: 'var(--color-accent)', fontFamily: 'var(--font-mono)' }}>{cmd.slash}</span>
                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{cmd.desc}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="border-t px-4 py-3" style={{ borderColor: 'var(--border-primary)', background: 'var(--bg-secondary)' }}>
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
          <div className="flex gap-2 items-center">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => { setInput(e.target.value); setShowCmd(true); }}
                onFocus={() => setShowCmd(true)}
                onBlur={() => setTimeout(() => setShowCmd(false), 150)}
                placeholder="Send a message..."
                disabled={loading}
                className="w-full px-4 py-2.5 rounded-xl text-sm border transition-colors disabled:opacity-40"
                style={{
                  background: 'var(--bg-primary)',
                  borderColor: 'var(--border-primary)',
                  color: 'var(--text-primary)',
                }}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 rounded-xl text-sm font-medium transition-all disabled:opacity-30"
              style={{ background: 'var(--color-accent)', color: '#fff' }}
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
