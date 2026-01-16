import { useState, useMemo, useCallback } from 'react';

/**
 * Transition log entry from the backend
 */
interface TransitionLogEntry {
  from_state: string;
  to_state: string;
  event: string;
  timestamp: string;
  user?: string;
}

/**
 * Processed timeline entry with computed metadata
 */
export interface TimelineEntry {
  /** Index in the timeline (0-based) */
  index: number;
  /** State before transition */
  fromState: string;
  /** State after transition */
  toState: string;
  /** Event that triggered the transition */
  event: string;
  /** ISO timestamp string */
  timestamp: string;
  /** User who triggered the transition */
  user?: string;
  /** Milliseconds from start of workflow */
  relativeTimeMs: number;
  /** Milliseconds spent in the fromState (null for last entry) */
  durationMs: number | null;
  /** Human-readable formatted time */
  formattedTime: string;
  /** Position as percentage (0-100) for rendering */
  positionPercent: number;
}

/**
 * Options for useExecutionTimeline hook
 */
export interface UseExecutionTimelineOptions {
  /** Transition log from the workflow instance */
  transitionLog: TransitionLogEntry[];
  /** Current state of the workflow */
  currentState?: string;
  /** Callback when an entry is selected */
  onSelect?: (entry: TimelineEntry) => void;
}

/**
 * Return type for useExecutionTimeline hook
 */
export interface UseExecutionTimelineReturn {
  /** Processed timeline entries */
  entries: TimelineEntry[];
  /** Currently selected entry index (null if none) */
  selectedIndex: number | null;
  /** Currently selected entry (null if none) */
  selectedEntry: TimelineEntry | null;
  /** Total duration from first to last transition in ms */
  totalDurationMs: number;
  /** State at the selected point in time (or current if no selection) */
  timeTravelState: string | null;
  /** States visited up to the selected point */
  visitedStatesAtSelection: string[];
  /** Transitions up to the selected point */
  transitionsAtSelection: TimelineEntry[];
  /** Select an entry by index */
  selectEntry: (index: number) => void;
  /** Clear the current selection */
  clearSelection: () => void;
  /** Navigate to next entry */
  nextEntry: () => void;
  /** Navigate to previous entry */
  previousEntry: () => void;
  /** Whether selection is at start of timeline */
  isAtStart: boolean;
  /** Whether selection is at end of timeline */
  isAtEnd: boolean;
  /** Whether can navigate to next */
  canGoNext: boolean;
  /** Whether can navigate to previous */
  canGoPrevious: boolean;
}

/**
 * Format a timestamp for display
 */
function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return timestamp;
  }
}

/**
 * Parse timestamp to milliseconds
 */
function parseTimestamp(timestamp: string): number {
  try {
    return new Date(timestamp).getTime();
  } catch {
    return 0;
  }
}

/**
 * Hook for managing execution timeline state and navigation.
 *
 * Provides:
 * - Processed timeline entries with computed durations and positions
 * - Selection and navigation between entries
 * - "Time travel" state showing workflow at a specific point in history
 *
 * @example
 * ```tsx
 * const {
 *   entries,
 *   selectedEntry,
 *   selectEntry,
 *   timeTravelState,
 *   nextEntry,
 *   previousEntry,
 * } = useExecutionTimeline({
 *   transitionLog,
 *   currentState,
 *   onSelect: (entry) => highlightState(entry.toState),
 * });
 *
 * // Render timeline
 * entries.map((entry) => (
 *   <TimelineMarker
 *     key={entry.index}
 *     position={entry.positionPercent}
 *     onClick={() => selectEntry(entry.index)}
 *   />
 * ));
 * ```
 */
