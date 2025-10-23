import { useState, useCallback } from 'react';
import { useLocalStorage } from './useLocalStorage';
import { Message } from './useLocalLLM';

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

export function useChatSessions() {
  const [sessions, setSessions] = useLocalStorage<ChatSession[]>('vastu-chat-sessions', []);
  const [activeSessionId, setActiveSessionId] = useLocalStorage<string | null>('active-session-id', null);

  // Initialize first session if none exist
  const initializeIfEmpty = useCallback(() => {
    if (sessions.length === 0) {
      const newSession: ChatSession = {
        id: crypto.randomUUID(),
        title: 'New Chat',
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      setSessions([newSession]);
      setActiveSessionId(newSession.id);
      return newSession;
    }
    return null;
  }, [sessions.length, setSessions, setActiveSessionId]);

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0] || initializeIfEmpty();

  const createSession = useCallback(() => {
    const newSession: ChatSession = {
      id: crypto.randomUUID(),
      title: 'New Chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setSessions(prev => [...prev, newSession]);
    setActiveSessionId(newSession.id);
    return newSession;
  }, [setSessions, setActiveSessionId]);

  const deleteSession = useCallback((sessionId: string) => {
    setSessions(prev => {
      const filtered = prev.filter(s => s.id !== sessionId);
      // If deleting active session, switch to another
      if (sessionId === activeSessionId && filtered.length > 0) {
        setActiveSessionId(filtered[0].id);
      }
      return filtered;
    });
  }, [setSessions, activeSessionId, setActiveSessionId]);

  const updateSession = useCallback((sessionId: string, updates: Partial<ChatSession>) => {
    setSessions(prev => prev.map(s => 
      s.id === sessionId 
        ? { ...s, ...updates, updatedAt: Date.now() }
        : s
    ));
  }, [setSessions]);

  const addMessage = useCallback((sessionId: string, message: Message) => {
    setSessions(prev => prev.map(s => {
      if (s.id === sessionId) {
        const newMessages = [...s.messages, message];
        // Auto-generate title from first user message
        const title = s.messages.length === 0 && message.role === 'user'
          ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
          : s.title;
        return {
          ...s,
          messages: newMessages,
          title,
          updatedAt: Date.now(),
        };
      }
      return s;
    }));
  }, [setSessions]);

  const clearSessionMessages = useCallback((sessionId: string) => {
    setSessions(prev => prev.map(s => 
      s.id === sessionId 
        ? { ...s, messages: [], updatedAt: Date.now() }
        : s
    ));
  }, [setSessions]);

  return {
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    createSession,
    deleteSession,
    updateSession,
    addMessage,
    clearSessionMessages,
  };
}
