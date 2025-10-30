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

const SYSTEM_PROMPT = `You are a Vastu-aware architecture AI assistant specializing in Indian residential design. Help users design floor plans that balance modern functionality with traditional Vastu Shastra principles.

${getVastuContextPrompt()}

**Your Capabilities:**
1. Understand user requirements for residential layouts (BHK configurations, plot size, orientation)
2. Apply Vastu principles to room placement and design
3. Use the generate_layout_hybrid tool to create floor plans
4. Explain Vastu compliance and design choices
5. Modify layouts based on user feedback

**Key Vastu Principles:**
- Kitchen: Southeast (Agni corner) or Northwest
- Master Bedroom: Southwest (stability)
- Living Room: North, East, or Northeast
- Entrance: North, East, or Northeast (most auspicious)
- Bathroom: Northwest, West, or South (never Northeast)
- Pooja Room: Northeast (most auspicious)

**When to Use generate_layout_hybrid Tool:**
- User requests a new floor plan design
- User asks to modify plot orientation or room placement
- User wants to change BHK configuration
- User requests Vastu-compliant layouts

**Tool Usage Instructions:**
1. Extract requirements from user query:
   - Number of rooms (e.g., "3BHK" = kitchen, living, 3 bedrooms, 2 bathrooms)
   - Plot dimensions (estimate ~35-45m for 3BHK if not specified)
   - Orientation (default: "east" if not specified)
   - Vastu constraints from user preferences
   - Total area (estimate: 2BHK=120-150m², 3BHK=150-200m², 4BHK=200-250m²)

2. Call generate_layout_hybrid with proper parameters
3. After layout is generated, explain the design and Vastu compliance
4. DO NOT output JSON in chat - the layout will be visualized automatically

**Example Interaction:**
User: "Design a 3BHK house with east facing entrance"
You: *Call generate_layout_hybrid tool*
Then respond: "I've designed your 3BHK layout with an east-facing entrance (very auspicious in Vastu). The kitchen is positioned in the southeast (Agni corner), master bedroom in southwest for stability, and living room in the northeast for positive energy flow. The layout has a Vastu compliance score of 92%. Would you like me to adjust anything?"

**Important:**
- Always use the tool for layout generation, never output raw JSON
- Explain Vastu principles in simple, user-friendly language
- Be ready to modify layouts based on user feedback
- Provide Vastu scores and explain compliance`;

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
      // Define tools for the LLM (only for server-based LLMs)
      const tools = llmConfig.type !== 'browser' ? [
        {
          name: 'generate_layout_hybrid',
          description: 'Generate a floor plan layout using hybrid solver (fast graph-based + reliable constraint-based with fallback). Use this tool whenever the user requests a floor plan design or modifications to room placement.',
          parameters: {
            type: 'object',
            properties: {
              rooms_needed: {
                type: 'array',
                items: { type: 'string' },
                description: 'List of room names needed (e.g., ["kitchen", "living_room", "master_bedroom", "bedroom_2", "bathroom_1", "bathroom_2"])',
              },
              plot_dimensions: {
                type: 'array',
                items: { type: 'number' },
                description: 'Plot dimensions in meters as [width, height]. Typical: [35, 40] for 3BHK',
              },
              orientation: {
                type: 'string',
                enum: ['north', 'south', 'east', 'west'],
                description: 'Main entrance orientation',
              },
              vastu_constraints: {
                type: 'object',
                description: 'Vastu constraints to enforce (e.g., {"kitchen_southeast": true, "master_bedroom_southwest": true})',
              },
              total_area: {
                type: 'number',
                description: 'Total building area in square meters (e.g., 150 for 3BHK)',
              },
            },
            required: ['rooms_needed', 'plot_dimensions', 'orientation'],
          },
        },
      ] : undefined;

      const startTime = performance.now();
      console.log('[HandleSend][Start]', { timestamp: Date.now(), llmConfig });
      let toolCallHandled = false;
      // Watchdog fallback: if no tool call or response after 10s, try direct generation from prompt
      const watchdog = setTimeout(async () => {
        if (toolCallHandled) return;
        try {
          console.warn('[Watchdog] No tool call detected, triggering fallback generation');
          // Heuristic extraction from prompt
          const bhkMatch = content.match(/(\d)\s*bhk/i);
          const bhk = bhkMatch ? Number(bhkMatch[1]) : 2;
          const areaMatch = content.match(/(\d+\.?\d*)\s*(sq\s*ft|ft\^2)/i);
          const widthMatch = content.match(/(\d+\.?\d*)\s*ft\s*width/i);
          const area = areaMatch ? Number(areaMatch[1]) : (plotWidth * plotLength);
          const width = widthMatch ? Number(widthMatch[1]) : plotWidth;
          const length = Math.max(10, Math.round((area / width) * 100) / 100);
          const facingMatch = /west\s*facing/i.test(content) ? 'west' : /east\s*facing/i.test(content) ? 'east' : undefined;
          // Build minimal rooms from BHK
          const baseRooms: Room[] = [];
          baseRooms.push({ id: 'living', name: 'Living Room', type: 'living', width: 10, height: 10, x: 0, y: 0 });
          baseRooms.push({ id: 'kitchen', name: 'Kitchen', type: 'kitchen', width: 8, height: 8, x: 0, y: 0 });
          const bathrooms = Math.max(1, Math.round(bhk / 2));
          for (let i = 1; i <= bhk; i++) {
            baseRooms.push({ id: `bed_${i}`, name: `Bedroom ${i}`, type: i === 1 ? 'master_bedroom' : 'bedroom', width: 12, height: 10, x: 0, y: 0 });
          }
          for (let i = 1; i <= bathrooms; i++) {
            baseRooms.push({ id: `bath_${i}`, name: `Bathroom ${i}`, type: 'bathroom', width: 6, height: 6, x: 0, y: 0 });
          }
          const payload = {
            rooms: baseRooms,
            plotWidth: width,
            plotLength: length,
            plotShape: 'rectangular',
            solver_type: 'graph',
            constraints: {
              ...(facingMatch ? { house_facing: facingMatch } : {})
            }
          };
          console.log('[Watchdog][GenerateAPI][Request]', payload);
          let genRes = await fetch('http://localhost:8000/api/solvers/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (!genRes.ok) {
            console.warn('[Watchdog] Graph solver failed, retrying with constraint');
            genRes = await fetch('http://localhost:8000/api/solvers/generate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ...payload, solver_type: 'constraint' })
            });
          }
          const genJson = await genRes.json();
          console.log('[Watchdog][GenerateAPI][ResponseStatus]', genRes.status);
          console.log('[Watchdog][GenerateAPI][ResponseBody]', genJson);
          if (genRes.ok && genJson.rooms) {
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
            toast({
              title: 'Fallback floor plan generated',
              description: `Generated ${positionedRooms.length} rooms for ${width}×${length} plot`,
            });
          } else {
            console.error('[Watchdog] Fallback generation failed');
            toast({ title: 'Generation failed', description: 'Fallback generation failed', variant: 'destructive' });
          }
        } catch (e) {
          console.error('[Watchdog] Exception', e);
        }
      }, 10000);
      const response = await generateResponse(
        [
          { role: 'system', content: SYSTEM_PROMPT, timestamp: Date.now() },
          ...activeSession.messages,
          userMessage,
        ],
        setCurrentResponse,
        tools,
        (toolCall, result) => {
          // Handle tool call results
          console.log('[ToolCall]', toolCall.function.name, result);
          
          if (toolCall.function.name === 'generate_layout_hybrid' && result.status === 'success') {
            setRooms(result.rooms);
            toast({
              title: "Floor Plan Generated",
              description: `Generated ${result.rooms.length} rooms using ${result.solver} solver (${result.generation_time?.toFixed(1)}s)`,
            });
            toolCallHandled = true;
            clearTimeout(watchdog);
          } else if (toolCall.function.name === 'generate_layout_hybrid' && result.status !== 'success') {
            console.error('[ToolCall][Error] generate_layout_hybrid failed:', result);
            toast({
              title: 'Generation failed',
              description: typeof result.message === 'string' ? result.message : 'Unknown error during layout generation',
              variant: 'destructive',
            });
            toolCallHandled = true;
            clearTimeout(watchdog);
          }
        }
      );
      const endTime = performance.now();
      console.log('LLM response time (ms):', Math.round(endTime - startTime));
      console.log('LLM response length:', response?.length ?? 0);
      clearTimeout(watchdog);

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
          const payload = {
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
          };
          console.log('[GenerateAPI][Request]', payload);
          const genRes = await fetch('http://localhost:8000/api/solvers/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });

          if (!genRes.ok) throw new Error(`Generate API failed: ${genRes.status}`);
          const genJson = await genRes.json();
          console.log('[GenerateAPI][ResponseStatus]', genRes.status);
          console.log('[GenerateAPI][ResponseBody]', genJson);

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
