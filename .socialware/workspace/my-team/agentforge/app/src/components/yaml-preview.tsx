"use client";
export function YamlPreview({ data }: { data: Record<string, any> }) {
  return (
    <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-primary)', background: 'var(--bg-elevated)' }}>
      {data.agent_name && <div className="text-xs mb-2" style={{ color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>{data.agent_name}/commitment</div>}
      <pre className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{data.commitment_yaml ?? data.content ?? ""}</pre>
    </div>
  );
}
