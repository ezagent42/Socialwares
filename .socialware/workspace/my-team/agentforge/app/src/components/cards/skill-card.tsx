"use client";

import { ActionButton } from "../action-button";

export function SkillCard({ data }: { data: Record<string, any> }) {
  return (
    <div className="rounded-lg p-3 border transition-all" style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-primary)', boxShadow: 'var(--shadow-sm)' }}>
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <span className="text-sm font-medium" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{data.name}</span>
          {data.description && <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{data.description}</p>}
          {data.roles && Array.isArray(data.roles) && data.roles.length > 0 && (
            <div className="flex gap-1 mt-1.5">
              {data.roles.map((role: string, i: number) => (
                <span key={i} className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: 'var(--color-accent-subtle)', color: 'var(--color-accent)', fontFamily: 'var(--font-mono)' }}>
                  {typeof role === "string" ? role : String(role)}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex gap-0.5 shrink-0">
          <ActionButton entity="skill" action="edit" data={data} label="Edit" />
          <ActionButton entity="skill" action="delete" data={data} label="Del" variant="danger" />
        </div>
      </div>
    </div>
  );
}
