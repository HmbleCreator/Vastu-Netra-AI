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
      const response = await fetch(`${config.endpoint}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: config.model || 'default',
          messages: messages.map(m => ({
            role: m.role,
            content: m.content
          })),
          stream: true,
          temperature: 0.7,
        }),
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
