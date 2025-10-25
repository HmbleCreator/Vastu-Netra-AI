import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface Room {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  direction: string;
  vastuScore?: number;
}

interface ConstraintLayoutParams {
  rooms_needed: string[];
  plot_dimensions: [number, number];
  orientation: string;
  vastu_constraints?: Record<string, boolean>;
  total_area?: number;
}

const ROOM_SPECS: Record<string, { minArea: number; maxArea: number; aspectRatio: number }> = {
  kitchen: { minArea: 11, maxArea: 17, aspectRatio: 1.2 },
  living: { minArea: 28, maxArea: 37, aspectRatio: 1.3 },
  master_bedroom: { minArea: 19, maxArea: 23, aspectRatio: 1.2 },
  bedroom: { minArea: 14, maxArea: 17, aspectRatio: 1.15 },
  bathroom: { minArea: 4, maxArea: 6, aspectRatio: 1.0 },
  dining: { minArea: 12, maxArea: 16, aspectRatio: 1.2 },
  study: { minArea: 10, maxArea: 14, aspectRatio: 1.1 },
  hall: { minArea: 28, maxArea: 37, aspectRatio: 1.3 },
};

function normalizeRoomType(type: string): string {
  const normalized = type.toLowerCase().replace(/[_\s]+/g, '_');
  if (normalized.includes('living') || normalized.includes('hall')) return 'living';
  if (normalized.includes('kitchen')) return 'kitchen';
  if (normalized.includes('master') || normalized.includes('main')) return 'master_bedroom';
  if (normalized.includes('bedroom') || normalized.includes('bed')) return 'bedroom';
  if (normalized.includes('bathroom') || normalized.includes('toilet')) return 'bathroom';
  if (normalized.includes('dining')) return 'dining';
  if (normalized.includes('study')) return 'study';
  return 'bedroom';
}

function calculateRoomDimensions(type: string, targetArea: number): { width: number; height: number } {
  const spec = ROOM_SPECS[type] || ROOM_SPECS.bedroom;
  const area = Math.max(spec.minArea, Math.min(spec.maxArea, targetArea));
  const width = Math.sqrt(area / spec.aspectRatio);
  const height = width * spec.aspectRatio;
  return { width, height };
}

function getVastuPreferredPosition(type: string, plotWidth: number, plotHeight: number): { x: number; y: number } {
  // Return preferred quadrant based on Vastu
  const positions: Record<string, { x: number; y: number }> = {
    kitchen: { x: plotWidth * 0.6, y: plotHeight * 0.6 }, // Southeast
    master_bedroom: { x: plotWidth * 0.3, y: plotHeight * 0.6 }, // Southwest
    bedroom: { x: plotWidth * 0.6, y: plotHeight * 0.3 }, // Northeast/Northwest
    bathroom: { x: plotWidth * 0.3, y: plotHeight * 0.3 }, // Northwest
    living: { x: plotWidth * 0.5, y: plotHeight * 0.3 }, // North/East
    dining: { x: plotWidth * 0.6, y: plotHeight * 0.5 }, // East
    study: { x: plotWidth * 0.3, y: plotHeight * 0.5 }, // West
    hall: { x: plotWidth * 0.5, y: plotHeight * 0.3 }, // North
  };
  return positions[type] || { x: plotWidth * 0.5, y: plotHeight * 0.5 };
}

function checkOverlap(room1: Room, room2: Room, margin: number = 0.5): boolean {
  return !(room1.x + room1.width + margin <= room2.x ||
           room2.x + room2.width + margin <= room1.x ||
           room1.y + room1.height + margin <= room2.y ||
           room2.y + room2.height + margin <= room1.y);
}

