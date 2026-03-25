"use client";

import { useState, useEffect } from "react";
import { getWorkspaces } from "@/lib/api";

type Workspace = {
  room: string;
  app: string;
  path: string;
  has_runtime: boolean;
};

export default function Dashboard() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getWorkspaces()
      .then((data) => setWorkspaces(data.workspaces))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Workspaces</h1>
            <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
              Manage your Socialware App instances
            </p>
          </div>
          <a
            href="/"
            className="text-sm px-3 py-1.5 rounded-md"
            style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}
          >
            ← Chat
          </a>
        </div>

        {loading ? (
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading...</div>
        ) : workspaces.length === 0 ? (
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>No workspaces found.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {workspaces.map((ws) => (
              <div
                key={`${ws.room}/${ws.app}`}
                className="rounded-xl p-5"
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{ws.app}</span>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{
                      background: ws.has_runtime ? "var(--green-glow)" : "var(--amber-bg)",
                      color: ws.has_runtime ? "var(--green)" : "var(--amber)",
                      border: `1px solid ${ws.has_runtime ? "var(--green)" : "var(--amber)"}`,
                      borderColor: ws.has_runtime
                        ? "color-mix(in srgb, var(--green) 30%, transparent)"
                        : "color-mix(in srgb, var(--amber) 30%, transparent)",
                    }}
                  >
                    {ws.has_runtime ? "deployed" : "not deployed"}
                  </span>
                </div>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {ws.room} / {ws.app}
                </div>
                <div className="text-xs mt-1 font-mono" style={{ color: "var(--text-muted)" }}>
                  {ws.path}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
