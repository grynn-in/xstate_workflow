import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useExecutionTimeline } from '../useExecutionTimeline';

describe('useExecutionTimeline', () => {
  // Sample transition log entries
  const createLogEntry = (
    fromState: string,
    toState: string,
    event: string,
    timestamp: string,
    user?: string
  ) => ({
    from_state: fromState,
    to_state: toState,
    event,
    timestamp,
    user,
  });

  const sampleLog = [
    createLogEntry('Draft', 'Pending Review', 'SUBMIT', '2024-01-15T10:00:00', 'alice@example.com'),
    createLogEntry('Pending Review', 'Under Review', 'ASSIGN', '2024-01-15T10:30:00', 'bob@example.com'),
    createLogEntry('Under Review', 'Approved', 'APPROVE', '2024-01-15T14:00:00', 'charlie@example.com'),
  ];

  describe('initialization', () => {
    it('should initialize with empty entries when no log provided', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: [] })
      );

      expect(result.current.entries).toEqual([]);
      expect(result.current.selectedIndex).toBeNull();
    });

    it('should create timeline entries from transition log', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      expect(result.current.entries).toHaveLength(3);
    });

    it('should include entry metadata', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      const firstEntry = result.current.entries[0];
      expect(firstEntry.fromState).toBe('Draft');
      expect(firstEntry.toState).toBe('Pending Review');
      expect(firstEntry.event).toBe('SUBMIT');
      expect(firstEntry.user).toBe('alice@example.com');
      expect(firstEntry.index).toBe(0);
    });
  });

  describe('time calculations', () => {
    it('should calculate relative time from start', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      // First entry is at 0ms from start
      expect(result.current.entries[0].relativeTimeMs).toBe(0);

      // Second entry is 30 minutes later
      expect(result.current.entries[1].relativeTimeMs).toBe(30 * 60 * 1000);

      // Third entry is 4 hours after start
      expect(result.current.entries[2].relativeTimeMs).toBe(4 * 60 * 60 * 1000);
    });

    it('should calculate duration in each state', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      // Time spent in "Pending Review" = 30 minutes
      expect(result.current.entries[0].durationMs).toBe(30 * 60 * 1000);

      // Time spent in "Under Review" = 3.5 hours
      expect(result.current.entries[1].durationMs).toBe(3.5 * 60 * 60 * 1000);

      // Last entry has no duration (current state)
      expect(result.current.entries[2].durationMs).toBeNull();
    });

    it('should provide formatted time strings', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      // Check that formatted strings exist
      expect(result.current.entries[0].formattedTime).toBeDefined();
      expect(typeof result.current.entries[0].formattedTime).toBe('string');
    });

    it('should calculate total duration', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      // Total time from first to last transition = 4 hours
      expect(result.current.totalDurationMs).toBe(4 * 60 * 60 * 1000);
    });
  });

  describe('selection', () => {
    it('should select entry by index', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(1);
      });

      expect(result.current.selectedIndex).toBe(1);
      expect(result.current.selectedEntry?.toState).toBe('Under Review');
    });

    it('should clear selection', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(1);
      });

      act(() => {
        result.current.clearSelection();
      });

      expect(result.current.selectedIndex).toBeNull();
      expect(result.current.selectedEntry).toBeNull();
    });

    it('should call onSelect callback when entry selected', () => {
      const onSelect = vi.fn();
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog, onSelect })
      );

      act(() => {
        result.current.selectEntry(1);
      });

      expect(onSelect).toHaveBeenCalledWith(
        expect.objectContaining({ index: 1, toState: 'Under Review' })
      );
    });

    it('should not select invalid index', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(99);
      });

      expect(result.current.selectedIndex).toBeNull();
    });
  });

  describe('time travel state', () => {
    it('should return current state when no selection', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({
          transitionLog: sampleLog,
          currentState: 'Approved',
        })
      );

      expect(result.current.timeTravelState).toBe('Approved');
    });

    it('should return state at selected point in time', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({
          transitionLog: sampleLog,
          currentState: 'Approved',
        })
      );

      // Select the first transition (Draft -> Pending Review)
      act(() => {
        result.current.selectEntry(0);
      });

      // Time travel state should be the toState of that transition
      expect(result.current.timeTravelState).toBe('Pending Review');
    });

    it('should return visited states up to selected point', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({
          transitionLog: sampleLog,
          currentState: 'Approved',
        })
      );

      // Select second transition
      act(() => {
        result.current.selectEntry(1);
      });

      // Should include states visited up to that point
      expect(result.current.visitedStatesAtSelection).toContain('Draft');
      expect(result.current.visitedStatesAtSelection).toContain('Pending Review');
      expect(result.current.visitedStatesAtSelection).toContain('Under Review');
      expect(result.current.visitedStatesAtSelection).not.toContain('Approved');
    });

    it('should return visited edges up to selected point', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({
          transitionLog: sampleLog,
          currentState: 'Approved',
        })
      );

      // Select first transition
      act(() => {
        result.current.selectEntry(0);
      });

      // Should only include first transition
      expect(result.current.transitionsAtSelection).toHaveLength(1);
      expect(result.current.transitionsAtSelection[0].toState).toBe('Pending Review');
    });
  });

  describe('navigation', () => {
    it('should navigate to next entry', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(0);
      });

      act(() => {
        result.current.nextEntry();
      });

      expect(result.current.selectedIndex).toBe(1);
    });

    it('should navigate to previous entry', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(2);
      });

      act(() => {
        result.current.previousEntry();
      });

      expect(result.current.selectedIndex).toBe(1);
    });

    it('should not go past last entry', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(2);
      });

      act(() => {
        result.current.nextEntry();
      });

      expect(result.current.selectedIndex).toBe(2);
    });

    it('should not go before first entry', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(0);
      });

      act(() => {
        result.current.previousEntry();
      });

      expect(result.current.selectedIndex).toBe(0);
    });

    it('should select first entry when navigating with no selection', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.nextEntry();
      });

      expect(result.current.selectedIndex).toBe(0);
    });
  });

  describe('playback', () => {
    it('should indicate if at start of timeline', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(0);
      });

      expect(result.current.isAtStart).toBe(true);
      expect(result.current.isAtEnd).toBe(false);
    });

    it('should indicate if at end of timeline', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(2);
      });

      expect(result.current.isAtStart).toBe(false);
      expect(result.current.isAtEnd).toBe(true);
    });

    it('should provide canGoNext and canGoPrevious helpers', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      act(() => {
        result.current.selectEntry(1);
      });

      expect(result.current.canGoNext).toBe(true);
      expect(result.current.canGoPrevious).toBe(true);
    });
  });

  describe('empty state handling', () => {
    it('should handle empty transition log gracefully', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: [] })
      );

      expect(result.current.entries).toEqual([]);
      expect(result.current.totalDurationMs).toBe(0);
      expect(result.current.isAtStart).toBe(true);
      expect(result.current.isAtEnd).toBe(true);
    });

    it('should handle single entry', () => {
      const singleEntry = [sampleLog[0]];
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: singleEntry })
      );

      expect(result.current.entries).toHaveLength(1);
      expect(result.current.entries[0].durationMs).toBeNull();
    });
  });

  describe('entry position for rendering', () => {
    it('should calculate position percentage for each entry', () => {
      const { result } = renderHook(() =>
        useExecutionTimeline({ transitionLog: sampleLog })
      );

      // First entry at 0%
      expect(result.current.entries[0].positionPercent).toBe(0);

      // Last entry at 100%
      expect(result.current.entries[2].positionPercent).toBe(100);

      // Middle entry somewhere in between
      expect(result.current.entries[1].positionPercent).toBeGreaterThan(0);
      expect(result.current.entries[1].positionPercent).toBeLessThan(100);
    });
  });
});