function generateConstraintLayout(params: ConstraintLayoutParams): Room[] {
  const [plotWidth, plotHeight] = params.plot_dimensions;
  const rooms: Room[] = [];
  
  // Calculate room sizes
  const totalRequestedArea = params.total_area || 150;
  const areaPerRoom = totalRequestedArea / params.rooms_needed.length;
  
  // Sort rooms by priority: larger rooms and Vastu-important rooms first
  const roomPriority: Record<string, number> = {
    master_bedroom: 1,
    kitchen: 2,
    living: 3,
    bedroom: 4,
    dining: 5,
    study: 6,
    bathroom: 7,
  };
  
  const sortedRoomNames = [...params.rooms_needed].sort((a, b) => {
    const typeA = normalizeRoomType(a);
    const typeB = normalizeRoomType(b);
    return (roomPriority[typeA] || 10) - (roomPriority[typeB] || 10);
  });
  
  // Greedy placement algorithm
  sortedRoomNames.forEach((roomName, index) => {
    const roomType = normalizeRoomType(roomName);
    const { width, height } = calculateRoomDimensions(roomType, areaPerRoom);
    
    // Get Vastu preferred position
    const preferred = getVastuPreferredPosition(roomType, plotWidth, plotHeight);
    
    // Try positions in a grid pattern around the preferred position
    let placed = false;
    const gridStep = 1.0;
    const maxAttempts = 100;
    
    for (let attempt = 0; attempt < maxAttempts && !placed; attempt++) {
      // Spiral search pattern from preferred position
      const radius = Math.floor(attempt / 8) * gridStep;
      const angle = (attempt % 8) * Math.PI / 4;
      
      const testX = Math.max(1, Math.min(plotWidth - width - 1, 
                    preferred.x - width / 2 + radius * Math.cos(angle)));
      const testY = Math.max(1, Math.min(plotHeight - height - 1,
                    preferred.y - height / 2 + radius * Math.sin(angle)));
      
      const testRoom: Room = {
        id: `${roomType}_${index + 1}`,
        name: roomName.charAt(0).toUpperCase() + roomName.slice(1).replace(/_/g, ' '),
        type: roomType,
        x: testX,
        y: testY,
        width,
        height,
        direction: 'interior',
        vastuScore: 80,
      };
      
      // Check for overlaps with existing rooms
      let hasOverlap = false;
      for (const existingRoom of rooms) {
        if (checkOverlap(testRoom, existingRoom)) {
          hasOverlap = true;
          break;
        }
      }
      
      if (!hasOverlap) {
        rooms.push(testRoom);
        placed = true;
      }
    }
    
    // If still not placed, force placement in any available space
    if (!placed) {
      const fallbackRoom: Room = {
        id: `${roomType}_${index + 1}`,
        name: roomName.charAt(0).toUpperCase() + roomName.slice(1).replace(/_/g, ' '),
        type: roomType,
        x: 1 + (index % 3) * (plotWidth / 3),
        y: 1 + Math.floor(index / 3) * (plotHeight / 3),
        width,
        height,
        direction: 'interior',
        vastuScore: 60,
      };
      rooms.push(fallbackRoom);
    }
  });
  
  // Snap to grid
  rooms.forEach(room => {
    const gridSize = 0.5;
    room.x = Math.round(room.x / gridSize) * gridSize;
    room.y = Math.round(room.y / gridSize) * gridSize;
    room.width = Math.round(room.width / gridSize) * gridSize;
    room.height = Math.round(room.height / gridSize) * gridSize;
  });
  
  return rooms;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const params: ConstraintLayoutParams = await req.json();
    console.log('Constraint layout generation started:', params);
    
    const startTime = Date.now();
    const rooms = generateConstraintLayout(params);
    const generationTime = (Date.now() - startTime) / 1000;
    
    console.log(`Constraint layout generated in ${generationTime}s with ${rooms.length} rooms`);
    
    return new Response(JSON.stringify({
      status: 'success',
      solver: 'constraint',
      generation_time: generationTime,
      rooms,
      plotWidth: params.plot_dimensions[0],
      plotLength: params.plot_dimensions[1],
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Constraint layout generation error:', error);
    return new Response(JSON.stringify({
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
