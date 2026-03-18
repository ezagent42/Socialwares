import { auth } from "@/lib/auth";
import { roomsApi } from "@/lib/api";
import { notFound } from "next/navigation";
import { AgentChat } from "@/components/agent/agent-chat";

interface Props {
  params: Promise<{ roomId: string }>;
}

export default async function RoomPage({ params }: Props) {
  const { roomId } = await params;
  const session = await auth();

  let room;
  try {
    room = await roomsApi.get(session!.accessToken, roomId);
  } catch {
    notFound();
  }

  return (
    <div className="h-screen flex flex-col">
      <div className="border-b px-6 py-3 flex items-center gap-2">
        <span className="font-medium">{room.display_name}</span>
        <span className="text-xs text-muted-foreground">#{room.name}</span>
      </div>
      <div className="flex-1 overflow-hidden">
        <AgentChat room={room} token={session!.accessToken} />
      </div>
    </div>
  );
}
