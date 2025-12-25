import { useState, useCallback, useRef, useEffect } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Error loading ${key} from localStorage:`, error);
      return initialValue;
    }
  });

  // Keep a ref to avoid stale closure issues
  const storedValueRef = useRef(storedValue);
  useEffect(() => {
    storedValueRef.current = storedValue;
  }, [storedValue]);

  const setValue = useCallback((value: T | ((val: T) => T)) => {
    try {
      // For function updaters, read fresh value from localStorage to avoid stale closures
      let currentValue: T;
      if (value instanceof Function) {
        const item = window.localStorage.getItem(key);
        currentValue = item ? JSON.parse(item) : storedValueRef.current;
      } else {
        currentValue = storedValueRef.current;
      }

      const valueToStore = value instanceof Function ? value(currentValue) : value;
      setStoredValue(valueToStore);
      storedValueRef.current = valueToStore;
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(`Error saving ${key} to localStorage:`, error);
    }
  }, [key]);

  return [storedValue, setValue] as const;
}
