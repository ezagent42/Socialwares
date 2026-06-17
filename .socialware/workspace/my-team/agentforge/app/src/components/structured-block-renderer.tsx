"use client";

import type { StructuredData } from "@/lib/types";
import { AgentCard } from "./cards/agent-card";
import { RoleCard } from "./cards/role-card";
import { SkillCard } from "./cards/skill-card";
import { ConfirmDialog } from "./confirm-dialog";
import { MarkdownPreview } from "./markdown-preview";
import { MarkdownEditor } from "./markdown-editor";
import { YamlPreview } from "./yaml-preview";
import { YamlEditor } from "./yaml-editor";
import { AgentDetail } from "./agent-detail";

function DeleteResult({ data }: { data: Record<string, any> }) {
  return (
    <div className="text-sm text-green-600 bg-green-50 rounded p-2">
      已删除: {data.name ?? data.id}
    </div>
  );
}

function DeployLog({ data }: { data: Record<string, any> }) {
  const downloads: Array<{ name: string; download_url: string; format?: string }> = data.downloads ?? [];
  if (downloads.length === 0 && data.download_url) {
    downloads.push({ name: data.agent_name ?? "agent", download_url: data.download_url, format: data.format });
  }
  const fmt = data.format ?? downloads[0]?.format ?? "";

  return (
    <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-primary)', background: 'var(--bg-elevated)' }}>
      <p className="text-sm font-medium mb-3" style={{ color: 'var(--text-primary)' }}>
        {downloads.length === 1 ? `Export ready: ${downloads[0].name}` : `${downloads.length} exports ready`}
        {fmt && <span className="ml-2 text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>{fmt}</span>}
      </p>
      <div className="space-y-2">
        {downloads.map((d, i) => (
          <a
            key={i}
            href={d.download_url}
            download
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{ background: 'var(--color-accent)', color: '#fff' }}
            onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.9'; }}
            onMouseLeave={(e) => { e.currentTarget.style.opacity = '1'; }}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            Download {d.name}.zip{d.format ? ` (${d.format})` : ""}
          </a>
        ))}
      </div>
    </div>
  );
}

function DataTable({ data }: { data: Record<string, any> }) {
  const items = data.agents ?? data.roles ?? data.skills ?? data.results ?? [];
  if (!Array.isArray(items) || items.length === 0) {
    return <p className="text-sm text-gray-500">暂无数据</p>;
  }
  return (
    <div className="space-y-2">
      {items.map((item: any, i: number) => {
        if (data.agents) return <AgentCard key={item.id ?? i} data={item} />;
        if (data.roles) return <RoleCard key={item.id ?? i} data={item} />;
        if (data.skills || data.results) return <SkillCard key={item.id ?? i} data={item} />;
        return null;
      })}
    </div>
  );
}

const COMPONENT_MAP: Record<string, Record<string, React.ComponentType<{ data: Record<string, any> }>>> = {
  agent: {
    created: AgentCard,
    detailed: AgentDetail,
    updated: AgentCard,
    listed: DataTable,
    deleted: DeleteResult,
    confirm_required: ConfirmDialog,
  },
  role: {
    created: RoleCard,
    updated: RoleCard,
    editing: MarkdownEditor,
    listed: DataTable,
    deleted: DeleteResult,
    confirm_required: ConfirmDialog,
  },
  skill: {
    created: SkillCard,
    updated: SkillCard,
    editing: MarkdownEditor,
    listed: DataTable,
    deleted: DeleteResult,
    confirm_required: ConfirmDialog,
  },
  scope: {
    updated: MarkdownPreview,
    editing: MarkdownEditor,
  },
  commitment: {
    updated: YamlPreview,
    editing: YamlEditor,
  },
  deploy: {
    exported: DeployLog,
  },
};

export function StructuredBlockRenderer({ structured }: { structured: StructuredData }) {
  const Component = COMPONENT_MAP[structured.type]?.[structured.action];
  if (!Component) return null;
  return <Component data={structured.data} />;
}
