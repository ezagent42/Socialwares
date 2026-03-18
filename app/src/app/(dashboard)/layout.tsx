import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { signOut } from "@/lib/auth";
import { LayoutDashboard, MessageSquare, LogOut } from "lucide-react";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session) redirect("/login");

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 border-r bg-muted/30 flex flex-col">
        <div className="p-4 border-b">
          <span className="font-semibold text-sm">Socialwares</span>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          <Link
            href="/rooms"
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-muted"
          >
            <LayoutDashboard className="h-4 w-4" />
            Rooms
          </Link>
        </nav>
        <div className="p-2 border-t">
          <div className="px-3 py-1 text-xs text-muted-foreground truncate">
            {session.user?.email}
          </div>
          <form
            action={async () => {
              "use server";
              await signOut({ redirectTo: "/login" });
            }}
          >
            <button
              type="submit"
              className="flex items-center gap-2 w-full px-3 py-2 text-sm rounded-md hover:bg-muted text-left"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </form>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
