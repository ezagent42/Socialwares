"use client";

import ReactMarkdown from "react-markdown";
import { ActionButton } from "./action-button";

interface Props {
  data: Record<string, any>;
}

export function AgentDetail({ data }: Props) {
  const skills: any[] = data.skills ?? [];
  const roleMd: string = data.role_md ?? "";

  return (
    <div className="space-y-4 max-w-2xl">
      {/* Header */}
      <div className="rounded-xl border p-4" style={{ background: "var(--bg-elevated)", borderColor: "var(--border-primary)" }}>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold" style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>{data.name}</h2>
              {data.is_example && (
                <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full uppercase tracking-wider" style={{ background: "var(--color-accent-subtle)", color: "var(--color-accent)", fontFamily: "var(--font-mono)" }}>
                  EXAMPLE
                </span>
              )}
            </div>
            {data.description && <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>{data.description}</p>}
          </div>
          <div className="flex gap-1">
            <ActionButton entity="agent" action="export" data={data} label="Export" />
          </div>
        </div>
        <div className="flex gap-3 mt-3 text-xs" style={{ color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
          <span>{skills.length} skills</span>
        </div>
      </div>

      {/* Role / Identity */}
      <Section title="IDENTITY" icon="role">
        {roleMd ? (
          <div className="prose prose-sm max-w-none text-sm" style={{ color: "var(--text-secondary)" }}>
            <ReactMarkdown>{roleMd}</ReactMarkdown>
          </div>
        ) : (
          <Empty>No identity defined</Empty>
        )}
      </Section>

      {/* Skills */}
      <Section title="SKILLS" icon="skill" count={skills.length}>
        {skills.length === 0 ? (
          <Empty>No skills defined</Empty>
        ) : (
          <div className="space-y-2">
            {skills.map((skill, i) => (
              <div key={skill.id ?? i} className="rounded-lg border p-3" style={{ borderColor: "var(--border-secondary)", background: "var(--bg-secondary)" }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold" style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>{skill.name}</span>
                </div>
                {skill.description && <p className="text-xs mb-2" style={{ color: "var(--text-tertiary)" }}>{skill.description}</p>}
                {skill.skill_md && (
                  <details className="mt-2">
                    <summary className="text-[10px] font-medium cursor-pointer select-none" style={{ color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                      SKILL.md
                    </summary>
                    <pre className="mt-2 text-[11px] leading-relaxed p-3 rounded-md overflow-x-auto" style={{ background: "var(--bg-primary)", color: "var(--text-secondary)", fontFamily: "var(--font-mono)", border: "1px solid var(--border-secondary)" }}>
                      {skill.skill_md}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

function Section({ title, icon, count, children }: { title: string; icon: string; count?: number; children: React.ReactNode }) {
  const iconColor = {
    role: "#10b981",
    skill: "#f59e0b",
  }[icon] ?? "var(--text-tertiary)";

  return (
    <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border-primary)", background: "var(--bg-elevated)" }}>
      <div className="flex items-center gap-2 px-4 py-2.5 border-b" style={{ borderColor: "var(--border-secondary)" }}>
        <span className="w-2 h-2 rounded-sm" style={{ background: iconColor }} />
        <span className="text-[10px] font-semibold tracking-widest uppercase" style={{ color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
          {title}
        </span>
        {count != null && (
          <span className="text-[10px] font-medium" style={{ color: iconColor, fontFamily: "var(--font-mono)" }}>{count}</span>
        )}
      </div>
      <div className="p-4">
        {children}
      </div>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-xs italic" style={{ color: "var(--text-tertiary)" }}>{children}</p>;
}
