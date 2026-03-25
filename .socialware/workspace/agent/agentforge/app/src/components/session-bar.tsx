type SessionBarProps = {
  connected: boolean;
  role?: string;
  adapter?: string;
  onDisconnect: () => void;
};

export default function SessionBar({ connected, role, adapter, onDisconnect }: SessionBarProps) {
  return (
    <div
      className="flex items-center justify-between px-5 py-3"
      style={{
        background: "var(--bg-secondary)",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-semibold"
          style={{ background: "var(--accent)", color: "#fff" }}
        >
          S
        </div>
        <span className="font-semibold text-base tracking-tight" style={{ color: "var(--text-primary)" }}>
          Socialware
        </span>
      </div>

      <div className="flex items-center gap-3">
        {connected ? (
          <>
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
              style={{ background: "var(--green-glow)", border: "1px solid var(--green)", color: "var(--green)" }}
            >
              <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: "var(--green)" }} />
              {role}
              <span style={{ color: "var(--text-muted)" }}>via</span>
              {adapter}
            </div>
            <button
              onClick={onDisconnect}
              className="text-xs px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer"
              style={{
                color: "var(--text-secondary)",
                border: "1px solid var(--border)",
                background: "transparent",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--red)";
                e.currentTarget.style.color = "var(--red)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              Disconnect
            </button>
          </>
        ) : (
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
            style={{ color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}
          >
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--text-muted)" }} />
            No Agent
          </div>
        )}
      </div>
    </div>
  );
}
