import { useState, useCallback } from 'react';

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface ServerLLMConfig {
  endpoint: string;
  model?: string;
}

export interface ToolCall {
  id: string;
  type: string;
  function: {
    name: string;
    arguments: string;
  };
}

export function useServerLLM(config: ServerLLMConfig) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateResponse = useCallback(async (
    messages: Message[],
    onToken?: (token: string) => void,
    tools?: Array<{name: string; description: string; parameters: any}>,
    onToolCall?: (toolCall: ToolCall, result: any) => void
  ): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
      const requestBody: any = {
        model: config.model || 'default',
        messages: messages.map(m => ({
          role: m.role,
          content: m.content
        })),
        stream: true,
        temperature: 0.7,
      };

      if (tools && tools.length > 0) {
        requestBody.tools = tools.map(tool => ({
          type: 'function',
          function: {
            name: tool.name,
            description: tool.description,
            parameters: tool.parameters,
          }
        }));
      }

      const response = await fetch(`${config.endpoint}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let fullResponse = '';
      let currentToolCalls: Map<number, ToolCall> = new Map();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              const delta = parsed.choices?.[0]?.delta;
              
              // Handle text content
              const content = delta?.content;
              if (content) {
                fullResponse += content;
                if (onToken) onToken(content);
              }

              // Handle tool calls
              if (delta?.tool_calls) {
                for (const toolCallDelta of delta.tool_calls) {
                  const index = toolCallDelta.index;
                  
                  if (!currentToolCalls.has(index)) {
                    currentToolCalls.set(index, {
                      id: toolCallDelta.id || `tool_${index}`,
                      type: 'function',
                      function: {
                        name: toolCallDelta.function?.name || '',
                        arguments: toolCallDelta.function?.arguments || '',
                      }
                    });
                  } else {
                    const existing = currentToolCalls.get(index)!;
                    if (toolCallDelta.function?.arguments) {
                      existing.function.arguments += toolCallDelta.function.arguments;
                    }
                  }
                }
              }

              // Check if tool call is complete
              const finishReason = parsed.choices?.[0]?.finish_reason;
              if (finishReason === 'tool_calls' && currentToolCalls.size > 0 && onToolCall) {
                // Execute tool calls
                for (const toolCall of currentToolCalls.values()) {
                  try {
                    const args = JSON.parse(toolCall.function.arguments);
                    
                    // Call the layout generation function
                    if (toolCall.function.name === 'generate_layout_hybrid') {
                      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
                      const toolResponse = await fetch(`${supabaseUrl}/functions/v1/generate-layout-hybrid`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(args),
                      });
                      
                      const result = await toolResponse.json();
                      onToolCall(toolCall, result);
                    }
                  } catch (e) {
                    console.error('Tool execution error:', e);
                  }
                }
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }

      return fullResponse;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate response';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [config]);

  return {
    generateResponse,
    isLoading,
    error,
    isReady: true,
    isInitializing: false,
    initializeModel: async () => {}, // No-op for server LLMs
  };
}
