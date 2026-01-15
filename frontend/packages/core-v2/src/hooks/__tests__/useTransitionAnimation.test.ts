import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTransitionAnimation } from '../useTransitionAnimation';

describe('useTransitionAnimation', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should start with no animating edges', () => {
    const { result } = renderHook(() => useTransitionAnimation());
    expect(result.current.animatingEdges.size).toBe(0);
  });

  it('should add edge to animating set when triggerAnimation called', () => {
    const { result } = renderHook(() => useTransitionAnimation());

    act(() => {
      result.current.triggerAnimation('edge-1', 'node-a', 'node-b');
    });

    expect(result.current.animatingEdges.has('edge-1')).toBe(true);
  });

  it('should store animation metadata (fromNode, toNode)', () => {
    const { result } = renderHook(() => useTransitionAnimation());

    act(() => {
      result.current.triggerAnimation('edge-1', 'node-a', 'node-b');
    });

    const edgeData = result.current.animatingEdges.get('edge-1');
    expect(edgeData).toBeDefined();
    expect(edgeData?.fromNode).toBe('node-a');
    expect(edgeData?.toNode).toBe('node-b');
  });

  it('should remove edge from animating set after duration', () => {
    const { result } = renderHook(() => useTransitionAnimation({ duration: 800 }));

    act(() => {
      result.current.triggerAnimation('edge-1', 'node-a', 'node-b');
    });

    expect(result.current.animatingEdges.has('edge-1')).toBe(true);

    act(() => {
      vi.advanceTimersByTime(850);
    });

    expect(result.current.animatingEdges.has('edge-1')).toBe(false);
  });

  it('should call onAnimationComplete callback when animation ends', () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() =>
      useTransitionAnimation({ duration: 800, onAnimationComplete: onComplete })
    );

    act(() => {
      result.current.triggerAnimation('edge-1', 'node-a', 'node-b');
    });

    expect(onComplete).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(850);
    });

    expect(onComplete).toHaveBeenCalledWith('edge-1', 'node-a', 'node-b');
  });

  it('should find edge ID by source and target nodes', () => {
    const edges = [
      { id: 'e1', source: 'a', target: 'b' },
      { id: 'e2', source: 'b', target: 'c' },
    ];
    const { result } = renderHook(() => useTransitionAnimation({ edges }));

    act(() => {
      result.current.triggerAnimationByNodes('a', 'b');
    });

    expect(result.current.animatingEdges.has('e1')).toBe(true);
    expect(result.current.animatingEdges.has('e2')).toBe(false);
  });

  it('should not trigger animation if edge not found by nodes', () => {
    const edges = [
      { id: 'e1', source: 'a', target: 'b' },
    ];
    const { result } = renderHook(() => useTransitionAnimation({ edges }));

    act(() => {
      result.current.triggerAnimationByNodes('x', 'y'); // Non-existent edge
    });

    expect(result.current.animatingEdges.size).toBe(0);
  });

  it('should return isAnimating helper for edge lookup', () => {
    const { result } = renderHook(() => useTransitionAnimation());

    act(() => {
      result.current.triggerAnimation('edge-1', 'a', 'b');
    });

    expect(result.current.isAnimating('edge-1')).toBe(true);
    expect(result.current.isAnimating('edge-2')).toBe(false);
  });

  it('should handle multiple concurrent animations', () => {
    const { result } = renderHook(() => useTransitionAnimation({ duration: 800 }));

    act(() => {
      result.current.triggerAnimation('edge-1', 'a', 'b');
      result.current.triggerAnimation('edge-2', 'b', 'c');
    });

    expect(result.current.animatingEdges.size).toBe(2);
    expect(result.current.isAnimating('edge-1')).toBe(true);
    expect(result.current.isAnimating('edge-2')).toBe(true);

    act(() => {
      vi.advanceTimersByTime(850);
    });

    expect(result.current.animatingEdges.size).toBe(0);
  });

  it('should reset animation if triggered again before completion', () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() =>
      useTransitionAnimation({ duration: 800, onAnimationComplete: onComplete })
    );

    act(() => {
      result.current.triggerAnimation('edge-1', 'a', 'b');
    });

    // Advance partway through
    act(() => {
      vi.advanceTimersByTime(400);
    });

    // Trigger again - should reset the timer
    act(() => {
      result.current.triggerAnimation('edge-1', 'a', 'b');
    });

    // Advance another 400ms - original would have finished but reset shouldn't
    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(result.current.isAnimating('edge-1')).toBe(true);
    expect(onComplete).not.toHaveBeenCalled();

    // Advance remaining time
    act(() => {
      vi.advanceTimersByTime(450);
    });

    expect(result.current.isAnimating('edge-1')).toBe(false);
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('should use default duration of 800ms', () => {
    const { result } = renderHook(() => useTransitionAnimation());

    act(() => {
      result.current.triggerAnimation('edge-1', 'a', 'b');
    });

    // At 700ms, should still be animating
    act(() => {
      vi.advanceTimersByTime(700);
    });
    expect(result.current.isAnimating('edge-1')).toBe(true);

    // At 850ms (700 + 150), should be done
    act(() => {
      vi.advanceTimersByTime(150);
    });
    expect(result.current.isAnimating('edge-1')).toBe(false);
  });

  it('should return animation progress for an edge', () => {
    const { result } = renderHook(() => useTransitionAnimation({ duration: 1000 }));

    act(() => {
      result.current.triggerAnimation('edge-1', 'a', 'b');
    });

    // Progress should be available
    const progress = result.current.getAnimationProgress('edge-1');
    expect(progress).toBeGreaterThanOrEqual(0);
    expect(progress).toBeLessThanOrEqual(1);
  });

  it('should return 0 progress for non-animating edge', () => {
    const { result } = renderHook(() => useTransitionAnimation());

    const progress = result.current.getAnimationProgress('non-existent');
    expect(progress).toBe(0);
  });
});
