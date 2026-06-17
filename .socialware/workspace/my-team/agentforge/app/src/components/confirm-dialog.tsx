"use client";

import { useChatStore } from "@/lib/chat-store";

export function ConfirmDialog({ data }: { data: Record<string, any> }) {
  const sendUIAction = useChatStore((s) => s.sendUIAction);
  return (
    <div className="rounded-xl p-4 border" style={{ background: 'var(--color-warning-subtle)', borderColor: 'rgba(245,158,11,0.3)' }}>
      <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{data.message}</p>
      <div className="flex gap-2 mt-3">
        <button onClick={() => sendUIAction({ entity: "_dialog", action: "confirm", targets: [] })} className="text-xs font-medium px-3 py-1.5 rounded-lg text-white transition-colors" style={{ background: 'var(--color-danger)' }}>
          {data.confirm_label ?? "Confirm"}
        </button>
        <button onClick={() => sendUIAction({ entity: "_dialog", action: "cancel", targets: [] })} className="text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors" style={{ borderColor: 'var(--border-primary)', color: 'var(--text-secondary)' }}>
          {data.cancel_label ?? "Cancel"}
        </button>
      </div>
    </div>
  );
}
