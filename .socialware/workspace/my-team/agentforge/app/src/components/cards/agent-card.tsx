"use client";

import { useChatStore } from "@/lib/chat-store";
import { ActionButton } from "../action-button";

export function AgentCard({ data }: { data: Record<string, any> }) {
  const toggleSelect = useChatStore((s) => s.toggleSelect);
  const isSelected = useChatStore((s) => s.selected.some((s) => s.id === data.id));

  const isExample = data.is_example;

  return (
    <div
      className="rounded-xl p-3.5 border transition-all cursor-default relative overflow-hidden"
      style={{
        background: 'var(--bg-elevated)',
        borderColor: isExample ? 'var(--color-accent-border)' : isSelected ? 'var(--color-accent)' : 'var(--border-primary)',
        boxShadow: isSelected ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
      }}
    >
      {/* Example ribbon */}
      {isExample && (
        <div
          className="absolute top-0 right-0 text-[8px] font-bold uppercase tracking-widest px-6 py-0.5"
          style={{
            background: 'var(--color-accent)',
            color: '#fff',
            transform: 'rotate(45deg) translate(18px, -6px)',
            transformOrigin: 'top right',
            fontFamily: 'var(--font-mono)',
          }}
        >
          EXAMPLE
        </div>
      )}
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => toggleSelect({ id: data.id, name: data.name, entity: "agent" })}
          className="mt-0.5 accent-emerald-500"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{data.name}</h3>
            {data.model && (
              <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full uppercase tracking-wider" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                {data.model}
              </span>
            )}
          </div>
          {data.description && <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-tertiary)' }}>{data.description}</p>}
          <div className="flex gap-2 mt-2">
            {(data.roles_count ?? data.roles?.length) != null && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded" style={{ background: 'var(--color-accent-subtle)', color: 'var(--color-accent)', fontFamily: 'var(--font-mono)' }}>
                {data.roles_count ?? data.roles?.length} roles
              </span>
            )}
            {(data.skills_count ?? data.skills?.length) != null && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                {data.skills_count ?? data.skills?.length} skills
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-0.5 shrink-0">
          <ActionButton entity="agent" action="detail" data={data} label="View" />
          <ActionButton entity="agent" action="export" data={data} label="Export" />
          {!isExample && <ActionButton entity="agent" action="delete" data={data} label="Delete" variant="danger" />}
        </div>
      </div>
    </div>
  );
}
