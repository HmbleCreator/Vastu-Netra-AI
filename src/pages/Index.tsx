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
- Create REALISTIC room dimensions - rooms should NOT be perfect squares unless specifically appropriate
  * Bedrooms: typically 3.5-4.5m x 4-5.5m (rectangular, not square)
  * Living rooms: 4-6m x 5-7m (rectangular, elongated)
  * Kitchen: 3-3.5m x 4-5m (rectangular)
  * Bathrooms: 2-2.5m x 2.5-3m (slightly rectangular)
  * Study: 3-3.5m x 3.5-4.5m (can be more square)
- Vary room dimensions to create a natural, livable floor plan
- Position rooms according to Vastu directions (e.g., kitchen in southeast at approximately x:20-25, y:20-25)
- Rooms should fit together logically with shared walls where appropriate
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
  const [llmConfig, setLLMConfig] = useLocalStorage<LLMConfig>('llm-config', {
    type: 'browser',
    endpoint: '',
    model: '',
  });
  
  const browserLLM = useLocalLLM();
  const serverLLM = useServerLLM({
    endpoint: llmConfig.endpoint,
    model: llmConfig.model,
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
      const floorPlanData = extractFloorPlanData(response);
      if (floorPlanData && floorPlanData.rooms.length > 0) {
        setRooms(floorPlanData.rooms);
        toast({
          title: 'Floor plan generated',
          description: `Added ${floorPlanData.rooms.length} rooms to the visualization`,
        });
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
    plotWidth: 30,
    plotLength: 30,
    plotShape: 'rectangular'
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
                  <ChatMessage key={index} message={message} />
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
          <div className="flex h-full flex-col">
        <div className="flex-1 p-6">
          <Tabs defaultValue="2d" className="h-full">
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="2d">2D View</TabsTrigger>
              <TabsTrigger value="3d">3D Walkthrough</TabsTrigger>
            </TabsList>
            <TabsContent value="2d" className="h-[calc(100%-3rem)]">
              <FloorPlanViewer rooms={rooms} plotWidth={30} plotLength={30} />
            </TabsContent>
            <TabsContent value="3d" className="h-[calc(100%-3rem)]">
              <FloorPlan3DViewer rooms={rooms} plotWidth={30} plotLength={30} />
            </TabsContent>
          </Tabs>
        </div>

        <div className="grid grid-cols-3 gap-4 border-t border-border p-6">
          <VastuScoreCard />
          <ExportPanel hasFloorPlan={rooms.length > 0} floorPlanData={floorPlanData} />
          <RoomAdjustmentPanel
            rooms={rooms}
            onUpdateRoom={handleUpdateRoom}
            onDeleteRoom={handleDeleteRoom}
            onAddRoom={handleAddRoom}
          />
        </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};

export default Index;