export function useExecutionTimeline(
  options: UseExecutionTimelineOptions
): UseExecutionTimelineReturn {
  const { transitionLog, currentState, onSelect } = options;

  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  // Process transition log into timeline entries
  const { entries, totalDurationMs } = useMemo(() => {
    if (transitionLog.length === 0) {
      return { entries: [], totalDurationMs: 0 };
    }

    // Parse all timestamps
    const timestamps = transitionLog.map((entry) => parseTimestamp(entry.timestamp));
    const startTime = timestamps[0];
    const endTime = timestamps[timestamps.length - 1];
    const totalDuration = endTime - startTime;

    const processedEntries: TimelineEntry[] = transitionLog.map((entry, index) => {
      const entryTime = timestamps[index];
      const relativeTimeMs = entryTime - startTime;

      // Calculate duration (time until next transition)
      let durationMs: number | null = null;
      if (index < transitionLog.length - 1) {
        durationMs = timestamps[index + 1] - entryTime;
      }

      // Calculate position percentage
      const positionPercent = totalDuration > 0
        ? (relativeTimeMs / totalDuration) * 100
        : (index / Math.max(transitionLog.length - 1, 1)) * 100;

      return {
        index,
        fromState: entry.from_state,
        toState: entry.to_state,
        event: entry.event,
        timestamp: entry.timestamp,
        user: entry.user,
        relativeTimeMs,
        durationMs,
        formattedTime: formatTime(entry.timestamp),
        positionPercent,
      };
    });

    return {
      entries: processedEntries,
      totalDurationMs: totalDuration,
    };
  }, [transitionLog]);

  // Get selected entry
  const selectedEntry = useMemo(() => {
    if (selectedIndex === null || selectedIndex < 0 || selectedIndex >= entries.length) {
      return null;
    }
    return entries[selectedIndex];
  }, [entries, selectedIndex]);

  // Time travel state
  const timeTravelState = useMemo(() => {
    if (selectedEntry) {
      return selectedEntry.toState;
    }
    return currentState ?? null;
  }, [selectedEntry, currentState]);

  // States visited up to selected point
  const visitedStatesAtSelection = useMemo(() => {
    if (selectedIndex === null) {
      // Return all visited states
      const states = new Set<string>();
      entries.forEach((entry) => {
        states.add(entry.fromState);
        states.add(entry.toState);
      });
      return Array.from(states);
    }

    const states = new Set<string>();
    for (let i = 0; i <= selectedIndex; i++) {
      states.add(entries[i].fromState);
      states.add(entries[i].toState);
    }
    return Array.from(states);
  }, [entries, selectedIndex]);

  // Transitions up to selected point
  const transitionsAtSelection = useMemo(() => {
    if (selectedIndex === null) {
      return entries;
    }
    return entries.slice(0, selectedIndex + 1);
  }, [entries, selectedIndex]);

  // Navigation state
  const isAtStart = selectedIndex === 0 || (selectedIndex === null && entries.length === 0);
  const isAtEnd = selectedIndex === entries.length - 1 || (selectedIndex === null && entries.length === 0);
  const canGoNext = selectedIndex === null || selectedIndex < entries.length - 1;
  const canGoPrevious = selectedIndex !== null && selectedIndex > 0;

  // Select entry
  const selectEntry = useCallback(
    (index: number) => {
      if (index < 0 || index >= entries.length) {
        return;
      }
      setSelectedIndex(index);
      onSelect?.(entries[index]);
    },
    [entries, onSelect]
  );

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedIndex(null);
  }, []);

  // Navigate to next entry
  const nextEntry = useCallback(() => {
    if (entries.length === 0) return;

    if (selectedIndex === null) {
      selectEntry(0);
    } else if (selectedIndex < entries.length - 1) {
      selectEntry(selectedIndex + 1);
    }
  }, [entries.length, selectedIndex, selectEntry]);

  // Navigate to previous entry
  const previousEntry = useCallback(() => {
    if (entries.length === 0) return;

    if (selectedIndex === null) {
      selectEntry(entries.length - 1);
    } else if (selectedIndex > 0) {
      selectEntry(selectedIndex - 1);
    }
  }, [entries.length, selectedIndex, selectEntry]);

  return {
    entries,
    selectedIndex,
    selectedEntry,
    totalDurationMs,
    timeTravelState,
    visitedStatesAtSelection,
    transitionsAtSelection,
    selectEntry,
    clearSelection,
    nextEntry,
    previousEntry,
    isAtStart,
    isAtEnd,
    canGoNext,
    canGoPrevious,
  };
}
