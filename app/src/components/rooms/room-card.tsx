import Link from "next/link";
import type { Room } from "@/types";
import { MessageSquare } from "lucide-react";

interface Props {
  room: Room;
}

export function RoomCard({ room }: Props) {
  return (
    <Link
      href={`/rooms/${room.id}`}
      className="block border rounded-lg p-4 hover:bg-muted/50 transition-colors"
    >
      <div className="flex items-start gap-3">
        <div className="p-2 bg-muted rounded-md">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="min-w-0">
          <p className="font-medium text-sm truncate">{room.display_name}</p>
          <p className="text-xs text-muted-foreground">#{room.name}</p>
        </div>
      </div>
    </Link>
  );
}
