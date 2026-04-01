"use client";

import { useState } from "react";
import { useChatStore } from "@/lib/chat-store";
import ReactMarkdown from "react-markdown";

export function MarkdownEditor({ data }: { data: Record<string, any> }) {
  const [content, setContent] = useState(data.soul_md ?? data.content ?? "");
  const [preview, setPreview] = useState(false);
  const sendUIAction = useChatStore((s) => s.sendUIAction);
  const entity = data.agent_id ? "role" : "scope";

  return (
    <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--border-primary)', background: 'var(--bg-elevated)' }}>
      {data.agent_name && data.name && (
        <div className="px-4 py-2 border-b text-xs font-medium" style={{ borderColor: 'var(--border-secondary)', color: 'var(--color-accent)', fontFamily: 'var(--font-mono)' }}>
          {data.agent_name} / {data.name}
        </div>
      )}
      <div className="flex border-b" style={{ borderColor: 'var(--border-secondary)' }}>
        {["Edit", "Preview"].map(tab => (
          <button key={tab} onClick={() => setPreview(tab === "Preview")}
            className="px-4 py-2 text-xs font-medium transition-colors"
            style={{ color: (preview ? "Preview" : "Edit") === tab ? 'var(--text-primary)' : 'var(--text-tertiary)', borderBottom: (preview ? "Preview" : "Edit") === tab ? '2px solid var(--color-accent)' : '2px solid transparent' }}>
            {tab}
          </button>
        ))}
      </div>
      <div className="p-4">
        {preview ? (
          <div className="prose prose-sm max-w-none min-h-[100px]" style={{ color: 'var(--text-secondary)' }}><ReactMarkdown>{content}</ReactMarkdown></div>
        ) : (
          <textarea value={content} onChange={(e) => setContent(e.target.value)}
            className="w-full min-h-[100px] text-sm border-0 resize-y focus:ring-0 p-0"
            style={{ background: 'transparent', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', outline: 'none', boxShadow: 'none' }} />
        )}
      </div>
      <div className="flex gap-2 px-4 py-3 border-t" style={{ borderColor: 'var(--border-secondary)' }}>
        <button onClick={() => sendUIAction({ entity, action: "update", targets: [{ id: data.id, name: data.name ?? "scope", entity }], context: { soul_md: content } })}
          className="text-xs font-medium px-3 py-1.5 rounded-lg text-white" style={{ background: 'var(--color-accent)' }}>Save</button>
        <button onClick={() => sendUIAction({ entity: "_dialog", action: "cancel", targets: [] })}
          className="text-xs font-medium px-3 py-1.5 rounded-lg border" style={{ borderColor: 'var(--border-primary)', color: 'var(--text-secondary)' }}>Cancel</button>
      </div>
    </div>
  );
}
