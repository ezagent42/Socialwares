"use client";

import { useEffect, useState } from "react";
import { useChatStore } from "@/lib/chat-store";
import { LoginPage } from "@/components/login-page";
import { AppShell } from "@/components/app-shell";

export default function Home() {
  const user = useChatStore((s) => s.user);
  const checkAuth = useChatStore((s) => s.checkAuth);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    checkAuth().then(() => setChecked(true));
  }, [checkAuth]);

  if (!checked) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: 'var(--bg-primary)' }}>
        <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--border-primary)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  if (!user) return <LoginPage />;
  return <AppShell />;
}
