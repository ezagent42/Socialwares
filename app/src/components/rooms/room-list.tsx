"use client";

import { useState } from "react";
import type { Room } from "@/types";
import { RoomCard } from "./room-card";
import { Button } from "@/components/ui/button";
import { roomsApi, ApiError } from "@/lib/api";
import { Plus } from "lucide-react";

interface Props {
  initialRooms: Room[];
  token: string;
}

export function RoomList({ initialRooms, token }: Props) {
  const [rooms, setRooms] = useState(initialRooms);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setCreating(true);

    const form = new FormData(e.currentTarget);
    try {
      const room = await roomsApi.create(token, {
        name: form.get("name") as string,
        display_name: form.get("display_name") as string,
      });
      setRooms((prev) => [room, ...prev]);
      setShowForm(false);
      (e.target as HTMLFormElement).reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create room");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>
          <Plus className="h-4 w-4" />
          New Room
        </Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="border rounded-lg p-4 space-y-3">
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="space-y-1">
            <label className="text-sm font-medium">Name (slug)</label>
            <input
              name="name"
              required
              pattern="^[a-z0-9-]+$"
              placeholder="my-room"
              className="w-full px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground">lowercase letters, numbers, hyphens only</p>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Display Name</label>
            <input
              name="display_name"
              required
              placeholder="My Room"
              className="w-full px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={creating}>
              {creating ? "Creating..." : "Create"}
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={() => setShowForm(false)}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {rooms.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-12">
          No rooms yet. Create one to get started.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {rooms.map((room) => (
            <RoomCard key={room.id} room={room} />
          ))}
        </div>
      )}
    </div>
  );
}
