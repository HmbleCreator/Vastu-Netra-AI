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

export function useServerLLM(config: ServerLLMConfig) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateResponse = useCallback(async (
    messages: Message[],
    onToken?: (token: string) => void
  ): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
      const isOllama = config.type === 'ollama' || config.endpoint.includes('11434');
      const endpoint = isOllama ? `${config.endpoint}/api/chat` : `${config.endpoint}/v1/chat/completions`;
      
      const requestBody = isOllama ? {
        model: config.model || 'llama3.2',
        messages: messages.map(m => ({
          role: m.role,
          content: m.content
        })),
        stream: true,
      } : {
        model: config.model || 'default',
        messages: messages.map(m => ({
          role: m.role,
          content: m.content
        })),
        stream: true,
        temperature: 0.7,
      };

      const response = await fetch(endpoint, {
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

      while (true) {
        const { done, value } = await reader.read();
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
              }
              if (parsed.done) break;
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
