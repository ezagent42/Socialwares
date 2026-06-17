"use client";

import { useChatStore } from "@/lib/chat-store";

interface Props {
  entity: string; action: string; data: Record<string, any>; label: string; variant?: "default" | "danger";
}

export function ActionButton({ entity, action, data, label, variant }: Props) {
  const sendUIAction = useChatStore((s) => s.sendUIAction);
  const loading = useChatStore((s) => s.session.loading);

  return (
    <button
      onClick={() => sendUIAction({ entity, action, targets: [{ id: data.id, name: data.name, entity }] })}
      disabled={loading}
      className="text-[11px] font-medium px-2 py-1 rounded-md transition-colors disabled:opacity-30"
      style={{
        color: variant === "danger" ? 'var(--color-danger)' : 'var(--text-tertiary)',
        background: 'transparent',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = variant === "danger" ? 'var(--color-danger-subtle)' : 'var(--bg-tertiary)';
      }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      {label}
    </button>
  );
}
