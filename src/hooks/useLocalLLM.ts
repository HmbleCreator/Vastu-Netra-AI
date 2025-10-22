import { useState, useCallback, useRef } from 'react';
import { pipeline } from '@huggingface/transformers';

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export function useLocalLLM() {
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modelRef = useRef<any>(null);

  const initializeModel = useCallback(async () => {
    if (modelRef.current) return;
    
    setIsInitializing(true);
    setError(null);
    
    try {
      // Using Qwen2.5-0.5B-Instruct for fast inference
      modelRef.current = await pipeline(
        'text-generation',
        'onnx-community/Qwen2.5-0.5B-Instruct',
        { device: 'webgpu' } as any
      );
      console.log('Local LLM initialized successfully');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to initialize model';
      setError(errorMessage);
      console.error('Error initializing LLM:', err);
    } finally {
      setIsInitializing(false);
    }
  }, []);

  const generateResponse = useCallback(async (
    messages: Message[],
    onToken?: (token: string) => void
  ): Promise<string> => {
    if (!modelRef.current) {
      await initializeModel();
      if (!modelRef.current) {
        throw new Error('Model failed to initialize');
      }
    }

    setIsLoading(true);
    setError(null);

    try {
      // Format messages for the model
      const prompt = messages
        .map(m => {
          if (m.role === 'system') return `System: ${m.content}`;
          if (m.role === 'user') return `User: ${m.content}`;
          return `Assistant: ${m.content}`;
        })
        .join('\n\n') + '\n\nAssistant:';

      const result = await modelRef.current(prompt, {
        max_new_tokens: 512,
        temperature: 0.7,
        top_p: 0.9,
        do_sample: true,
      });

      // Extract the generated text from the result
      let response = '';
      if (Array.isArray(result) && result.length > 0) {
        const text = result[0]?.generated_text || result[0]?.text || '';
        response = text.split('Assistant:').pop()?.trim() || text;
      } else if (typeof result === 'object' && result !== null) {
        const text = (result as any).generated_text || (result as any).text || '';
        response = text.split('Assistant:').pop()?.trim() || text;
      }
      
      if (onToken) {
        onToken(response);
      }

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate response';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [initializeModel]);

  return {
    generateResponse,
    initializeModel,
    isLoading,
    isInitializing,
    error,
    isReady: !!modelRef.current
  };
}
