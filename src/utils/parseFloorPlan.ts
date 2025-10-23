import { Room } from '@/components/RoomAdjustmentPanel';

interface FloorPlanJSON {
  rooms: Room[];
  plotWidth?: number;
  plotLength?: number;
  plotShape?: string;
}

export function extractFloorPlanData(content: string): FloorPlanJSON | null {
  try {
    // Look for JSON code block
    const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
    if (!jsonMatch) return null;

    const jsonStr = jsonMatch[1];
    const data = JSON.parse(jsonStr) as FloorPlanJSON;

    // Validate the data structure
    if (!data.rooms || !Array.isArray(data.rooms)) return null;

    // Ensure all rooms have required properties
    const validRooms = data.rooms.filter(room => 
      room.id && room.name && room.type && room.direction &&
      typeof room.x === 'number' && typeof room.y === 'number' &&
      typeof room.width === 'number' && typeof room.height === 'number'
    );

    if (validRooms.length === 0) return null;

    return {
      rooms: validRooms,
      plotWidth: data.plotWidth || 30,
      plotLength: data.plotLength || 30,
      plotShape: data.plotShape || 'rectangular',
    };
  } catch (error) {
    console.error('Failed to parse floor plan JSON:', error);
    return null;
  }
}
