import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentForge",
  description: "Agent creation and configuration management platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){
            try {
              var t = localStorage.getItem('forge-theme');
              if (t === 'dark' || t === 'light') { document.documentElement.className = t; }
              else if (window.matchMedia('(prefers-color-scheme: dark)').matches) { document.documentElement.className = 'dark'; }
            } catch(e) {}
          })();
        `}} />
      </head>
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
