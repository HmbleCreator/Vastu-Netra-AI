import { Card } from '@/components/ui/card';
import { Room } from '@/components/RoomAdjustmentPanel';

interface FloorPlanViewerProps {
  rooms?: Room[];
  plotWidth?: number;
  plotLength?: number;
}

const getRoomColor = (type: string) => {
  const colors: Record<string, string> = {
    bedroom: 'hsl(var(--primary))',
    kitchen: 'hsl(var(--accent))',
    bathroom: 'hsl(210 100% 70%)',
    living: 'hsl(120 60% 70%)',
    dining: 'hsl(30 70% 70%)',
    study: 'hsl(270 60% 70%)',
    entrance: 'hsl(50 90% 70%)',
    other: 'hsl(var(--muted))',
  };
  return colors[type] || colors.other;
};

export function FloorPlanViewer({ rooms = [], plotWidth = 30, plotLength = 30 }: FloorPlanViewerProps) {
  if (rooms.length === 0) {
    return (
      <Card className="flex h-full items-center justify-center border-2 border-dashed border-border blueprint-grid">
        <div className="text-center text-muted-foreground">
          <p className="text-lg font-medium">No floor plan yet</p>
          <p className="text-sm">Ask the AI to generate a Vastu-compliant floor plan</p>
        </div>
      </Card>
    );
  }

  const scale = 15; // pixels per meter

  return (
    <Card className="h-full overflow-hidden border-2 border-border">
      <div className="h-full w-full overflow-auto p-4 bg-card">
        <svg
          width={plotWidth * scale + 40}
          height={plotLength * scale + 40}
          className="mx-auto"
          style={{ border: '2px solid hsl(var(--border))' }}
        >
          {/* Grid */}
          <defs>
            <pattern id="grid" width={scale} height={scale} patternUnits="userSpaceOnUse">
              <path
                d={`M ${scale} 0 L 0 0 0 ${scale}`}
                fill="none"
                stroke="hsl(var(--grid-color))"
                strokeWidth="0.5"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Plot boundary */}
          <rect
            x="20"
            y="20"
            width={plotWidth * scale}
            height={plotLength * scale}
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="2"
          />

          {/* Compass directions */}
          <text x={plotWidth * scale / 2 + 20} y="15" textAnchor="middle" className="fill-primary text-xs font-bold">N</text>
          <text x={plotWidth * scale / 2 + 20} y={plotLength * scale + 35} textAnchor="middle" className="fill-foreground text-xs">S</text>
          <text x="10" y={plotLength * scale / 2 + 20} textAnchor="middle" className="fill-foreground text-xs">W</text>
          <text x={plotWidth * scale + 30} y={plotLength * scale / 2 + 20} textAnchor="middle" className="fill-foreground text-xs">E</text>

          {/* Rooms */}
          {rooms.map((room) => (
            <g key={room.id}>
              <rect
                x={room.x * scale + 20}
                y={room.y * scale + 20}
                width={room.width * scale}
                height={room.height * scale}
                fill={getRoomColor(room.type)}
                fillOpacity="0.6"
                stroke="hsl(var(--foreground))"
                strokeWidth="1.5"
              />
              <text
                x={room.x * scale + room.width * scale / 2 + 20}
                y={room.y * scale + room.height * scale / 2 + 20}
                textAnchor="middle"
                className="fill-foreground text-xs font-medium"
                dominantBaseline="middle"
              >
                {room.name}
              </text>
              {room.vastuScore !== undefined && (
                <text
                  x={room.x * scale + room.width * scale / 2 + 20}
                  y={room.y * scale + room.height * scale / 2 + 30}
                  textAnchor="middle"
                  className="fill-foreground text-[10px]"
                  dominantBaseline="middle"
                >
                  Vastu: {room.vastuScore}%
                </text>
              )}
            </g>
          ))}
        </svg>
      </div>
    </Card>
  );
}
