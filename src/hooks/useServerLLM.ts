import { useState, useCallback } from 'react';

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface ServerLLMConfig {
  endpoint: string;
  model?: string;
  type?: 'ollama' | 'openai' | 'llamacpp' | 'lmstudio';
}

// Minimal tool definition compatible with Ollama's tool schema
export interface ToolDefinition {
  name: string;
  description?: string;
  parameters?: any; // JSON Schema
}

interface ToolCall {
  function: {
    name: string;
    arguments: string; // JSON string per Ollama stream format
  };
}

export function useServerLLM(config: ServerLLMConfig) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateResponse = useCallback(async (
    messages: Message[],
    onToken?: (token: string) => void,
    tools?: ToolDefinition[],
    onToolCall?: (toolCall: ToolCall, result: any) => boolean | void
  ): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
      const controller = new AbortController();
      const { signal } = controller;
      let abortedByToolSuccess = false;
      const isOllama = config.type === 'ollama' || config.endpoint.includes('11434');
      const endpoint = isOllama ? `${config.endpoint}/api/chat` : `${config.endpoint}/v1/chat/completions`;
      
      const ollamaTools = tools?.map(t => ({
        type: 'function',
        function: {
          name: t.name,
          description: t.description ?? '',
          parameters: t.parameters ?? { type: 'object', properties: {} }
        }
      }));

      const requestBody = isOllama ? {
        model: config.model || 'llama3.2',
        messages: messages.map(m => ({ role: m.role, content: m.content })),
        stream: true,
        ...(ollamaTools ? { tools: ollamaTools } : {})
      } : {
        model: config.model || 'default',
        messages: messages.map(m => ({ role: m.role, content: m.content })),
        stream: true,
        temperature: 0.7,
      };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal,
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        let readResult;
        try {
          readResult = await reader.read();
        } catch (e: any) {
          // Abort due to tool success or stream end
          if (e?.name === 'AbortError') {
            break;
          }
          throw e;
        }
        const { done, value } = readResult;
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');

        for (const line of lines) {
          if (isOllama) {
            // Ollama format: each line is a complete JSON object
            try {
              const parsed = JSON.parse(line);
              const content = parsed.message?.content;
              if (content) {
                fullResponse += content;
                if (onToken) onToken(content);
                console.log('[LLM][Token]', content.length);
              }
              // Handle tool calls if present
              const toolCalls: ToolCall[] | undefined = parsed.message?.tool_calls;
              if (toolCalls && toolCalls.length > 0) {
                console.log('[LLM][ToolCalls]', toolCalls.map(tc => tc.function?.name));
                for (const tc of toolCalls) {
                  try {
                    const argsJson = tc.function?.arguments ?? '{}';
                    const args = JSON.parse(argsJson);
                    // Execute known tools here; currently support generate_layout_hybrid
                    let result: any = { status: 'error', message: 'Unknown tool' };
                    if (tc.function?.name === 'generate_layout_hybrid') {
                      // Convert room names to room objects expected by backend
                      const roomObjects = (args.rooms_needed ?? []).map((roomName: string, index: number) => ({
                        id: `room_${index + 1}`,
                        name: roomName,
                        type: roomName.toLowerCase().replace(/[^a-z]/g, '_'),
                        width: 10, // Default dimensions - solver will optimize
                        height: 10
                      }));
                      
                      // Attempt to call backend generator with provided args
                      const payload = {
                        rooms: roomObjects,
                        plotWidth: Array.isArray(args.plot_dimensions) ? args.plot_dimensions[0] : args.plot_width ?? 30,
                        plotLength: Array.isArray(args.plot_dimensions) ? args.plot_dimensions[1] : args.plot_length ?? 30,
                        plotShape: args.plot_shape ?? 'rectangular',
                        solver_type: 'graph',
                        constraints: {
                          ...(args.orientation ? { house_facing: args.orientation } : {}),
                          ...(args.vastu_constraints ? args.vastu_constraints : {})
                        }
                      };
                      try {
                        const genRes = await fetch('http://localhost:8000/api/solvers/generate', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify(payload)
                        });
                        if (genRes.ok) {
                          const genJson = await genRes.json();
                          console.log('[Backend][Generate][Status]', genRes.status);
                          console.log('[Backend][Generate][Rooms]', (genJson.rooms || []).length);
                          result = {
                            status: 'success',
                            rooms: genJson.rooms ?? [],
                            solver: genJson.solver ?? 'graph',
                            generation_time: genJson.generation_time
                          };
                        } else {
                          console.error('[Backend][Generate][ErrorStatus]', genRes.status);
                          result = { status: 'error', message: `Backend responded ${genRes.status}` };
                        }
                      } catch (e: any) {
                        console.error('[Backend][Generate][Exception]', e?.message);
                        result = { status: 'error', message: e?.message ?? 'Backend call failed' };
                      }
                    }
                    if (onToolCall) {
                      const stop = onToolCall(tc, result);
                      if (result.status === 'success' || stop === true) {
                        abortedByToolSuccess = true;
                        try { controller.abort(); } catch {}
                        break; // break out of current tool processing
                      }
                    }
                  } catch (e) {
                    // Bad tool arguments; report via callback
                    if (onToolCall) onToolCall(tc, { status: 'error', message: 'Invalid tool arguments' });
                  }
                }
              }
              if (parsed.done) {
                try { controller.abort(); } catch {}
                break;
              }
            } catch (e) {
              // Skip invalid JSON
            }
          } else {
            // OpenAI format: SSE with data: prefix
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') continue;

              try {
                const parsed = JSON.parse(data);
                const content = parsed.choices?.[0]?.delta?.content;
                if (content) {
                  fullResponse += content;
                  if (onToken) onToken(content);
                }
              } catch (e) {
                // Skip invalid JSON
              }
            }
          }
        }
      }

      return fullResponse;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate response';
      // Treat AbortError as normal completion (tool success or stream end)
      if ((err as any)?.name === 'AbortError') {
        return '';
      }
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
