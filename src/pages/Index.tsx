import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { FloorPlanViewer } from '@/components/FloorPlanViewer';
import { FloorPlan3DViewer } from '@/components/FloorPlan3DViewer';
import { VastuScoreCard } from '@/components/VastuScoreCard';
import { ExportPanel } from '@/components/ExportPanel';
import { RoomAdjustmentPanel, Room } from '@/components/RoomAdjustmentPanel';
import { LLMSettings, LLMConfig } from '@/components/LLMSettings';
import { SessionSidebar } from '@/components/SessionSidebar';
import { useLocalLLM, Message } from '@/hooks/useLocalLLM';
import { useServerLLM } from '@/hooks/useServerLLM';
import { useLocalStorage } from '@/hooks/useLocalStorage';
import { useChatSessions } from '@/hooks/useChatSessions';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Trash2 } from 'lucide-react';
import { getVastuContextPrompt } from '@/data/vastuRules';
import { FloorPlanData } from '@/utils/exportUtils';
import { extractFloorPlanData } from '@/utils/parseFloorPlan';

const SYSTEM_PROMPT = `You are a Vastu-aware architecture AI assistant specialized in Indian architectural design.

${getVastuContextPrompt()}

Help users design floor plans that comply with Vastu Shastra principles. Provide guidance on:
- Room placement and orientation
- Entrance directions and positioning
- Spatial arrangements and dimensions
- Irregular plot shapes (L-shaped, T-shaped, etc.)
- Landscape zones (gardens, lawns, parking)

CRITICAL: When users request floor plan designs, you MUST output structured JSON data in addition to your explanation.

**Output Format:**
1. First, provide a brief explanation of the design and Vastu principles applied
2. Then, output a JSON code block with room data in this EXACT format:

\`\`\`json
{
  "rooms": [
    {
      "id": "unique-id",
      "name": "Room Name",
      "type": "bedroom|kitchen|bathroom|living|dining|study|entrance|other",
      "direction": "north|south|east|west|northeast|northwest|southeast|southwest",
      "x": 0,
      "y": 0,
      "width": 10,
      "height": 10,
      "vastuScore": 85
    }
  ],
  "plotWidth": 30,
  "plotLength": 30,
  "plotShape": "rectangular|square|L-shaped|T-shaped|irregular"
}
\`\`\`

**Room Placement Guidelines:**
- Use a coordinate system where (0,0) is the top-left corner
- Standard plot size: 30x30 meters (adjust based on user requirements)
- Typical room dimensions: 3-5 meters for bedrooms, 4-6 meters for living rooms, 2-3 meters for bathrooms
- Position rooms according to Vastu directions (e.g., kitchen in southeast at approximately x:20-25, y:20-25)
- Calculate vastuScore (0-100) based on how well the room follows Vastu principles

**Example coordinates for 30x30 plot:**
- Northeast (0-10, 0-10) - Pooja room, entrance
- Southeast (20-30, 20-30) - Kitchen
- Southwest (20-30, 0-10) - Master bedroom
- Northwest (0-10, 20-30) - Guest room/bathroom
- Center - Living room

Keep responses concise but thorough. Always reference specific Vastu rules by their ID (e.g., V001, V004).`;

