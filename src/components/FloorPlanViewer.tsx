import { Card } from '@/components/ui/card';
import { Room } from '@/components/RoomAdjustmentPanel';
import { useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, Move, RotateCw, Ruler, Maximize2, Minimize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useHotkeys } from 'react-hotkeys-hook';

interface FloorPlanViewerProps {
  rooms?: Room[];
  plotWidth?: number;
  plotLength?: number;
  plotShape?: string;
  plotPolygon?: number[][];
  circle?: { center: [number, number]; radius: number };
  selectedRoomId?: string | null;
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

export function FloorPlanViewer({ rooms = [], plotWidth = 30, plotLength = 30, plotShape = 'rectangular', plotPolygon, circle, selectedRoomId = null }: FloorPlanViewerProps) {
  const [scale, setScale] = useState(15); // pixels per meter
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const [isMeasuring, setIsMeasuring] = useState(false);
  const [measurePoints, setMeasurePoints] = useState<{start?: {x: number, y: number}, end?: {x: number, y: number}}>({});
  const [showMinimap, setShowMinimap] = useState(true);

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev * 1.2, 50));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev * 0.8, 5));
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) { // Left mouse button
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      setPosition(prev => ({ x: prev.x + dx, y: prev.y + dy }));
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Keyboard shortcuts
  useHotkeys('plus', handleZoomIn, []);
  useHotkeys('minus', handleZoomOut, []);
  useHotkeys('r', () => setIsMeasuring(prev => !prev), []);
  useHotkeys('m', () => setShowMinimap(prev => !prev), []);
  useHotkeys('escape', () => {
    setIsMeasuring(false);
    setMeasurePoints({});
  }, []);
  
  // Handle measurement clicks
  const handleSvgClick = (e: React.MouseEvent) => {
    if (!isMeasuring) return;
    
    const svgRect = svgRef.current?.getBoundingClientRect();
    if (!svgRect) return;
    
    const x = (e.clientX - svgRect.left - position.x - 20) / scale;
    const y = (e.clientY - svgRect.top - position.y - 20) / scale;
    
    if (!measurePoints.start) {
      setMeasurePoints({ start: { x, y } });
    } else {
      setMeasurePoints({ ...measurePoints, end: { x, y } });
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      handleZoomIn();
    } else {
      handleZoomOut();
    }
  };

  // Calculate distance for measurement tool
  const calculateDistance = () => {
    if (measurePoints.start && measurePoints.end) {
      const dx = measurePoints.end.x - measurePoints.start.x;
      const dy = measurePoints.end.y - measurePoints.start.y;
      return Math.sqrt(dx * dx + dy * dy).toFixed(2);
    }
    return null;
  };

  useEffect(() => {
    const svg = svgRef.current;
    if (svg) {
      svg.addEventListener('wheel', handleWheel as unknown as EventListener, { passive: false });
      return () => {
        svg.removeEventListener('wheel', handleWheel as unknown as EventListener);
      };
    }
  }, []);

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

  return (
    <Card className="h-full overflow-hidden border-2 border-border relative">
      <div className="absolute top-2 right-2 z-10 flex gap-1">
        <Button variant="outline" size="icon" onClick={handleZoomIn} title="Zoom In (+ key)">
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" onClick={handleZoomOut} title="Zoom Out (- key)">
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button 
          variant="outline" 
          size="icon" 
          className={isDragging ? 'bg-primary text-primary-foreground' : ''}
          title="Pan (or drag with mouse)"
        >
          <Move className="h-4 w-4" />
        </Button>
        <Button 
          variant={isMeasuring ? "default" : "outline"} 
          size="icon" 
          onClick={() => {
            setIsMeasuring(!isMeasuring);
            if (isMeasuring) setMeasurePoints({});
          }}
          title="Measure (R key)"
        >
          <Ruler className="h-4 w-4" />
        </Button>
        <Button 
          variant={showMinimap ? "default" : "outline"} 
          size="icon" 
          onClick={() => setShowMinimap(!showMinimap)}
          title="Toggle Minimap (M key)"
        >
          {showMinimap ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </Button>
      </div>
      
      <div 
        className="h-full w-full overflow-auto p-4 bg-card"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: isDragging ? 'grabbing' : isMeasuring ? 'crosshair' : 'grab' }}
      >
        <svg
          ref={svgRef}
          width={plotWidth * scale + 40}
          height={plotLength * scale + 40}
          className="mx-auto"
          style={{ 
            border: '2px solid hsl(var(--border))',
            transform: `translate(${position.x}px, ${position.y}px)`,
            transition: isDragging ? 'none' : 'transform 0.1s ease-out'
          }}
          onClick={handleSvgClick}
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
          {plotPolygon && plotPolygon.length >= 3 ? (
            <polygon
              points={plotPolygon.map(([x, y]) => `${20 + x * scale},${20 + y * scale}`).join(' ')}
              fill="none"
              stroke="hsl(var(--border))"
              strokeWidth="2"
            />
          ) : circle ? (
            <circle
              cx={20 + circle.center[0] * scale}
              cy={20 + circle.center[1] * scale}
              r={circle.radius * scale}
              fill="none"
              stroke="hsl(var(--border))"
              strokeWidth="2"
            />
          ) : plotShape?.toLowerCase() === 'triangular' ? (
            <polygon
              points={`${20},${20} ${20 + plotWidth * scale},${20} ${20},${20 + plotLength * scale}`}
              fill="none"
              stroke="hsl(var(--border))"
              strokeWidth="2"
            />
          ) : (
            <rect
              x="20"
              y="20"
              width={plotWidth * scale}
              height={plotLength * scale}
              fill="none"
              stroke="hsl(var(--border))"
              strokeWidth="2"
            />
          )}

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
                stroke={selectedRoomId === room.id ? "hsl(var(--primary))" : "hsl(var(--foreground))"}
                strokeWidth={selectedRoomId === room.id ? "3" : "1.5"}
                strokeDasharray={selectedRoomId === room.id ? "5,5" : ""}
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

          {/* Measurement Tool */}
          {isMeasuring && measurePoints.start && (
            <>
              <circle 
                cx={measurePoints.start.x * scale + 20} 
                cy={measurePoints.start.y * scale + 20} 
                r="4" 
                fill="hsl(var(--primary))" 
              />
              {measurePoints.end && (
                <>
                  <line 
                    x1={measurePoints.start.x * scale + 20} 
                    y1={measurePoints.start.y * scale + 20}
                    x2={measurePoints.end.x * scale + 20} 
                    y2={measurePoints.end.y * scale + 20}
                    stroke="hsl(var(--primary))"
                    strokeWidth="2"
                    strokeDasharray="5,5"
                  />
                  <circle 
                    cx={measurePoints.end.x * scale + 20} 
                    cy={measurePoints.end.y * scale + 20} 
                    r="4" 
                    fill="hsl(var(--primary))" 
                  />
                  <text
                    x={(measurePoints.start.x + measurePoints.end.x) * scale / 2 + 20}
                    y={(measurePoints.start.y + measurePoints.end.y) * scale / 2 + 20 - 10}
                    textAnchor="middle"
                    className="fill-primary text-xs font-bold"
                    dominantBaseline="middle"
                    stroke="white"
                    strokeWidth="2"
                    paintOrder="stroke"
                  >
                    {calculateDistance()} m
                  </text>
                </>
              )}
            </>
          )}
        </svg>
      </div>

      {/* Mini-map */}
      {showMinimap && (
        <div className="absolute bottom-4 right-4 z-10 bg-background border border-border rounded-md shadow-md overflow-hidden">
          <svg
            width={150}
            height={150}
            viewBox={`0 0 ${plotWidth * scale + 40} ${plotLength * scale + 40}`}
            className="opacity-90"
          >
            {/* Plot boundary */}
            {plotPolygon && plotPolygon.length >= 3 ? (
              <polygon
                points={plotPolygon.map(([x, y]) => `${20 + x * scale},${20 + y * scale}`).join(' ')}
                fill="hsl(var(--background))"
                stroke="hsl(var(--border))"
                strokeWidth="2"
              />
            ) : circle ? (
              <circle
                cx={20 + circle.center[0] * scale}
                cy={20 + circle.center[1] * scale}
                r={circle.radius * scale}
                fill="hsl(var(--background))"
                stroke="hsl(var(--border))"
                strokeWidth="2"
              />
            ) : plotShape?.toLowerCase() === 'triangular' ? (
              <polygon
                points={`${20},${20} ${20 + plotWidth * scale},${20} ${20} ${20},${20 + plotLength * scale}`}
                fill="hsl(var(--background))"
                stroke="hsl(var(--border))"
                strokeWidth="2"
              />
            ) : (
              <rect
                x="20"
                y="20"
                width={plotWidth * scale}
                height={plotLength * scale}
                fill="hsl(var(--background))"
                stroke="hsl(var(--border))"
                strokeWidth="2"
              />
            )}

            {/* Rooms */}
            {rooms.map((room) => (
              <rect
                key={room.id}
                x={room.x * scale + 20}
                y={room.y * scale + 20}
                width={room.width * scale}
                height={room.height * scale}
                fill={getRoomColor(room.type)}
                fillOpacity="0.6"
                stroke="hsl(var(--foreground))"
                strokeWidth="1"
              />
            ))}

            {/* Viewport indicator */}
            <rect
              x={20 - position.x / (scale / 15)}
              y={20 - position.y / (scale / 15)}
              width={Math.min(plotWidth * scale, window.innerWidth / (scale / 15))}
              height={Math.min(plotLength * scale, window.innerHeight / (scale / 15))}
              fill="none"
              stroke="hsl(var(--primary))"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
          </svg>
        </div>
      )}
    </Card>
  );
}
