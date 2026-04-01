"use client";

import { useChatStore } from "@/lib/chat-store";
import { AgentCard } from "./cards/agent-card";
import { BatchActionBar } from "./batch-action-bar";

export function DashboardPanel() {
  const agents = useChatStore((s) => s.entities.agents);
  const list = Object.values(agents);

  return (
    <div className="h-full overflow-y-auto flex flex-col" style={{ background: 'var(--bg-secondary)' }}>
      <div className="px-4 py-3 border-b flex items-center justify-between shrink-0" style={{ borderColor: 'var(--border-primary)' }}>
        <h2 className="text-xs font-semibold tracking-wider uppercase" style={{ color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
          Agents
          {list.length > 0 && <span className="ml-1.5" style={{ color: 'var(--color-accent)' }}>{list.length}</span>}
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <BatchActionBar />

        {list.length === 0 ? (
          <div className="flex items-center justify-center h-full bg-grid rounded-xl">
            <div className="text-center py-16 anim-fade">
              <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>No agents yet</p>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Create one in the terminal</p>
            </div>
          </div>
        ) : (
          list.map((agent, i) => (
            <div key={agent.id} className="anim-slide" style={{ animationDelay: `${i * 50}ms` }}>
              <AgentCard data={agent} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
