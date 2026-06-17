"use client";

import type { Message } from "@/lib/types";
import { StructuredBlockRenderer } from "./structured-block-renderer";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isUIAction = message.source === "ui_action";

  if (isUser) {
    return (
      <div className="flex justify-end">
        {isUIAction ? (
          <span className="text-xs italic px-3 py-1 rounded-full" style={{ color: 'var(--text-tertiary)', background: 'var(--bg-tertiary)' }}>
            {message.content}
          </span>
        ) : (
          <div className="rounded-2xl rounded-br-md px-4 py-2.5 max-w-[80%] text-sm text-white" style={{ background: 'var(--color-accent)' }}>
            {message.content}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-full space-y-3">
        {message.content && (
          <div className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
            {message.content}
          </div>
        )}
        {message.structured && <StructuredBlockRenderer structured={message.structured} />}
      </div>
    </div>
  );
}
