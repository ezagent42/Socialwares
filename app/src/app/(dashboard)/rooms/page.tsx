import { auth } from "@/lib/auth";
import { roomsApi } from "@/lib/api";
import { RoomList } from "@/components/rooms/room-list";

export default async function RoomsPage() {
  const session = await auth();
  const rooms = await roomsApi.list(session!.accessToken).catch(() => []);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Rooms</h1>
      </div>
      <RoomList initialRooms={rooms} token={session!.accessToken} />
    </div>
  );
}
