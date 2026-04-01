"use client";

import { ActionButton } from "../action-button";

export function RoleCard({ data }: { data: Record<string, any> }) {
  return (
    <div className="rounded-lg p-3 border transition-all" style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-primary)', boxShadow: 'var(--shadow-sm)' }}>
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: 'var(--color-accent)' }} />
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{data.name}</span>
          </div>
          {data.soul_md_preview && <p className="text-xs mt-1 ml-3.5 line-clamp-2" style={{ color: 'var(--text-tertiary)' }}>{data.soul_md_preview}</p>}
        </div>
        <div className="flex gap-0.5 shrink-0">
          <ActionButton entity="role" action="edit" data={data} label="Edit" />
          <ActionButton entity="role" action="delete" data={data} label="Del" variant="danger" />
        </div>
      </div>
    </div>
  );
}
