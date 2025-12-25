import { useState, useCallback } from 'react';

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface ServerLLMConfig {
  endpoint: string;
  model?: string;
  type?: 'ollama' | 'openai' | 'llamacpp' | 'lmstudio' | 'browser';
}

// Minimal tool definition compatible with Ollama's tool schema
export interface ToolDefinition {
  name: string;
  description?: string;
  parameters?: any; // JSON Schema
}

interface ToolCall {
  function?: {
    name: string;
    arguments: string | Record<string, any>; // Can be JSON string or parsed object
  };
  // Some models use flat structure instead of nested 'function' object
  name?: string;
  arguments?: string | Record<string, any>;
}

export function useServerLLM(config: ServerLLMConfig) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Helper to wrap thinking/reasoning patterns in collapsible container
  const cleanThinkingContent = (text: string): string => {
    if (!text) return '';

    let mainContent = text;
    let thinkingContent = '';

    // Extract content between <think> tags
    const thinkMatch = text.match(/<think>([\s\S]*?)<\/think>/i);
    if (thinkMatch) {
      thinkingContent = thinkMatch[1].trim();
      mainContent = text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
    }

    // Check if the content looks like thinking/reasoning (starts with thinking patterns)
    const thinkingPatterns = [
      /^(Okay,|Wait,|Hmm,|Let me think|Let me check|I need to|First,|So,|Actually,)/im,
      /^(The user|They didn't|Since they|I should|I have to|I'll|Maybe I)/im,
      /^(Looking at|Checking|Analyzing|Processing|Thinking about)/im,
    ];

    const looksLikeThinking = thinkingPatterns.some(p => p.test(mainContent));

    // If main content looks like thinking, move it to thinking section
    if (looksLikeThinking && !thinkingContent) {
      thinkingContent = mainContent;
      mainContent = '';
    }

    // Build final response
    let result = '';

    if (thinkingContent) {
      // Wrap thinking in a collapsible details element
      result += `<details class="thinking-container">\n<summary>💭 View AI Reasoning</summary>\n\n${thinkingContent}\n\n</details>\n\n`;
    }

    if (mainContent) {
      result += mainContent;
    }

    // If nothing useful, provide a fallback
    if (!result.trim()) {
      result = "I've processed your request. The floor plan has been generated and is displayed in the viewer.";
    }

    return result.trim();
  };

  const generateResponse = useCallback(async (
    messages: Message[],
    onToken?: (token: string) => void,
    tools?: ToolDefinition[],
    onToolCall?: (toolCall: ToolCall, result: any) => boolean | void
  ): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
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

      let fullResponse = '';
      // Maintain rolling message list for multi-round tool execution
      let rollingMessages: Array<{ role: 'user' | 'assistant' | 'system' | 'tool'; content: string; name?: string }> = messages.map(m => ({ role: m.role, content: m.content }));
      let rounds = 0;
      const maxRounds = 3; // prevent infinite tool loops
      let haveToolResults = false;
      let lastToolResult: any = null;

      console.log('[ServerLLM][Init]', {
        endpoint,
        isOllama,
        toolsCount: ollamaTools?.length ?? 0,
        initialMessages: rollingMessages.length,
      });

      while (rounds < maxRounds) {
        // For follow-up after tools, prevent further tool calls so we get a narrative
        // Add a debug switch: set localStorage 'llm_disable_tools' = 'true' to force-disable tools
        const forceDisableToolsDebug = (typeof window !== 'undefined' && localStorage.getItem('llm_disable_tools') === 'true');
        const shouldDisableToolsThisRound = haveToolResults || forceDisableToolsDebug;
        const roundIndex = rounds + 1;
        const roundStart = performance.now();
        // Use 'auto' instead of 'required' because some models (like qwen3) don't support required tool calls
        const initialToolChoice = shouldDisableToolsThisRound ? 'none' : 'auto';
        console.log('[ServerLLM][RoundStart]', {
          round: roundIndex,
          disableTools: shouldDisableToolsThisRound,
          toolChoice: initialToolChoice,
          messagesCount: rollingMessages.length,
        });
        const controller = new AbortController();
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(isOllama ? {
            model: config.model || 'gpt-oss:20b-cloud',
            messages: rollingMessages,
            stream: true,
            tools: shouldDisableToolsThisRound ? undefined : (ollamaTools && ollamaTools.length > 0 ? ollamaTools : undefined),
            tool_choice: initialToolChoice,
            options: {
              // Encourage tool calls and bounded outputs
              num_predict: 1024, // Increased for longer explanations
              temperature: 0.3, // Slightly higher for more natural responses
              // Stop sequences to prevent thinking mode output only
              stop: [
                '<think>',
                '</think>',
              ],
              repeat_penalty: 1.1,
              num_ctx: 4096,
              num_thread: 4,
              top_k: 40,
              top_p: 0.9,
            },
            // Disable thinking mode for Qwen3 and similar models
            think: false,
            // Do not constrain output format (ensure plain text)
            format: undefined,
            // Avoid global system enforcement; rely on first system message
            system: undefined,
          } : {
            model: config.model || 'default',
            messages: rollingMessages,
            stream: true,
            temperature: 0.4,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Server responded with ${response.status}`);
        }

        console.log('[ServerLLM][HTTP]', { round: roundIndex, status: response.status });

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let encounteredToolCall = false;
        let firstTokenLogged = false;
        let streamedCharsThisRound = 0;
        let streamBuffer = '';
        let stallTimer: any = null;
        const stallTimeoutMs = 30000;
        const resetStallTimer = () => {
          if (stallTimer) clearTimeout(stallTimer);
          stallTimer = setTimeout(() => {
            console.warn('[ServerLLM][StallTimeout]', { round: roundIndex, ms: stallTimeoutMs });
            try { controller.abort(); } catch { }
          }, stallTimeoutMs);
        };
        resetStallTimer();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          resetStallTimer();
          const chunk = decoder.decode(value);
          if (!firstTokenLogged) {
            console.log('[ServerLLM][Chunk]', { round: roundIndex, bytes: value?.length ?? 0 });
          }
          streamBuffer += chunk;
          const segments = streamBuffer.split(/\r?\n/);
          // keep the last incomplete segment in buffer
          streamBuffer = segments.pop() || '';
          for (const line of segments) {
            if (isOllama) {
              try {
                const parsed = JSON.parse(line);
                // Debug visibility into chunk structure
                console.log('[ServerLLM][ParsedChunk]', {
                  round: roundIndex,
                  hasMessage: !!parsed.message,
                  messageKeys: parsed.message ? Object.keys(parsed.message) : [],
                  contentPreview: (parsed.message?.content || parsed.message?.thinking || parsed.content || parsed.response || parsed.thinking || parsed.text || '').toString().slice(0, 200),
                  fullParsed: JSON.stringify(parsed).substring(0, 200)
                });
                if (!firstTokenLogged) {
                  console.log('[ServerLLM][FirstParsedLine]', {
                    round: roundIndex,
                    keys: Object.keys(parsed),
                    hasMessage: !!parsed.message,
                    messageKeys: parsed.message ? Object.keys(parsed.message) : [],
                    done: parsed.done,
                    sample: JSON.stringify(parsed).substring(0, 300)
                  });
                }

                // Only use message.content - DO NOT include thinking fields
                // Qwen3 and other thinking models output reasoning in 'thinking' field which should be hidden
                const content: string = parsed.message?.content
                  || parsed.response
                  || parsed.content
                  || parsed.text
                  || '';

                if (content) {
                  fullResponse += content;
                  if (onToken) onToken(content);
                  streamedCharsThisRound += content.length;
                  if (!firstTokenLogged) {
                    console.log('[ServerLLM][TokenStart]', {
                      round: roundIndex,
                      firstChars: content.substring(0, 50),
                      contentLength: content.length,
                      source: parsed.message?.thinking ? 'thinking' : (parsed.message?.content ? 'content' : (parsed.thinking ? 'thinking(root)' : 'other'))
                    });
                    firstTokenLogged = true;
                  }
                }
                // If parsed but no content, log keys to understand format
                if (!content && Object.keys(parsed).length > 0) {
                  console.log('[ServerLLM][EmptyContent]', {
                    round: roundIndex,
                    keys: Object.keys(parsed),
                    sample: JSON.stringify(parsed).substring(0, 150)
                  });
                }
                const toolCalls = parsed.message?.tool_calls || parsed.tool_calls;
                if (Array.isArray(toolCalls) && toolCalls.length > 0) {
                  encounteredToolCall = true;
                  console.log('[ServerLLM][ToolCallsDetected]', { round: roundIndex, count: toolCalls.length });
                  for (const toolCall of toolCalls as ToolCall[]) {
                    try {
                      // Handle both string and object arguments (different models return different formats)
                      let args: Record<string, any>;
                      const rawArgs = toolCall.function?.arguments ?? toolCall.arguments ?? '{}';
                      if (typeof rawArgs === 'string') {
                        args = JSON.parse(rawArgs);
                      } else if (typeof rawArgs === 'object') {
                        args = rawArgs;
                      } else {
                        args = {};
                      }
                      let result: any = { status: 'error', message: 'No handler' };
                      console.log('[ServerLLM][ToolCall]', {
                        round: roundIndex,
                        name: toolCall.function?.name || toolCall.name,
                        argsKeys: Object.keys(args),
                        rawArgsType: typeof rawArgs
                      });

                      if (toolCall.function.name === 'generate_layout_hybrid') {
                        const dims: number[] = Array.isArray(args.plot_dimensions) ? args.plot_dimensions : [30, 30];
                        const width = Number(dims[0]) || 30;
                        const length = Number(dims[1]) || 30;
                        const orientation: string | undefined = typeof args.orientation === 'string' ? args.orientation : undefined;
                        const roomsNeeded: string[] = Array.isArray(args.rooms_needed) ? args.rooms_needed : [];

                        const defaults: Record<string, { w: number; h: number; type: string; name: string }> = {
                          living_room: { w: 10, h: 10, type: 'living', name: 'Living Room' },
                          living: { w: 10, h: 10, type: 'living', name: 'Living Room' },
                          kitchen: { w: 8, h: 8, type: 'kitchen', name: 'Kitchen' },
                          master_bedroom: { w: 14, h: 12, type: 'master_bedroom', name: 'Master Bedroom' },
                          bedroom: { w: 12, h: 10, type: 'bedroom', name: 'Bedroom' },
                          bathroom: { w: 6, h: 6, type: 'bathroom', name: 'Bathroom' },
                          pooja_room: { w: 6, h: 6, type: 'pooja', name: 'Pooja Room' }
                        };
                        const baseRooms = roomsNeeded.map((key: string, idx: number) => {
                          const k = String(key).toLowerCase();
                          const def = defaults[k] || defaults[k.split(' ').join('_')] || { w: 8, h: 8, type: k, name: key } as any;
                          return { id: `${k}_${idx + 1}`, name: def.name, type: def.type, width: def.w, height: def.h, x: 0, y: 0 };
                        });

                        const payload = {
                          rooms: baseRooms,
                          plotWidth: width,
                          plotLength: length,
                          plotShape: 'rectangular',
                          solver_type: 'constraint',  // VGF-SA solver for better Vastu compliance (94% vs 45%)
                          constraints: orientation ? { house_facing: orientation } : undefined,
                        };

                        try {
                          let genRes = await fetch('http://localhost:8000/api/solvers/generate', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                          });
                          console.log('[ServerLLM][ConstraintSolverResponse]', { status: genRes.status, ok: genRes.ok });
                          if (!genRes.ok) {
                            // Log why constraint solver failed
                            console.warn('[ServerLLM][ConstraintSolverFailed] status:', genRes.status, 'falling back to graph solver');
                            // Fallback to graph solver if constraint fails
                            genRes = await fetch('http://localhost:8000/api/solvers/generate', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ ...payload, solver_type: 'graph' })
                            });
                          }
                          const genJson = await genRes.json();
                          console.log('[ServerLLM][ToolResult]', { round: roundIndex, solver_type: genJson.solver_type, rooms: Array.isArray(genJson.rooms) ? genJson.rooms.length : undefined, score: genJson.score });
                          result = genJson;
                        } catch (e: any) {
                          console.error('[ServerLLM][ToolError]', { round: roundIndex, message: e?.message });
                          result = { status: 'error', message: e?.message || 'Backend generation failed' };
                        }
                      }

                      if (onToolCall) {
                        try { onToolCall(toolCall, result); } catch { }
                      }

                      // Append tool result to rolling messages for next round
                      rollingMessages.push({ role: 'tool', content: JSON.stringify(result), name: toolCall.function.name });
                      haveToolResults = true;
                      lastToolResult = result;
                    } catch (e) {
                      console.error('[ServerLLM][ToolArgsParseError]', { round: roundIndex });
                      // ignore malformed args
                    }
                  }
                }
                if (parsed.done && streamedCharsThisRound === 0) {
                  console.warn('[ServerLLM][StreamDoneNoContent]', {
                    round: roundIndex,
                    parsedKeys: Object.keys(parsed),
                    fullParsed: JSON.stringify(parsed)
                  });
                }
              } catch (e) {
                // Skip invalid JSON lines (handled by buffering)
              }
            } else {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') continue;
                try {
                  const parsed = JSON.parse(data);
                  const content = parsed.choices?.[0]?.delta?.content;
                  if (content) {
                    fullResponse += content;
                    if (onToken) onToken(content);
                    streamedCharsThisRound += content.length;
                    if (!firstTokenLogged) {
                      console.log('[ServerLLM][TokenStart]', { round: roundIndex });
                      firstTokenLogged = true;
                    }
                  }
                } catch { }
              }
            }
          }
        }
        // Parse any residual buffered JSON after stream ends (e.g., single final line without newline)
        if (streamBuffer && streamBuffer.trim().length > 0) {
          try {
            if (isOllama) {
              const parsed = JSON.parse(streamBuffer);
              // Try multiple possible locations for text content (residual)
              const content: string = parsed.message?.content
                || parsed.message?.thinking
                || parsed.response
                || parsed.thinking
                || parsed.content
                || parsed.text
                || '';
              if (content) {
                fullResponse += content;
                if (onToken) onToken(content);
                streamedCharsThisRound += content.length;
                if (!firstTokenLogged) {
                  console.log('[ServerLLM][TokenStart]', {
                    round: roundIndex,
                    residual: true,
                    firstChars: content.substring(0, 50),
                    contentLength: content.length,
                    source: parsed.message?.thinking ? 'thinking' : (parsed.message?.content ? 'content' : (parsed.thinking ? 'thinking(root)' : 'other'))
                  });
                  firstTokenLogged = true;
                }
              }
              if (!content && Object.keys(parsed).length > 0) {
                console.log('[ServerLLM][EmptyContent]', {
                  round: roundIndex,
                  residual: true,
                  keys: Object.keys(parsed),
                  sample: JSON.stringify(parsed).substring(0, 150)
                });
              }
              const toolCallsResidual = parsed.message?.tool_calls || parsed.tool_calls;
              if (Array.isArray(toolCallsResidual) && toolCallsResidual.length > 0) {
                encounteredToolCall = true;
                console.log('[ServerLLM][ToolCallsDetected]', { round: roundIndex, count: toolCallsResidual.length, residual: true });
                for (const toolCall of toolCallsResidual as ToolCall[]) {
                  try {
                    // Handle both string and object arguments
                    let args: Record<string, any>;
                    const rawArgs = toolCall.function?.arguments ?? toolCall.arguments ?? '{}';
                    if (typeof rawArgs === 'string') {
                      args = JSON.parse(rawArgs);
                    } else if (typeof rawArgs === 'object') {
                      args = rawArgs as Record<string, any>;
                    } else {
                      args = {};
                    }
                    let result: any = { status: 'error', message: 'No handler' };
                    console.log('[ServerLLM][ToolCall]', { round: roundIndex, name: toolCall.function?.name || toolCall.name, argsKeys: Object.keys(args), residual: true });
                    // (tool handler remains same)
                  } catch { }
                }
              }
            } else {
              if (streamBuffer.startsWith('data: ')) {
                const data = streamBuffer.slice(6);
                if (data !== '[DONE]') {
                  const parsed = JSON.parse(data);
                  const content = parsed.choices?.[0]?.delta?.content || parsed.choices?.[0]?.message?.content;
                  if (content) {
                    fullResponse += content;
                    if (onToken) onToken(content);
                    streamedCharsThisRound += content.length;
                    if (!firstTokenLogged) {
                      console.log('[ServerLLM][TokenStart]', { round: roundIndex, residual: true });
                      firstTokenLogged = true;
                    }
                  }
                }
              }
            }
            console.log('[ServerLLM][ResidualParsed]', { round: roundIndex });
          } catch {
            // ignore if residual is not valid JSON
          }
        }
        if (stallTimer) clearTimeout(stallTimer);

        // If we handled a tool call, start another round to let the model respond
        if (encounteredToolCall) {
          // Encourage narrative in the follow-up by appending a brief assistant nudge
          rollingMessages.push({
            role: 'assistant',
            content: `Tool execution complete. Now provide an INTERACTIVE response that includes:
1. A brief summary of what was created (room count, plot size, key features)
2. Vastu compliance highlights (what's good and what could be improved)
3. Ask 1-2 SPECIFIC questions like: "Do you prefer open or enclosed kitchen?" or "Would you like attached bathrooms?"
4. Offer 2-3 specific suggestions: "I can move the master bedroom to SW for better Vastu" or "Should I add a study room?"

Be conversational and engaging. Do NOT call any tools again.`,
          });
          console.log('[ServerLLM][RoundEnd]', { round: roundIndex, encounteredToolCall, streamedChars: streamedCharsThisRound, durationMs: Math.round(performance.now() - roundStart) });
          rounds += 1;
          continue;
        }
        // If no tokens streamed and no tool calls, try a non-stream fallback to avoid stalling
        if (streamedCharsThisRound === 0 && !encounteredToolCall) {
          console.warn('[ServerLLM][NoStreamData] Attempting non-stream fallback', { round: roundIndex });
          const flatResponse = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(isOllama ? {
              model: config.model || 'gpt-oss:20b-cloud',
              messages: rollingMessages,
              stream: false,
              tools: ollamaTools && !shouldDisableToolsThisRound ? ollamaTools : undefined,
              tool_choice: initialToolChoice,
              options: {
                num_predict: 1024,
                temperature: 0.3,
                stop: [
                  '<think>',
                  '</think>',
                ],
                repeat_penalty: 1.1,
                num_ctx: 4096,
                num_thread: 4,
                top_k: 40,
                top_p: 0.9,
              },
              think: false,
              format: undefined,
              system: undefined,
            } : {
              model: config.model || 'default',
              messages: rollingMessages,
              stream: false,
              temperature: 0.4,
            })
          });
          if (flatResponse.ok) {
            const json = await flatResponse.json();
            if (isOllama) {
              const content = json?.message?.content
                || json?.message?.thinking
                || json?.response
                || json?.thinking
                || json?.content
                || json?.text
                || '';
              if (content) {
                fullResponse += content;
                if (onToken) onToken(content);
              }
            } else {
              const content = json?.choices?.[0]?.message?.content ?? '';
              if (content) {
                fullResponse += content;
                if (onToken) onToken(content);
              }
            }
            const addedChars = (json?.message?.content || json?.message?.thinking || json?.choices?.[0]?.message?.content || '').length || 0;
            console.log('[ServerLLM][FallbackNonStream] Completed', { addedChars });
          } else {
            console.error('[ServerLLM][FallbackNonStream] Failed', { status: flatResponse.status });
          }
        }
        // No tool calls; we're done
        console.log('[ServerLLM][RoundEnd]', { round: roundIndex, encounteredToolCall, streamedChars: streamedCharsThisRound, durationMs: Math.round(performance.now() - roundStart) });
        break;
      }

      // If no text was produced but we have tool results, synthesize a concise summary
      if (!fullResponse && haveToolResults && lastToolResult && typeof lastToolResult === 'object') {
        try {
          const rooms = Array.isArray(lastToolResult.rooms) ? lastToolResult.rooms.length : undefined;
          const score = typeof lastToolResult.score === 'number' ? Math.round(lastToolResult.score) : undefined;
          const solver = lastToolResult.solver || 'graph';
          fullResponse = `Generated layout using ${solver} solver${score ? ` (score ${score})` : ''}. Visualized rooms${rooms ? ` (${rooms})` : ''} have been updated. Summary: 1) Plot parsed and constraints applied; 2) Vastu potential mapping considered; 3) Rule-guided placement optimized; 4) Final vector output rendered.`;
        } catch { }
      }

      console.log('[ServerLLM][Done]', {
        roundsExecuted: rounds,
        haveToolResults,
        responseLength: fullResponse.length,
      });

      // Clean thinking/reasoning patterns from the response before returning
      const cleanedResponse = cleanThinkingContent(fullResponse);
      console.log('[ServerLLM][CleanedResponse]', {
        originalLength: fullResponse.length,
        cleanedLength: cleanedResponse.length
      });

      return cleanedResponse;
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
    initializeModel: async () => { }, // No-op for server LLMs
  };
}
