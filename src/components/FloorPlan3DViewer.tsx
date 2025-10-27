import { useRef, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, PerspectiveCamera, GizmoHelper, GizmoViewport } from '@react-three/drei';
import { Card } from '@/components/ui/card';
import * as THREE from 'three';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, RotateCw, MoveHorizontal, ArrowUp, ArrowDown, RefreshCw, Ruler } from 'lucide-react';
import { useHotkeys } from 'react-hotkeys-hook';

interface Room {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  wall_height?: number;
  color?: string;
}

interface FloorPlan3DViewerProps {
  rooms?: Room[];
  plotWidth?: number;
  plotLength?: number;
  selectedRoomId?: string | null;
}

function Room3D({ room, isSelected }: { room: Room, isSelected?: boolean }) {
  const wallHeight = room.wall_height || 3;
  const color = room.color || '#e0e0e0';
  const wallColor = isSelected ? "#4169E1" : "#ffffff";
  const outlineWidth = isSelected ? 0.1 : 0;

  return (
    <group position={[room.x + room.width / 2, 0, room.y + room.height / 2]}>
      {/* Floor */}
      <mesh position={[0, 0, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[room.width, room.height]} />
        <meshStandardMaterial color={isSelected ? "#a8c7ff" : color} />
      </mesh>

      {/* Walls - North */}
      <mesh position={[0, wallHeight / 2, -room.height / 2]}>
        <boxGeometry args={[room.width, wallHeight, 0.2]} />
        <meshStandardMaterial color={wallColor} />
      </mesh>

      {/* Walls - South */}
      <mesh position={[0, wallHeight / 2, room.height / 2]}>
        <boxGeometry args={[room.width, wallHeight, 0.2]} />
        <meshStandardMaterial color={wallColor} />
      </mesh>

      {/* Walls - East */}
      <mesh position={[room.width / 2, wallHeight / 2, 0]}>
        <boxGeometry args={[0.2, wallHeight, room.height]} />
        <meshStandardMaterial color={wallColor} />
      </mesh>

      {/* Walls - West */}
      <mesh position={[-room.width / 2, wallHeight / 2, 0]}>
        <boxGeometry args={[0.2, wallHeight, room.height]} />
        <meshStandardMaterial color={wallColor} />
      </mesh>

      {/* Room label (floating text placeholder) */}
      <mesh position={[0, wallHeight + 0.5, 0]}>
        <boxGeometry args={[0.1, 0.1, 0.1]} />
        <meshStandardMaterial color="#4169E1" />
      </mesh>
    </group>
  );
}

function CameraControls({ controlsRef }: { controlsRef: React.RefObject<any> }) {
  const { camera } = useThree();
  
  const handleZoomIn = () => {
    if (controlsRef.current) {
      controlsRef.current.dollyIn(1.2);
      controlsRef.current.update();
    }
  };

  const handleZoomOut = () => {
    if (controlsRef.current) {
      controlsRef.current.dollyOut(1.2);
      controlsRef.current.update();
    }
  };

  const handleRotateLeft = () => {
    if (controlsRef.current) {
      controlsRef.current.rotateLeft(Math.PI / 8);
      controlsRef.current.update();
    }
  };

  const handleRotateRight = () => {
    if (controlsRef.current) {
      controlsRef.current.rotateRight(Math.PI / 8);
      controlsRef.current.update();
    }
  };

  const handleMoveUp = () => {
    if (controlsRef.current) {
      camera.position.y += 2;
      controlsRef.current.update();
    }
  };

  const handleMoveDown = () => {
    if (controlsRef.current) {
      camera.position.y = Math.max(1, camera.position.y - 2);
      controlsRef.current.update();
    }
  };

  const handleReset = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };

  return null;
}

