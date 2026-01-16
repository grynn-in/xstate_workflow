import { useCallback, useRef } from 'react';
import { useSyncExternalStore } from 'react';

/**
 * Options for useUndoRedo hook
 */
export interface UseUndoRedoOptions<T> {
  /** Initial state */
  initialState: T;
  /** Maximum number of history entries to keep (default: 50) */
  maxHistorySize?: number;
  /** Callback when state changes (via setState, undo, or redo) */
  onChange?: (state: T) => void;
}

/**
 * Return type for useUndoRedo hook
 */
export interface UseUndoRedoReturn<T> {
  /** Current state */
  state: T;
  /** Update state and add to history */
  setState: (newState: T) => void;
  /** Undo to previous state */
  undo: () => void;
  /** Redo to next state */
  redo: () => void;
  /** Whether undo is available */
  canUndo: boolean;
  /** Whether redo is available */
  canRedo: boolean;
  /** Total number of history entries */
  historyLength: number;
  /** Current position in history (0-based) */
  currentIndex: number;
  /** Reset history with a new initial state */
  reset: (newInitialState: T) => void;
}

/**
 * Deep equality check for objects (simple implementation)
 */
function deepEqual<T>(a: T, b: T): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Internal store for undo/redo state
 */
interface UndoRedoStore<T> {
  history: T[];
  currentIndex: number;
}

/**
 * Hook for managing undo/redo functionality.
 *
 * Maintains a history stack of states and provides undo/redo operations.
 * Supports:
 * - Configurable max history size
 * - Duplicate state detection (skips consecutive identical states)
 * - Reset functionality
 * - Change callbacks
 *
 * @example
 * ```tsx
 * const {
 *   state,
 *   setState,
 *   undo,
 *   redo,
 *   canUndo,
 *   canRedo,
 * } = useUndoRedo({
 *   initialState: { nodes: [], edges: [] },
 *   maxHistorySize: 50,
 *   onChange: (newState) => console.log('State changed:', newState),
 * });
 *
 * // Make a change
 * setState({ nodes: [newNode], edges: [] });
 *
 * // Undo the change
 * if (canUndo) undo();
 *
 * // Redo the change
 * if (canRedo) redo();
 * ```
 */
export function useUndoRedo<T>(options: UseUndoRedoOptions<T>): UseUndoRedoReturn<T> {
  const { initialState, maxHistorySize = 50, onChange } = options;

  // Use a ref to store the mutable state to handle synchronous updates correctly
  const storeRef = useRef<UndoRedoStore<T>>({
    history: [initialState],
    currentIndex: 0,
  });

  // Listeners for useSyncExternalStore
  const listenersRef = useRef(new Set<() => void>());

  // Use ref for onChange to avoid it being a dependency
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  // Notify all listeners
  const emitChange = useCallback(() => {
    listenersRef.current.forEach((listener) => listener());
  }, []);

  // Subscribe function for useSyncExternalStore
  const subscribe = useCallback((listener: () => void) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  // Get snapshot for useSyncExternalStore
  const getSnapshot = useCallback(() => storeRef.current, []);

  // Use sync external store to trigger re-renders
  const store = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  // Current state
  const state = store.history[store.currentIndex];
  const canUndo = store.currentIndex > 0;
  const canRedo = store.currentIndex < store.history.length - 1;

  /**
   * Set a new state and add it to history
   */
  const setState = useCallback(
    (newState: T) => {
      const { history, currentIndex } = storeRef.current;

      // Check if new state is the same as current state (skip duplicates)
      const currentState = history[currentIndex];
      if (deepEqual(currentState, newState)) {
        return;
      }

      // Remove any "future" states (everything after currentIndex)
      const newHistory = history.slice(0, currentIndex + 1);

      // Add the new state
      newHistory.push(newState);

      // Trim history if it exceeds maxHistorySize + 1
      // (maxHistorySize controls number of undos, so we need maxHistorySize + 1 entries)
      let newIndex = currentIndex + 1;
      if (newHistory.length > maxHistorySize + 1) {
        newHistory.shift();
        newIndex = newHistory.length - 1;
      }

      // Update store
      storeRef.current = {
        history: newHistory,
        currentIndex: newIndex,
      };

      // Notify listeners
      emitChange();

      // Call onChange
      onChangeRef.current?.(newState);
    },
    [maxHistorySize, emitChange]
  );

  /**
   * Undo to previous state
   */
  const undo = useCallback(() => {
    const { history, currentIndex } = storeRef.current;

    if (currentIndex > 0) {
      const newIndex = currentIndex - 1;
      storeRef.current = {
        history,
        currentIndex: newIndex,
      };
      emitChange();
      onChangeRef.current?.(history[newIndex]);
    }
  }, [emitChange]);

  /**
   * Redo to next state
   */
  const redo = useCallback(() => {
    const { history, currentIndex } = storeRef.current;

    if (currentIndex < history.length - 1) {
      const newIndex = currentIndex + 1;
      storeRef.current = {
        history,
        currentIndex: newIndex,
      };
      emitChange();
      onChangeRef.current?.(history[newIndex]);
    }
  }, [emitChange]);

  /**
   * Reset history with a new initial state
   */
  const reset = useCallback(
    (newInitialState: T) => {
      storeRef.current = {
        history: [newInitialState],
        currentIndex: 0,
      };
      emitChange();
    },
    [emitChange]
  );

  return {
    state,
    setState,
    undo,
    redo,
    canUndo,
    canRedo,
    historyLength: store.history.length,
    currentIndex: store.currentIndex,
    reset,
  };
}
