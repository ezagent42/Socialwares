type MessageProps = {
  role: "user" | "agent" | "system";
  content: string;
};

export default function MessageBubble({ role, content }: MessageProps) {
  if (role === "system") {
    return (
      <div className="animate-fade-in-up flex justify-center my-3">
        <div
          className="px-4 py-2 rounded-full text-xs max-w-[90%] text-center"
          style={{
            background: "var(--amber-bg)",
            color: "var(--amber)",
            border: "1px solid var(--amber)",
            borderColor: "color-mix(in srgb, var(--amber) 25%, transparent)",
          }}
        >
          {content}
        </div>
      </div>
    );
  }

  const isUser = role === "user";

  return (
    <div className={`animate-fade-in-up flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className="flex gap-3 max-w-[85%]" style={{ flexDirection: isUser ? "row-reverse" : "row" }}>
        {/* Avatar */}
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-semibold shrink-0 mt-0.5"
          style={{
            background: isUser ? "var(--user-border)" : "var(--accent)",
            color: "#fff",
          }}
        >
          {isUser ? "U" : "A"}
        </div>

        {/* Bubble */}
        <div>
          <div
            className="text-[10px] font-medium mb-1 px-1"
            style={{ color: "var(--text-muted)", textAlign: isUser ? "right" : "left" }}
          >
            {isUser ? "You" : "Agent"}
          </div>
          <div
            className="px-4 py-2.5 rounded-xl text-sm leading-relaxed whitespace-pre-wrap"
            style={{
              background: isUser ? "var(--user-bg)" : "var(--agent-bg)",
              border: `1px solid ${isUser ? "var(--user-border)" : "var(--agent-border)"}`,
              color: "var(--text-primary)",
              fontFamily: role === "agent" ? "'JetBrains Mono', monospace" : "inherit",
              fontSize: role === "agent" ? "0.8125rem" : undefined,
            }}
          >
            {content}
          </div>
        </div>
      </div>
    </div>
  );
}
