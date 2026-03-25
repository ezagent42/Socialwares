import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Socialware Chat",
  description: "Agent interaction visualization",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
