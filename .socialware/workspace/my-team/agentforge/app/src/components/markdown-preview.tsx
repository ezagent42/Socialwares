"use client";
import ReactMarkdown from "react-markdown";

export function MarkdownPreview({ data }: { data: Record<string, any> }) {
  return (
    <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-primary)', background: 'var(--bg-elevated)' }}>
      {data.agent_name && data.name && <div className="text-xs mb-2" style={{ color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>{data.agent_name}/{data.name}</div>}
      <div className="prose prose-sm max-w-none" style={{ color: 'var(--text-secondary)' }}><ReactMarkdown>{data.soul_md ?? data.content ?? ""}</ReactMarkdown></div>
    </div>
  );
}