const Index = () => {
  const {
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    createSession,
    deleteSession,
    addMessage,
    clearSessionMessages,
  } = useChatSessions();
  
  const [currentResponse, setCurrentResponse] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useLocalStorage('sidebar-collapsed', false);
  const [rooms, setRooms] = useLocalStorage<Room[]>('vastu-rooms', []);
  const [plotWidth, setPlotWidth] = useLocalStorage<number>('vastu-plot-width', 30);
  const [plotLength, setPlotLength] = useLocalStorage<number>('vastu-plot-length', 30);
  const [plotShape, setPlotShape] = useLocalStorage<string>('vastu-plot-shape', 'rectangular');
  const [plotPolygon, setPlotPolygon] = useLocalStorage<number[][] | undefined>('vastu-plot-polygon', undefined);
  const [plotCircle, setPlotCircle] = useLocalStorage<{ center: [number, number]; radius: number } | undefined>('vastu-plot-circle', undefined);
  const [vastuScore, setVastuScore] = useState<{ overall: number; entranceCompliance: number; roomPlacement: number; directionAlignment: number } | undefined>(undefined);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [llmConfig, setLLMConfig] = useLocalStorage<LLMConfig>('llm-config', {
    type: 'browser',
    endpoint: '',
    model: '',
  });
  
  const browserLLM = useLocalLLM();
  const serverLLM = useServerLLM({
    endpoint: llmConfig.endpoint,
    model: llmConfig.model,
    type: llmConfig.type === 'browser' ? 'ollama' : llmConfig.type,
  });
  
  const activeLLM = llmConfig.type === 'browser' ? browserLLM : serverLLM;
  const { generateResponse, initializeModel, isLoading, isInitializing, error, isReady } = activeLLM;
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages, currentResponse]);

  const handleSend = async (content: string) => {
    if (!activeSession || !activeSessionId) return;

    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    // Add user message immediately to prevent state loss
    addMessage(activeSessionId, userMessage);

    try {
      const response = await generateResponse(
        [
          { role: 'system', content: SYSTEM_PROMPT, timestamp: Date.now() },
          ...activeSession.messages,
          userMessage,
        ],
        setCurrentResponse
      );

      const assistantMessage: Message = {
        role: 'assistant',
        content: response,
        timestamp: Date.now(),
      };

      // Add assistant message after response is complete
      addMessage(activeSessionId, assistantMessage);
      setCurrentResponse('');

      // Extract and apply floor plan data if present
      const parsed = extractFloorPlanData(response);
      if (parsed && parsed.rooms.length > 0) {
        // Update local plot settings from parsed data
        setPlotWidth(parsed.plotWidth ?? 30);
        setPlotLength(parsed.plotLength ?? 30);
        setPlotShape(parsed.plotShape ?? 'rectangular');
        // Optional shape constraints
        const poly = (parsed as any).plot_polygon || parsed.constraints?.plot_polygon;
        const circ = (parsed as any).circle || parsed.constraints?.circle;
        setPlotPolygon(poly);
        setPlotCircle(circ);

        // Call backend solver to position rooms and avoid overlaps
        try {
          const facingMatch = /west\s*facing/i.test(content) ? 'west' : /east\s*facing/i.test(content) ? 'east' : undefined;
          const genRes = await fetch('http://localhost:8000/api/solvers/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              rooms: parsed.rooms,
              plotWidth: parsed.plotWidth ?? 30,
              plotLength: parsed.plotLength ?? 30,
              plotShape: parsed.plotShape ?? 'rectangular',
              solver_type: 'graph',
              constraints: {
                ...(facingMatch ? { house_facing: facingMatch } : {}),
                ...(poly ? { plot_polygon: poly } : {}),
                ...(circ ? { circle: circ } : {}),
              }
            })
          });

          if (!genRes.ok) throw new Error(`Generate API failed: ${genRes.status}`);
          const genJson = await genRes.json();

          // Apply positioned rooms
          const positionedRooms: Room[] = (genJson.rooms || []).map((r: any) => ({
            id: r.id,
            name: r.name,
            type: r.type,
            x: r.x,
            y: r.y,
            width: r.width,
            height: r.height,
            color: r.color,
          }));
          setRooms(positionedRooms);

          // Validate for Vastu scores
          try {
            const valRes = await fetch('http://localhost:8000/api/validation/validate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ rooms: positionedRooms, constraints: facingMatch ? { house_facing: facingMatch } : undefined })
            });
            if (valRes.ok) {
              const valJson = await valRes.json();
              const overall = typeof valJson.vastu_score === 'number' ? Math.round(valJson.vastu_score) : undefined;
              setVastuScore(overall !== undefined ? {
                overall,
                entranceCompliance: Math.round(valJson.entrance_compliance ?? overall ?? 0),
                roomPlacement: Math.round(valJson.room_placement_score ?? overall ?? 0),
                directionAlignment: Math.round(valJson.direction_alignment_score ?? overall ?? 0),
              } : undefined);
            }
          } catch (e) {
            console.error('Validation error', e);
          }

          toast({
            title: 'Floor plan generated',
            description: `Optimized ${positionedRooms.length} rooms for ${parsed.plotWidth ?? 30}×${parsed.plotLength ?? 30} plot`,
          });
        } catch (e) {
          console.error('Generation error', e);
          // Fallback: use parsed rooms directly
          setRooms(parsed.rooms);
          toast({
            title: 'Floor plan parsed',
            description: `Added ${parsed.rooms.length} rooms (generation fallback)`,
          });
        }
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to generate response. Please try again.',
        variant: 'destructive',
      });
      console.error('Error generating response:', err);
    }
  };

  const handleClearChat = () => {
    if (!activeSessionId) return;
    clearSessionMessages(activeSessionId);
    setCurrentResponse('');
    toast({
      title: 'Chat cleared',
      description: 'All messages have been removed',
    });
  };

  const handleUpdateRoom = (roomId: string, updates: Partial<Room>) => {
    setRooms(rooms.map(room => room.id === roomId ? { ...room, ...updates } : room));
    toast({
      title: 'Room updated',
      description: 'Room properties have been modified',
    });
  };

  const handleDeleteRoom = (roomId: string) => {
    setRooms(rooms.filter(room => room.id !== roomId));
    toast({
      title: 'Room deleted',
      description: 'Room has been removed from floor plan',
    });
  };

  const handleAddRoom = (room: Room) => {
    setRooms([...rooms, room]);
    toast({
      title: 'Room added',
      description: 'New room has been added to floor plan',
    });
  };

  const floorPlanData: FloorPlanData = {
    rooms,
    plotWidth,
    plotLength,
    plotShape: plotShape as 'rectangular' | 'L-shaped' | 'T-shaped' | 'irregular'
  };

  const handleInitialize = async () => {
    try {
      await initializeModel();
      toast({
        title: 'Model ready',
        description: 'Local LLM initialized successfully',
      });
    } catch (err) {
      toast({
        title: 'Initialization failed',
        description: 'Could not load the model. Please refresh the page.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Session Sidebar */}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSessionSelect={setActiveSessionId}
        onSessionCreate={createSession}
        onSessionDelete={deleteSession}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Resizable Chat and Visualization Panels */}
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Chat Panel */}
        <ResizablePanel defaultSize={50} minSize={30}>
          <div className="flex h-full flex-col border-r border-border">
        <div className="border-b border-border bg-card px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Vastu Architect AI</h1>
              <p className="text-sm text-muted-foreground">
                {isReady ? `${llmConfig.type === 'browser' ? 'Browser' : llmConfig.type.toUpperCase()} ready` : isInitializing ? 'Loading model...' : 'Configure LLM to start'}
              </p>
            </div>
            <div className="flex gap-2">
              <LLMSettings config={llmConfig} onConfigChange={setLLMConfig} />
              {activeSession && activeSession.messages.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearChat}
                  disabled={isLoading}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Clear
                </Button>
              )}
            </div>
          </div>
        </div>

        {!isReady && !isInitializing && (
          <div className="flex flex-1 items-center justify-center p-6">
            <div className="text-center">
              <h2 className="mb-4 text-xl font-semibold">Welcome to Vastu Architect AI</h2>
              <p className="mb-6 text-muted-foreground">
                {llmConfig.type === 'browser' 
                  ? 'Initialize the browser-based AI model to start'
                  : 'Make sure your local LLM server is running and click below to start'}
              </p>
              <Button onClick={handleInitialize} size="lg">
                {llmConfig.type === 'browser' ? 'Initialize AI Model' : 'Connect to Server'}
              </Button>
              {error && (
                <p className="mt-4 text-sm text-destructive">{error}</p>
              )}
            </div>
          </div>
        )}

        {isInitializing && (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center">
              <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Loading AI model...</p>
              <p className="mt-2 text-sm text-muted-foreground">This may take a minute</p>
            </div>
          </div>
        )}

        {isReady && (
          <>
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-4">
                {activeSession && activeSession.messages.length === 0 && (
                  <div className="text-center text-muted-foreground">
                    <p className="mb-4">Start designing your Vastu-compliant floor plan</p>
                    <div className="grid gap-2">
                      <Button
                        variant="outline"
                        onClick={() => handleSend('I need a 3BHK apartment with Vastu compliance')}
                      >
                        Design a 3BHK apartment
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleSend('What are the Vastu principles for entrance placement?')}
                      >
                        Learn about entrance placement
                      </Button>
                    </div>
                  </div>
                )}

                {activeSession?.messages.map((message, index) => (
                  <ChatMessage key={`message-${index}`} message={message} />
                ))}

                {currentResponse && (
                  <ChatMessage
                    message={{
                      role: 'assistant',
                      content: currentResponse,
                      timestamp: Date.now(),
                    }}
                  />
                )}

                {isLoading && !currentResponse && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Thinking...</span>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            <div className="border-t border-border bg-card p-4">
              <ChatInput onSend={handleSend} disabled={isLoading} />
            </div>
          </>
        )}
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Visualization Panel */}
        <ResizablePanel defaultSize={50} minSize={30}>
          <ResizablePanelGroup direction="vertical" className="h-full">
            {/* Layout Area */}
            <ResizablePanel defaultSize={70} minSize={30} className="overflow-hidden">
              <div className="h-full overflow-auto p-6">
                <Tabs defaultValue="2d" className="h-full">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="2d">2D View</TabsTrigger>
                      <TabsTrigger value="3d">3D View</TabsTrigger>
                    </TabsList>
                    <TabsContent value="2d" className="h-[calc(100%-40px)]">
                      <FloorPlanViewer 
                        rooms={rooms} 
                        plotWidth={plotWidth} 
                        plotLength={plotLength} 
                        plotShape={plotShape}
                        plotPolygon={plotPolygon}
                        circle={plotCircle}
                        selectedRoomId={selectedRoomId}
                      />
                    </TabsContent>
                    <TabsContent value="3d" className="h-[calc(100%-40px)]">
                      <FloorPlan3DViewer 
                        rooms={rooms} 
                        plotWidth={plotWidth} 
                        plotLength={plotLength}
                        selectedRoomId={selectedRoomId}
                      />
                    </TabsContent>
                  </Tabs>
              </div>
            </ResizablePanel>

            <ResizableHandle withHandle />

            {/* Scores and Export Area */}
            <ResizablePanel defaultSize={30} minSize={20} className="overflow-hidden">
              <div className="h-full overflow-auto border-t border-border">
                <div className="grid grid-cols-3 gap-4 p-6">
                  <VastuScoreCard score={vastuScore} />
                  <ExportPanel hasFloorPlan={rooms.length > 0} floorPlanData={floorPlanData} />
                  <RoomAdjustmentPanel
                    rooms={rooms}
                    onUpdateRoom={handleUpdateRoom}
                    onDeleteRoom={handleDeleteRoom}
                    onAddRoom={handleAddRoom}
                    selectedRoomId={selectedRoomId}
                    onSelectRoom={setSelectedRoomId}
                  />
                </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};

export default Index;
