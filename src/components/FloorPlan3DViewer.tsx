import { useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, PerspectiveCamera } from '@react-three/drei';
import { Card } from '@/components/ui/card';
import * as THREE from 'three';

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
}

function Room3D({ room }: { room: Room }) {
  const wallHeight = room.wall_height || 3;
  const color = room.color || '#e0e0e0';

  return (
    <group position={[room.x + room.width / 2, 0, room.y + room.height / 2]}>
      {/* Floor */}
      <mesh position={[0, 0, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[room.width, room.height]} />
        <meshStandardMaterial color={color} />
      </mesh>

      {/* Walls - North */}
      <mesh position={[0, wallHeight / 2, -room.height / 2]}>
        <boxGeometry args={[room.width, wallHeight, 0.2]} />
        <meshStandardMaterial color="#ffffff" />
      </mesh>

      {/* Walls - South */}
      <mesh position={[0, wallHeight / 2, room.height / 2]}>
        <boxGeometry args={[room.width, wallHeight, 0.2]} />
        <meshStandardMaterial color="#ffffff" />
      </mesh>

      {/* Walls - East */}
      <mesh position={[room.width / 2, wallHeight / 2, 0]}>
        <boxGeometry args={[0.2, wallHeight, room.height]} />
        <meshStandardMaterial color="#ffffff" />
      </mesh>

      {/* Walls - West */}
      <mesh position={[-room.width / 2, wallHeight / 2, 0]}>
        <boxGeometry args={[0.2, wallHeight, room.height]} />
        <meshStandardMaterial color="#ffffff" />
      </mesh>

      {/* Room label (floating text placeholder) */}
      <mesh position={[0, wallHeight + 0.5, 0]}>
        <boxGeometry args={[0.1, 0.1, 0.1]} />
        <meshStandardMaterial color="#4169E1" />
      </mesh>
    </group>
  );
}

export function FloorPlan3DViewer({ rooms, plotWidth = 30, plotLength = 30 }: FloorPlan3DViewerProps) {
  const controlsRef = useRef<any>(null);

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
    <Card className="h-full overflow-hidden border-2 border-border">
      <Canvas shadows className="bg-gradient-to-b from-sky-200 to-sky-50">
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
          <Room3D key={room.id} room={room} />
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
      </Canvas>
    </Card>
  );
}
