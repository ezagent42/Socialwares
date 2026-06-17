"use client";

import { useState, useEffect } from "react";
import { useChatStore } from "@/lib/chat-store";

interface Props {
  currentView: string;
  onViewChange: (view: "dashboard" | "chat") => void;
}

export function Sidebar({ currentView, onViewChange }: Props) {
  const user = useChatStore((s) => s.user);
  const agentCount = Object.keys(useChatStore((s) => s.entities.agents)).length;
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [showLogout, setShowLogout] = useState(false);

  useEffect(() => {
    setTheme(document.documentElement.className === "light" ? "light" : "dark");
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.className = next;
    localStorage.setItem("forge-theme", next);
  };

  return (
    <div className="w-14 flex flex-col items-center py-4 gap-1 border-r shrink-0" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-primary)' }}>
      {/* Logo */}
      <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-4" style={{ background: 'var(--color-accent-subtle)' }}>
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ color: 'var(--color-accent)' }}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
        </svg>
      </div>

      {/* Nav items */}
      <NavButton
        active={currentView === "chat"}
        onClick={() => onViewChange("chat")}
        title="Terminal"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="m6.75 7.5 3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0 0 21 18V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v12a2.25 2.25 0 0 0 2.25 2.25Z" />
        </svg>
      </NavButton>

      <NavButton
        active={currentView === "dashboard"}
        onClick={() => onViewChange("dashboard")}
        title="Dashboard"
        badge={agentCount > 0 ? agentCount : undefined}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
        </svg>
      </NavButton>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Theme toggle */}
      <NavButton active={false} onClick={toggleTheme} title={theme === "dark" ? "Light mode" : "Dark mode"}>
        {theme === "dark" ? (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
          </svg>
        )}
      </NavButton>

      {/* User avatar + logout popover */}
      {user && (
        <div className="mt-2 relative">
          <button
            onClick={() => setShowLogout(!showLogout)}
            className="group relative"
            title={user.github_login}
          >
            {user.github_avatar ? (
              <img src={user.github_avatar} alt="" className="w-8 h-8 rounded-full ring-1 transition-all group-hover:ring-2" style={{ '--tw-ring-color': 'var(--border-primary)' } as React.CSSProperties} />
            ) : (
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium" style={{ background: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}>
                {user.github_login?.[0]?.toUpperCase()}
              </div>
            )}
          </button>

          {/* Logout popover */}
          {showLogout && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowLogout(false)} />
              <div
                className="absolute left-full bottom-0 ml-2 z-50 w-52 rounded-xl border p-3 anim-fade"
                style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-primary)', boxShadow: 'var(--shadow-lg)' }}
              >
                <div className="flex items-center gap-2.5 mb-3 pb-3 border-b" style={{ borderColor: 'var(--border-secondary)' }}>
                  {user.github_avatar && (
                    <img src={user.github_avatar} alt="" className="w-8 h-8 rounded-full" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>{user.github_name || user.github_login}</p>
                    <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>@{user.github_login}</p>
                  </div>
                </div>
                <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
                  Are you sure you want to log out?
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={async () => {
                      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
                      useChatStore.getState().setUser(null);
                    }}
                    className="flex-1 text-xs font-medium py-1.5 rounded-lg text-white transition-colors"
                    style={{ background: 'var(--color-danger)' }}
                  >
                    Log out
                  </button>
                  <button
                    onClick={() => setShowLogout(false)}
                    className="flex-1 text-xs font-medium py-1.5 rounded-lg border transition-colors"
                    style={{ borderColor: 'var(--border-primary)', color: 'var(--text-secondary)' }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function NavButton({ active, onClick, title, badge, children }: {
  active: boolean; onClick: () => void; title: string; badge?: number; children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="relative w-9 h-9 rounded-lg flex items-center justify-center transition-all"
      style={{
        background: active ? 'var(--color-accent-subtle)' : 'transparent',
        color: active ? 'var(--color-accent)' : 'var(--text-tertiary)',
      }}
    >
      {children}
      {badge != null && (
        <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center text-white" style={{ background: 'var(--color-accent)' }}>
          {badge}
        </span>
      )}
    </button>
  );
}
