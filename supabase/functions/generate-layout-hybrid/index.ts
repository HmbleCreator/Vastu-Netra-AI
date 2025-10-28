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

interface LayoutResult {
  status: string;
  solver: string;
  generation_time: number;
  rooms: Room[];
  plotWidth: number;
  plotLength: number;
}

interface HybridLayoutParams {
  rooms_needed: string[];
  plot_dimensions: [number, number];
  orientation: string;
  vastu_constraints?: Record<string, boolean>;
  total_area?: number;
}

function checkOverlap(room1: Room, room2: Room): boolean {
  return !(room1.x + room1.width <= room2.x ||
           room2.x + room2.width <= room1.x ||
           room1.y + room1.height <= room2.y ||
           room2.y + room2.height <= room1.y);
}

function evaluateQuality(layout: LayoutResult): number {
  let score = 100;
  const rooms = layout.rooms;
  
  // Penalty for overlaps
  for (let i = 0; i < rooms.length; i++) {
    for (let j = i + 1; j < rooms.length; j++) {
      if (checkOverlap(rooms[i], rooms[j])) {
        const overlapArea = Math.min(
          rooms[i].x + rooms[i].width - rooms[j].x,
          rooms[j].x + rooms[j].width - rooms[i].x
        ) * Math.min(
          rooms[i].y + rooms[i].height - rooms[j].y,
          rooms[j].y + rooms[j].height - rooms[i].y
        );
        score -= Math.abs(overlapArea) / 10;
      }
    }
  }
  
  // Penalty for rooms outside boundaries
  for (const room of rooms) {
    if (room.x < 0 || room.y < 0 ||
        room.x + room.width > layout.plotWidth ||
        room.y + room.height > layout.plotLength) {
      score -= 15;
    }
  }
  
  // Calculate space utilization
  const totalRoomArea = rooms.reduce((sum, room) => sum + room.width * room.height, 0);
  const plotArea = layout.plotWidth * layout.plotLength;
  const utilization = totalRoomArea / plotArea;
  
  if (utilization < 0.4) {
    score -= (0.4 - utilization) * 50;
  } else if (utilization > 0.85) {
    score -= (utilization - 0.85) * 100;
  }
  
  // Bonus for good Vastu compliance (average room vastuScore)
  const avgVastuScore = rooms.reduce((sum, room) => sum + (room.vastuScore || 0), 0) / rooms.length;
  score += (avgVastuScore - 70) * 0.2;
  
  return Math.max(0, Math.min(100, score));
}

function generateGridFallback(params: HybridLayoutParams): Room[] {
  const [plotWidth, plotHeight] = params.plot_dimensions;
  const rooms: Room[] = [];
  
  const roomWidth = 4.0;
  const roomHeight = 5.0;
  const gap = 1.0;
  const cols = Math.floor(plotWidth / (roomWidth + gap));
  
  let x = 1.0;
  let y = 1.0;
  let col = 0;
  
  params.rooms_needed.forEach((roomName, index) => {
    rooms.push({
      id: `room_${index + 1}`,
      name: roomName.charAt(0).toUpperCase() + roomName.slice(1).replace(/_/g, ' '),
      type: roomName.toLowerCase(),
      x,
      y,
      width: roomWidth,
      height: roomHeight,
      direction: 'interior',
      vastuScore: 50,
    });
    
    col++;
    if (col >= cols) {
      col = 0;
      x = 1.0;
      y += roomHeight + gap;
    } else {
      x += roomWidth + gap;
    }
  });
  
  return rooms;
}

async function callSolver(solverName: string, params: HybridLayoutParams): Promise<LayoutResult | null> {
  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    if (!supabaseUrl) throw new Error('SUPABASE_URL not configured');
    
    const response = await fetch(`${supabaseUrl}/functions/v1/generate-layout-${solverName}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });
    
    if (!response.ok) {
      console.error(`${solverName} solver failed with status ${response.status}`);
      return null;
    }
    
    const result = await response.json();
    if (result.status !== 'success') {
      console.error(`${solverName} solver returned error:`, result.error);
      return null;
    }
    
    return result as LayoutResult;
  } catch (error) {
    console.error(`${solverName} solver error:`, error);
    return null;
  }
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const params: HybridLayoutParams = await req.json();
    console.log('Hybrid layout generation started:', params);
    
    const startTime = Date.now();
    const results: Array<{ layout: LayoutResult; score: number }> = [];
    
    // Try graph solver first (fast)
    console.log('Trying graph solver...');
    const graphLayout = await callSolver('graph', params);
    if (graphLayout) {
      const score = evaluateQuality(graphLayout);
      console.log(`Graph solver succeeded with quality score: ${score}`);
      results.push({ layout: graphLayout, score });
    }
    
    // Try constraint solver if we have time and graph didn't produce excellent results
    const elapsed = (Date.now() - startTime) / 1000;
    if (elapsed < 10 && (!graphLayout || results[0]?.score < 85)) {
      console.log('Trying constraint solver...');
      const constraintLayout = await callSolver('constraint', params);
      if (constraintLayout) {
        const score = evaluateQuality(constraintLayout);
        console.log(`Constraint solver succeeded with quality score: ${score}`);
        results.push({ layout: constraintLayout, score });
      }
    }
    
    // Pick best result or use fallback
    let finalLayout: LayoutResult;
    
    if (results.length > 0) {
      // Sort by score and pick best
      results.sort((a, b) => b.score - a.score);
      finalLayout = results[0].layout;
      console.log(`Using ${finalLayout.solver} solver (score: ${results[0].score})`);
    } else {
      // Both solvers failed, use grid fallback
      console.log('Both solvers failed, using grid fallback');
      const fallbackRooms = generateGridFallback(params);
      finalLayout = {
        status: 'success',
        solver: 'fallback_grid',
        generation_time: (Date.now() - startTime) / 1000,
        rooms: fallbackRooms,
        plotWidth: params.plot_dimensions[0],
        plotLength: params.plot_dimensions[1],
      };
    }
    
    const totalTime = (Date.now() - startTime) / 1000;
    console.log(`Hybrid layout generation completed in ${totalTime}s`);
    
    return new Response(JSON.stringify({
      ...finalLayout,
      total_generation_time: totalTime,
      quality_score: results.length > 0 ? results[0].score : 50,
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Hybrid layout generation error:', error);
    return new Response(JSON.stringify({
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