export function FloorPlan3DViewer({ rooms = [], plotWidth = 30, plotLength = 30, selectedRoomId = null }: FloorPlan3DViewerProps) {
  const controlsRef = useRef<any>(null);
  const [showControls, setShowControls] = useState(true);
  const [isMeasuring, setIsMeasuring] = useState(false);
  const [measurePoints, setMeasurePoints] = useState<{start?: THREE.Vector3, end?: THREE.Vector3}>({});

  // Keyboard shortcuts
  useHotkeys('plus', () => {
    if (controlsRef.current) {
      controlsRef.current.dollyIn(1.2);
      controlsRef.current.update();
    }
  }, []);
  
  useHotkeys('minus', () => {
    if (controlsRef.current) {
      controlsRef.current.dollyOut(1.2);
      controlsRef.current.update();
    }
  }, []);
  
  useHotkeys('r', () => {
    if (controlsRef.current) {
      controlsRef.current.rotateLeft(Math.PI / 8);
      controlsRef.current.update();
    }
  }, []);
  
  useHotkeys('shift+r', () => {
    if (controlsRef.current) {
      controlsRef.current.rotateRight(Math.PI / 8);
      controlsRef.current.update();
    }
  }, []);
  
  useHotkeys('space', () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  }, []);

  if (!rooms || rooms.length === 0) {
    return (
      <Card className="flex h-full items-center justify-center border-2 border-dashed border-border">
        <div className="text-center text-muted-foreground">
          <p className="text-lg font-medium">No 3D model yet</p>
          <p className="text-sm">Generate a floor plan to see 3D walkthrough</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="h-full overflow-hidden border-2 border-border relative">
      {/* 3D Controls */}
      <div className="absolute top-2 right-2 z-10 flex flex-col gap-2">
        <div className="flex gap-1">
          <Button variant="outline" size="icon" onClick={() => setShowControls(!showControls)} title="Toggle Controls">
            <RotateCw className="h-4 w-4" />
          </Button>
        </div>
        
        {showControls && (
          <>
            <div className="flex gap-1">
              <Button 
                variant="outline" 
                size="icon" 
                onClick={() => {
                  const controls = controlsRef.current;
                  if (controls) {
                    controls.dollyIn(1.2);
                    controls.update();
                  }
                }}
                title="Zoom In"
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button 
                variant="outline" 
                size="icon" 
                onClick={() => {
                  const controls = controlsRef.current;
                  if (controls) {
                    controls.dollyOut(1.2);
                    controls.update();
                  }
                }}
                title="Zoom Out"
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="flex gap-1">
              <Button 
                variant="outline" 
                size="icon" 
                onClick={() => {
                  const controls = controlsRef.current;
                  if (controls) {
                    controls.rotateLeft(Math.PI / 8);
                    controls.update();
                  }
                }}
                title="Rotate Left"
              >
                <RotateCw className="h-4 w-4 transform -scale-x-100" />
              </Button>
              <Button 
                variant="outline" 
                size="icon" 
                onClick={() => {
                  const controls = controlsRef.current;
                  if (controls) {
                    controls.rotateRight(Math.PI / 8);
                    controls.update();
                  }
                }}
                title="Rotate Right"
              >
                <RotateCw className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="flex gap-1">
              <Button 
                variant="outline" 
                size="icon" 
                onClick={() => {
                  const controls = controlsRef.current;
                  if (controls) {
                    controls.reset();
                  }
                }}
                title="Reset View"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </>
        )}
      </div>
      
      <Canvas shadows className="h-full bg-gradient-to-b from-sky-200 to-sky-50">
        <PerspectiveCamera makeDefault position={[plotWidth * 0.8, plotWidth * 0.6, plotLength * 0.8]} />
        
        {/* Lighting */}
        <ambientLight intensity={0.5} />
        <directionalLight
          position={[10, 20, 10]}
          intensity={1}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
        />
        <pointLight position={[-10, 10, -10]} intensity={0.5} />

        {/* Ground plane */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
          <planeGeometry args={[plotWidth * 2, plotLength * 2]} />
          <meshStandardMaterial color="#90EE90" />
        </mesh>

        {/* Grid */}
        <Grid
          args={[plotWidth * 2, plotLength * 2]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#6e6e6e"
          sectionSize={5}
          sectionThickness={1}
          sectionColor="#4169E1"
          fadeDistance={plotWidth * 3}
          fadeStrength={1}
          followCamera={false}
          position={[0, 0.01, 0]}
        />

        {/* Render rooms */}
        {rooms.map((room) => (
          <Room3D key={room.id} room={room} isSelected={selectedRoomId === room.id} />
        ))}

        {/* Controls */}
        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.05}
          minDistance={5}
          maxDistance={plotWidth * 2}
          maxPolarAngle={Math.PI / 2 - 0.1}
        />
        
        {/* XYZ Axis Helper */}
        <GizmoHelper
          alignment="bottom-right"
          margin={[80, 80]}
        >
          <GizmoViewport axisColors={['red', 'green', 'blue']} labelColor="black" />
        </GizmoHelper>
        
        <CameraControls controlsRef={controlsRef} />
      </Canvas>
    </Card>
  );
}
