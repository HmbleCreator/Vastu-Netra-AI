import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { FloorPlanViewer } from '@/components/FloorPlanViewer';
import { VastuScoreCard } from '@/components/VastuScoreCard';
import { ExportPanel } from '@/components/ExportPanel';
import { LLMSettings, LLMConfig } from '@/components/LLMSettings';
import { useLocalLLM, Message } from '@/hooks/useLocalLLM';
import { useServerLLM } from '@/hooks/useServerLLM';
import { useLocalStorage } from '@/hooks/useLocalStorage';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Trash2 } from 'lucide-react';

const SYSTEM_PROMPT = `You are a Vastu-aware architecture AI assistant. Help users design floor plans that comply with Vastu Shastra principles. Provide guidance on room placement, entrance directions, and spatial arrangements. Keep responses concise and practical.`;

const Index = () => {
  const [messages, setMessages] = useLocalStorage<Message[]>('vastu-chat-messages', []);
  const [currentResponse, setCurrentResponse] = useState('');
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
  }, [messages, currentResponse]);

  const handleSend = async (content: string) => {
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    setMessages([...messages, userMessage]);

    try {
      const response = await generateResponse(
        [
          { role: 'system', content: SYSTEM_PROMPT, timestamp: Date.now() },
          ...messages,
          userMessage,
        ],
        setCurrentResponse
      );

      const assistantMessage: Message = {
        role: 'assistant',
        content: response,
        timestamp: Date.now(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setCurrentResponse('');
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
    setMessages([]);
    setCurrentResponse('');
    toast({
      title: 'Chat cleared',
      description: 'All messages have been removed',
    });
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
      {/* Chat Panel */}
      <div className="flex w-1/2 flex-col border-r border-border">
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
              {messages.length > 0 && (
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
                {messages.length === 0 && (
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

                {messages.map((message, index) => (
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

      {/* Visualization Panel */}
      <div className="flex w-1/2 flex-col">
        <div className="flex-1 p-6">
          <FloorPlanViewer />
        </div>

        <div className="grid grid-cols-2 gap-4 border-t border-border p-6">
          <VastuScoreCard />
          <ExportPanel hasFloorPlan={false} />
        </div>
      </div>
    </div>
  );
};

export default Index;
