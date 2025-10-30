import { Room } from '@/components/RoomAdjustmentPanel';

interface FloorPlanJSON {
  rooms: Room[];
  plotWidth?: number;
  plotLength?: number;
  plotShape?: string;
  constraints?: {
    plot_polygon?: number[][];
    circle?: { center: [number, number]; radius: number };
  };
  plot_polygon?: number[][];
  circle?: { center: [number, number]; radius: number };
}

export function extractFloorPlanData(content: string): FloorPlanJSON | null {
  try {
    // Primary: Look for JSON fenced code block (markdown)
    let jsonStr: string | null = null;
    const fencedMatch = content.match(/```json\s*([\s\S]*?)\s*```/i);
    if (fencedMatch) {
      jsonStr = fencedMatch[1];
    }

    // Secondary: Some markdown renderers convert code blocks to HTML (<pre><code class="language-json">...)
    // Try to extract JSON inside HTML code blocks if fenced markdown not present
    if (!jsonStr) {
      const htmlCodeMatch = content.match(/<pre[^>]*>\s*<code[^>]*(?:class=["'][^"']*json[^"']*["'])?[^>]*>([\s\S]*?)<\/code>\s*<\/pre>/i)
        || content.match(/<code[^>]*(?:class=["'][^"']*json[^"']*["'])?[^>]*>([\s\S]*?)<\/code>/i);
      if (htmlCodeMatch) {
        // inner HTML may contain escaped entities - unescape common ones
        const htmlInner = htmlCodeMatch[1];
        jsonStr = htmlInner
          .replace(/&quot;/g, '"')
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&#39;/g, "'");
      }
    }

    // Tertiary fallback: try to find a JSON object containing a "rooms" key anywhere in the text
    if (!jsonStr) {
      const looseJsonMatch = content.match(/(\{[\s\S]*?"rooms"\s*:\s*\[[\s\S]*?\][\s\S]*?\})/i);
      if (looseJsonMatch) jsonStr = looseJsonMatch[1];
    }

    if (!jsonStr) return null;

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

    // Units detection (default meters); convert if feet provided
    const unitsRaw = (data as any).units || (data as any).unit;
    const units = typeof unitsRaw === 'string' ? unitsRaw.toLowerCase() : 'meters';
    const toMeters = units.includes('ft') || units.includes('feet') ? 0.3048 : 1.0;

    // Convert rooms to meters if needed
    const roomsInMeters = validRooms.map(r => ({
      ...r,
      x: r.x * toMeters,
      y: r.y * toMeters,
      width: r.width * toMeters,
      height: r.height * toMeters,
    }));

    // Extract optional polygon/circle either top-level or under constraints
    let polygon = data.plot_polygon || data.constraints?.plot_polygon;
    let circle = data.circle || data.constraints?.circle;
    // Convert polygon and circle units if provided
    if (Array.isArray(polygon)) {
      polygon = polygon.map(([x, y]) => [x * toMeters, y * toMeters]);
    }
    if (circle && typeof circle === 'object') {
      circle = {
        center: [circle.center[0] * toMeters, circle.center[1] * toMeters] as [number, number],
        radius: circle.radius * toMeters,
      };
    }

    return {
      rooms: roomsInMeters,
      plotWidth: (data.plotWidth || 30) * toMeters,
      plotLength: (data.plotLength || 30) * toMeters,
      plotShape: data.plotShape || 'rectangular',
      // Pass through optional shape constraints for downstream consumers
      constraints: {
        plot_polygon: Array.isArray(polygon) ? polygon : undefined,
        circle: circle && typeof circle === 'object' ? circle : undefined,
      },
      plot_polygon: Array.isArray(polygon) ? polygon : undefined,
      circle: circle && typeof circle === 'object' ? circle : undefined,
    } as FloorPlanJSON;
  } catch (error) {
    console.error('Failed to parse floor plan JSON:', error);
    return null;
  }
}
