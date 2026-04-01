"use client";
import { useState } from "react";
import { useChatStore } from "@/lib/chat-store";

export function YamlEditor({ data }: { data: Record<string, any> }) {
  const [content, setContent] = useState(data.commitment_yaml ?? data.content ?? "");
  const sendUIAction = useChatStore((s) => s.sendUIAction);
  return (
    <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--border-primary)', background: 'var(--bg-elevated)' }}>
      {data.agent_name && <div className="px-4 py-2 border-b text-xs font-medium" style={{ borderColor: 'var(--border-secondary)', color: 'var(--color-accent)', fontFamily: 'var(--font-mono)' }}>{data.agent_name}/commitment</div>}
      <textarea value={content} onChange={(e) => setContent(e.target.value)}
        className="w-full min-h-[120px] p-4 text-sm border-0 resize-y"
        style={{ background: 'transparent', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', outline: 'none', boxShadow: 'none' }} />
      <div className="flex gap-2 px-4 py-3 border-t" style={{ borderColor: 'var(--border-secondary)' }}>
        <button onClick={() => sendUIAction({ entity: "commitment", action: "update", targets: [{ id: data.id ?? "commitment", name: "commitment", entity: "commitment" }], context: { commitment_yaml: content } })}
          className="text-xs font-medium px-3 py-1.5 rounded-lg text-white" style={{ background: 'var(--color-accent)' }}>Save</button>
        <button onClick={() => sendUIAction({ entity: "_dialog", action: "cancel", targets: [] })}
          className="text-xs font-medium px-3 py-1.5 rounded-lg border" style={{ borderColor: 'var(--border-primary)', color: 'var(--text-secondary)' }}>Cancel</button>
      </div>
    </div>
  );
}
