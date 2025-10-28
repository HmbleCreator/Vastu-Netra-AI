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

interface GraphLayoutParams {
  rooms_needed: string[];
  plot_dimensions: [number, number];
  orientation: string;
  vastu_constraints?: Record<string, boolean>;
  total_area?: number;
}

interface Vector2D {
  x: number;
  y: number;
}

// Room size specifications (in meters)
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

// Adjacency graph: which rooms should be close to each other
const ADJACENCY_GRAPH: Record<string, string[]> = {
  kitchen: ['dining', 'living'],
  dining: ['kitchen', 'living'],
  living: ['dining', 'master_bedroom', 'bedroom'],
  master_bedroom: ['bathroom', 'living'],
  bedroom: ['bathroom', 'living'],
  bathroom: ['bedroom', 'master_bedroom'],
  study: ['living'],
  hall: ['living', 'dining'],
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

function getVastuDirection(type: string, orientation: string): Vector2D {
  const forceStrength = 2.0;
  const directions: Record<string, Vector2D> = {
    kitchen: { x: forceStrength, y: forceStrength }, // Southeast
    master_bedroom: { x: -forceStrength, y: forceStrength }, // Southwest
    bedroom: { x: forceStrength, y: -forceStrength }, // Northeast or Northwest
    bathroom: { x: -forceStrength, y: -forceStrength }, // Northwest
    living: { x: 0, y: -forceStrength }, // North or East
    dining: { x: forceStrength, y: 0 }, // East
    study: { x: -forceStrength, y: 0 }, // West
    hall: { x: 0, y: -forceStrength }, // North
  };
  return directions[type] || { x: 0, y: 0 };
}

function calculateForces(rooms: Room[], adjacency: Map<string, Set<string>>): Map<string, Vector2D> {
  const forces = new Map<string, Vector2D>();
  
  // Initialize forces
  rooms.forEach(room => forces.set(room.id, { x: 0, y: 0 }));
  
  // Calculate pairwise forces
  for (let i = 0; i < rooms.length; i++) {
    for (let j = i + 1; j < rooms.length; j++) {
      const roomA = rooms[i];
      const roomB = rooms[j];
      
      const centerA = { x: roomA.x + roomA.width / 2, y: roomA.y + roomA.height / 2 };
      const centerB = { x: roomB.x + roomB.width / 2, y: roomB.y + roomB.height / 2 };
      
      const dx = centerB.x - centerA.x;
      const dy = centerB.y - centerA.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 0.1;
      
      const dirX = dx / distance;
      const dirY = dy / distance;
      
      const isAdjacent = adjacency.get(roomA.type)?.has(roomB.type) || 
                         adjacency.get(roomB.type)?.has(roomA.type);
      
      let forceX = 0, forceY = 0;
      
      if (isAdjacent) {
        // Attractive force
        const idealDistance = (roomA.width + roomB.width) / 2 + 0.5;
        const forceMagnitude = 0.5 * (distance - idealDistance);
        forceX = forceMagnitude * dirX;
        forceY = forceMagnitude * dirY;
      } else {
        // Repulsive force
        const forceMagnitude = 5.0 / distance;
        forceX = -forceMagnitude * dirX;
        forceY = -forceMagnitude * dirY;
      }
      
      const forceA = forces.get(roomA.id)!;
      const forceB = forces.get(roomB.id)!;
      
      forces.set(roomA.id, { x: forceA.x + forceX, y: forceA.y + forceY });
      forces.set(roomB.id, { x: forceB.x - forceX, y: forceB.y - forceY });
    }
  }
  
  return forces;
}

function resolveOverlaps(rooms: Room[]): void {
  const maxIterations = 10;
  for (let iter = 0; iter < maxIterations; iter++) {
    let hasOverlap = false;
    
    for (let i = 0; i < rooms.length; i++) {
      for (let j = i + 1; j < rooms.length; j++) {
        const roomA = rooms[i];
        const roomB = rooms[j];
        
        const overlapX = Math.min(roomA.x + roomA.width, roomB.x + roomB.width) - 
                         Math.max(roomA.x, roomB.x);
        const overlapY = Math.min(roomA.y + roomA.height, roomB.y + roomB.height) - 
                         Math.max(roomA.y, roomB.y);
        
        if (overlapX > 0 && overlapY > 0) {
          hasOverlap = true;
          
          // Push apart in the direction of least overlap
          if (overlapX < overlapY) {
            const pushAmount = overlapX / 2 + 0.1;
            if (roomA.x < roomB.x) {
              roomA.x -= pushAmount;
              roomB.x += pushAmount;
            } else {
              roomA.x += pushAmount;
              roomB.x -= pushAmount;
            }
          } else {
            const pushAmount = overlapY / 2 + 0.1;
            if (roomA.y < roomB.y) {
              roomA.y -= pushAmount;
              roomB.y += pushAmount;
            } else {
              roomA.y += pushAmount;
              roomB.y -= pushAmount;
            }
          }
        }
      }
    }
    
    if (!hasOverlap) break;
  }
}

function snapToGrid(rooms: Room[]): void {
  const gridSize = 0.5;
  rooms.forEach(room => {
    room.x = Math.round(room.x / gridSize) * gridSize;
    room.y = Math.round(room.y / gridSize) * gridSize;
    room.width = Math.round(room.width / gridSize) * gridSize;
    room.height = Math.round(room.height / gridSize) * gridSize;
  });
}

function generateGraphLayout(params: GraphLayoutParams): Room[] {
  const [plotWidth, plotHeight] = params.plot_dimensions;
  const rooms: Room[] = [];
  
  // Create adjacency map
  const adjacency = new Map<string, Set<string>>();
  Object.entries(ADJACENCY_GRAPH).forEach(([key, values]) => {
    adjacency.set(key, new Set(values));
  });
  
  // Calculate room sizes
  const totalRequestedArea = params.total_area || 150; // Default 150 sqm
  const areaPerRoom = totalRequestedArea / params.rooms_needed.length;
  
  // Initialize rooms at random positions
  params.rooms_needed.forEach((roomName, index) => {
    const roomType = normalizeRoomType(roomName);
    const { width, height } = calculateRoomDimensions(roomType, areaPerRoom);
    
    rooms.push({
      id: `${roomType}_${index + 1}`,
      name: roomName.charAt(0).toUpperCase() + roomName.slice(1).replace(/_/g, ' '),
      type: roomType,
      x: Math.random() * (plotWidth - width),
      y: Math.random() * (plotHeight - height),
      width,
      height,
      direction: 'interior',
      vastuScore: 80,
    });
  });
  
  // Physics simulation
  const velocities = new Map<string, Vector2D>();
  rooms.forEach(room => velocities.set(room.id, { x: 0, y: 0 }));
  
  const maxIterations = 100;
  const damping = 0.8;
  const timeStep = 0.1;
  
  for (let iter = 0; iter < maxIterations; iter++) {
    const forces = calculateForces(rooms, adjacency);
    
    // Add Vastu directional forces
    rooms.forEach(room => {
      const vastuForce = getVastuDirection(room.type, params.orientation);
      const currentForce = forces.get(room.id)!;
      forces.set(room.id, {
        x: currentForce.x + vastuForce.x,
        y: currentForce.y + vastuForce.y,
      });
    });
    
    // Update positions
    let maxVelocity = 0;
    rooms.forEach(room => {
      const force = forces.get(room.id)!;
      const velocity = velocities.get(room.id)!;
      
      velocity.x = (velocity.x + force.x) * damping;
      velocity.y = (velocity.y + force.y) * damping;
      
      room.x += velocity.x * timeStep;
      room.y += velocity.y * timeStep;
      
      // Clamp to boundaries
      room.x = Math.max(1, Math.min(plotWidth - room.width - 1, room.x));
      room.y = Math.max(1, Math.min(plotHeight - room.height - 1, room.y));
      
      maxVelocity = Math.max(maxVelocity, Math.abs(velocity.x), Math.abs(velocity.y));
    });
    
    // Check convergence
    if (maxVelocity < 0.01) break;
  }
  
  // Resolve overlaps
  resolveOverlaps(rooms);
  
  // Snap to grid
  snapToGrid(rooms);
  
  return rooms;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const params: GraphLayoutParams = await req.json();
    console.log('Graph layout generation started:', params);
    
    const startTime = Date.now();
    const rooms = generateGraphLayout(params);
    const generationTime = (Date.now() - startTime) / 1000;
    
    console.log(`Graph layout generated in ${generationTime}s with ${rooms.length} rooms`);
    
    return new Response(JSON.stringify({
      status: 'success',
      solver: 'graph',
      generation_time: generationTime,
      rooms,
      plotWidth: params.plot_dimensions[0],
      plotLength: params.plot_dimensions[1],
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Graph layout generation error:', error);
    return new Response(JSON.stringify({
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
