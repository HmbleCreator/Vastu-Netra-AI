import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Move, Trash2, Plus } from 'lucide-react';
import { useState } from 'react';

export interface Room {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: string;
  direction?: string;
  vastuScore?: number;
}

interface RoomAdjustmentPanelProps {
  rooms: Room[];
  onUpdateRoom: (roomId: string, updates: Partial<Room>) => void;
  onDeleteRoom: (roomId: string) => void;
  onAddRoom: (room: Room) => void;
  selectedRoomId: string | null;
  onSelectRoom: (roomId: string | null) => void;
}

export function RoomAdjustmentPanel({ 
  rooms, 
  onUpdateRoom, 
  onDeleteRoom,
  onAddRoom,
  selectedRoomId,
  onSelectRoom
}: RoomAdjustmentPanelProps) {
  const [isAddingRoom, setIsAddingRoom] = useState(false);
  
  const selectedRoom = rooms.find(r => r.id === selectedRoomId);

  const handleAddRoom = () => {
    const newRoom: Room = {
      id: `room_${Date.now()}`,
      name: 'New Room',
      x: 0,
      y: 0,
      width: 3,
      height: 3,
      type: 'bedroom'
    };
    onAddRoom(newRoom);
    setIsAddingRoom(false);
    onSelectRoom(newRoom.id);
  };

  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Room Adjustments</h3>
        <Button
          size="sm"
          onClick={() => isAddingRoom ? handleAddRoom() : setIsAddingRoom(true)}
          disabled={rooms.length === 0}
        >
          <Plus className="mr-2 h-4 w-4" />
          Add Room
        </Button>
      </div>

      <div className="space-y-2">
        <Label>Select Room</Label>
        <Select value={selectedRoomId || ''} onValueChange={onSelectRoom}>
          <SelectTrigger>
            <SelectValue placeholder="Choose a room to edit" />
          </SelectTrigger>
          <SelectContent>
            {rooms.map((room) => (
              <SelectItem key={room.id} value={room.id}>
                {room.name} ({room.type})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedRoom && (
        <div className="space-y-4 border-t pt-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="room-name">Name</Label>
              <Input
                id="room-name"
                value={selectedRoom.name}
                onChange={(e) => onUpdateRoom(selectedRoom.id, { name: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="room-type">Type</Label>
              <Select
                value={selectedRoom.type}
                onValueChange={(type) => onUpdateRoom(selectedRoom.id, { type })}
              >
                <SelectTrigger id="room-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bedroom">Bedroom</SelectItem>
                  <SelectItem value="living_room">Living Room</SelectItem>
                  <SelectItem value="kitchen">Kitchen</SelectItem>
                  <SelectItem value="bathroom">Bathroom</SelectItem>
                  <SelectItem value="dining_room">Dining Room</SelectItem>
                  <SelectItem value="study_room">Study Room</SelectItem>
                  <SelectItem value="pooja_room">Pooja Room</SelectItem>
                  <SelectItem value="balcony">Balcony</SelectItem>
                  <SelectItem value="storage">Storage</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Position</Label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label htmlFor="x-pos" className="text-xs text-muted-foreground">X (meters)</Label>
                <Input
                  id="x-pos"
                  type="number"
                  step="0.1"
                  value={selectedRoom.x}
                  onChange={(e) => onUpdateRoom(selectedRoom.id, { x: parseFloat(e.target.value) })}
                />
              </div>
              <div>
                <Label htmlFor="y-pos" className="text-xs text-muted-foreground">Y (meters)</Label>
                <Input
                  id="y-pos"
                  type="number"
                  step="0.1"
                  value={selectedRoom.y}
                  onChange={(e) => onUpdateRoom(selectedRoom.id, { y: parseFloat(e.target.value) })}
                />
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Dimensions</Label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label htmlFor="width" className="text-xs text-muted-foreground">Width (m)</Label>
                <Input
                  id="width"
                  type="number"
                  step="0.1"
                  min="1"
                  value={selectedRoom.width}
                  onChange={(e) => onUpdateRoom(selectedRoom.id, { width: parseFloat(e.target.value) })}
                />
              </div>
              <div>
                <Label htmlFor="height" className="text-xs text-muted-foreground">Length (m)</Label>
                <Input
                  id="height"
                  type="number"
                  step="0.1"
                  min="1"
                  value={selectedRoom.height}
                  onChange={(e) => onUpdateRoom(selectedRoom.id, { height: parseFloat(e.target.value) })}
                />
              </div>
            </div>
          </div>

          <Button
            variant="destructive"
            size="sm"
            className="w-full"
            onClick={() => {
              onDeleteRoom(selectedRoom.id);
              onSelectRoom(null);
            }}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete Room
          </Button>
        </div>
      )}

      {!selectedRoom && rooms.length > 0 && (
        <div className="text-sm text-muted-foreground text-center py-4">
          Select a room to adjust its properties
        </div>
      )}

      {rooms.length === 0 && (
        <div className="text-sm text-muted-foreground text-center py-4">
          Generate a floor plan first
        </div>
      )}
    </Card>
  );
}
