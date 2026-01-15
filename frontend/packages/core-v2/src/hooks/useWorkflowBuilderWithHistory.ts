import { useCallback, useRef, useEffect } from 'react';
import {
  useWorkflowBuilder,
  type UseWorkflowBuilderOptions,
  type UseWorkflowBuilderReturn,
  type WorkflowBuilderConfig,
  type WorkflowNode,
  type WorkflowEdge,
} from '@xstate-workflow/core';
import { useUndoRedo } from './useUndoRedo';

/**
 * Workflow state snapshot for undo/redo
 */
interface WorkflowSnapshot {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

/**
 * Options for useWorkflowBuilderWithHistory hook
 */
export interface UseWorkflowBuilderWithHistoryOptions extends UseWorkflowBuilderOptions {
  /** Maximum number of undo steps (default: 50) */
  maxHistorySize?: number;
  /** Debounce time in ms for saving snapshots (default: 500) */
  debounceMs?: number;
}

/**
 * Return type for useWorkflowBuilderWithHistory hook
 */
export interface UseWorkflowBuilderWithHistoryReturn extends UseWorkflowBuilderReturn {
  /** Undo the last change */
  undo: () => void;
  /** Redo the previously undone change */
  redo: () => void;
  /** Whether undo is available */
  canUndo: boolean;
  /** Whether redo is available */
  canRedo: boolean;
  /** Number of items in history */
  historyLength: number;
  /** Take an immediate snapshot (for significant operations) */
  takeSnapshot: () => void;
}

/**
 * Deep clone an object using JSON serialization
 */
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Hook that wraps useWorkflowBuilder with undo/redo functionality.
 *
 * Automatically tracks changes to nodes and edges, allowing users to
 * undo/redo their modifications. Uses debouncing to avoid creating
 * too many history entries for rapid changes.
 *
 * @example
 * ```tsx
 * const {
 *   nodes,
 *   edges,
 *   undo,
 *   redo,
 *   canUndo,
 *   canRedo,
 *   ...rest
 * } = useWorkflowBuilderWithHistory({
 *   maxHistorySize: 50,
 *   debounceMs: 500,
 * });
 *
 * // In toolbar:
 * <button onClick={undo} disabled={!canUndo}>Undo</button>
 * <button onClick={redo} disabled={!canRedo}>Redo</button>
 * ```
 */
export function useWorkflowBuilderWithHistory(
  options: UseWorkflowBuilderWithHistoryOptions = {}
): UseWorkflowBuilderWithHistoryReturn {
  const { maxHistorySize = 50, debounceMs = 500, ...builderOptions } = options;

  // Use the base workflow builder
  const builder = useWorkflowBuilder(builderOptions);
  const { nodes, edges, loadConfig, getConfig } = builder;

  // Track whether we're currently restoring from history (to avoid re-saving)
  const isRestoringRef = useRef(false);

  // Debounce timer ref
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track the last saved snapshot to detect actual changes
  const lastSnapshotRef = useRef<string>('');

  // Initialize undo/redo with current state
  const initialSnapshot: WorkflowSnapshot = {
    nodes: deepClone(nodes),
    edges: deepClone(edges),
  };

  const {
    state: historyState,
    setState: setHistoryState,
    undo: undoHistory,
    redo: redoHistory,
    canUndo,
    canRedo,
    historyLength,
    reset: resetHistory,
  } = useUndoRedo<WorkflowSnapshot>({
    initialState: initialSnapshot,
    maxHistorySize,
    onChange: (snapshot) => {
      // When undo/redo changes the state, restore it to the builder
      isRestoringRef.current = true;
      loadConfig({
        ...getConfig(),
        nodes: deepClone(snapshot.nodes),
        edges: deepClone(snapshot.edges),
      });
      // Reset after a microtask to ensure the state has been applied
      queueMicrotask(() => {
        isRestoringRef.current = false;
      });
    },
  });

  /**
   * Take an immediate snapshot of the current state
   */
  const takeSnapshot = useCallback(() => {
    if (isRestoringRef.current) return;

    const snapshot: WorkflowSnapshot = {
      nodes: deepClone(nodes),
      edges: deepClone(edges),
    };

    const snapshotKey = JSON.stringify(snapshot);
    if (snapshotKey !== lastSnapshotRef.current) {
      lastSnapshotRef.current = snapshotKey;
      setHistoryState(snapshot);
    }
  }, [nodes, edges, setHistoryState]);

  /**
   * Debounced snapshot - schedules a snapshot after debounceMs
   */
  const scheduleSnapshot = useCallback(() => {
    if (isRestoringRef.current) return;

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Schedule new snapshot
    debounceTimerRef.current = setTimeout(() => {
      takeSnapshot();
    }, debounceMs);
  }, [takeSnapshot, debounceMs]);

  // Watch for changes to nodes/edges and schedule snapshots
  useEffect(() => {
    // Skip if we're restoring from history
    if (isRestoringRef.current) return;

    // Skip the initial render (we already have the initial state in history)
    const currentKey = JSON.stringify({ nodes, edges });
    if (lastSnapshotRef.current === '') {
      lastSnapshotRef.current = currentKey;
      return;
    }

    // Schedule a debounced snapshot
    scheduleSnapshot();

    // Cleanup timer on unmount
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [nodes, edges, scheduleSnapshot]);

  /**
   * Undo - first flush any pending snapshot, then undo
   */
  const undo = useCallback(() => {
    // Flush any pending debounced snapshot first
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
      takeSnapshot();
    }
    undoHistory();
  }, [undoHistory, takeSnapshot]);

  /**
   * Redo - simply call redo from history
   */
  const redo = useCallback(() => {
    redoHistory();
  }, [redoHistory]);

  // Override loadConfig to reset history when loading a new workflow
  const loadConfigWithHistoryReset = useCallback(
    (config: WorkflowBuilderConfig) => {
      isRestoringRef.current = true;
      loadConfig(config);

      // Reset history with the new state
      const snapshot: WorkflowSnapshot = {
        nodes: deepClone(config.nodes),
        edges: deepClone(config.edges),
      };
      lastSnapshotRef.current = JSON.stringify(snapshot);
      resetHistory(snapshot);

      queueMicrotask(() => {
        isRestoringRef.current = false;
      });
    },
    [loadConfig, resetHistory]
  );

  return {
    ...builder,
    loadConfig: loadConfigWithHistoryReset,
    undo,
    redo,
    canUndo,
    canRedo,
    historyLength,
    takeSnapshot,
  };
}
