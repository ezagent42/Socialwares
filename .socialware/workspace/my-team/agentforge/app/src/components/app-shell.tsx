"use client";

import { useState } from "react";
import { Sidebar } from "./sidebar";
import { ChatPanel } from "./chat-panel";
import { DashboardPanel } from "./dashboard-panel";

export function AppShell() {
  const [view, setView] = useState<"dashboard" | "chat">("chat");

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Sidebar */}
      <Sidebar currentView={view} onViewChange={setView} />

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Dashboard */}
        <div className={`${view === "dashboard" ? "flex-1" : "hidden lg:block lg:w-[380px]"} border-r overflow-hidden`} style={{ borderColor: 'var(--border-primary)' }}>
          <DashboardPanel />
        </div>

        {/* Chat */}
        <div className={`${view === "chat" ? "flex-1" : "hidden lg:flex lg:flex-1"} overflow-hidden`}>
          <ChatPanel />
        </div>
      </main>
    </div>
  );
}
