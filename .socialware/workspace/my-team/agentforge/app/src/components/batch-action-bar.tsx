"use client";

import { useChatStore } from "@/lib/chat-store";

export function BatchActionBar() {
  const selected = useChatStore((s) => s.selected);
  const sendUIAction = useChatStore((s) => s.sendUIAction);
  const clearSelection = useChatStore((s) => s.clearSelection);
  if (selected.length === 0) return null;
  const entity = selected[0]?.entity ?? "agent";

  return (
    <div className="rounded-xl p-3 border flex items-center gap-2 text-xs anim-slide" style={{ background: 'var(--color-accent-subtle)', borderColor: 'var(--color-accent-border)' }}>
      <span className="font-semibold" style={{ color: 'var(--color-accent)', fontFamily: 'var(--font-mono)' }}>{selected.length} selected</span>
      <button onClick={() => sendUIAction({ entity, action: "export", targets: selected })} className="font-medium px-2.5 py-1 rounded-md text-white" style={{ background: 'var(--color-accent)' }}>Export</button>
      <button onClick={() => sendUIAction({ entity, action: "delete", targets: selected })} className="font-medium px-2.5 py-1 rounded-md" style={{ color: 'var(--color-danger)', background: 'var(--color-danger-subtle)' }}>Delete</button>
      <button onClick={clearSelection} className="font-medium px-2.5 py-1 rounded-md" style={{ color: 'var(--text-tertiary)' }}>Clear</button>
    </div>
  );
}
