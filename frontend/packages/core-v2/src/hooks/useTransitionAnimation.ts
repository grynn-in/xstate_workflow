import { useState, useCallback, useRef } from 'react';

/**
 * Metadata for an animating edge
 */
interface AnimatingEdge {
  startTime: number;
  fromNode: string;
  toNode: string;
}

/**
 * Edge structure for lookup
 */
interface EdgeLike {
  id: string;
  source: string;
  target: string;
}

/**
 * Options for useTransitionAnimation hook
 */
export interface UseTransitionAnimationOptions {
  /** Animation duration in milliseconds (default: 800) */
  duration?: number;
  /** Edges array for node-based lookup */
  edges?: EdgeLike[];
  /** Callback when animation completes */
  onAnimationComplete?: (edgeId: string, fromNode: string, toNode: string) => void;
}

/**
 * Return type for useTransitionAnimation hook
 */
export interface UseTransitionAnimationReturn {
  /** Map of currently animating edges */
  animatingEdges: Map<string, AnimatingEdge>;
  /** Trigger animation for a specific edge */
  triggerAnimation: (edgeId: string, fromNode: string, toNode: string) => void;
  /** Trigger animation by finding edge from source/target nodes */
  triggerAnimationByNodes: (fromNodeId: string, toNodeId: string) => void;
  /** Check if a specific edge is currently animating */
  isAnimating: (edgeId: string) => boolean;
  /** Get animation progress (0-1) for an edge */
  getAnimationProgress: (edgeId: string) => number;
}

/**
 * Hook for managing transition animations on workflow edges.
 *
 * Provides functionality to:
 * - Trigger animations on edges when transitions occur
 * - Track which edges are currently animating
 * - Auto-cleanup animations after duration
 * - Get animation progress for rendering
 *
 * @example
 * ```tsx
 * const { triggerAnimation, isAnimating } = useTransitionAnimation({
 *   duration: 800,
 *   onAnimationComplete: (edgeId) => console.log('Animation done:', edgeId)
 * });
 *
 * // When a transition happens:
 * triggerAnimation('edge-1', 'stateA', 'stateB');
 *
 * // In edge component:
 * const animating = isAnimating(edge.id);
 * ```
 */
export function useTransitionAnimation(
  options: UseTransitionAnimationOptions = {}
): UseTransitionAnimationReturn {
  const { duration = 800, edges = [], onAnimationComplete } = options;

  const [animatingEdges, setAnimatingEdges] = useState<Map<string, AnimatingEdge>>(
    () => new Map()
  );
  const timeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  /**
   * Trigger animation for a specific edge
   */
  const triggerAnimation = useCallback(
    (edgeId: string, fromNode: string, toNode: string) => {
      // Add edge to animating set
      setAnimatingEdges((prev) => {
        const next = new Map(prev);
        next.set(edgeId, {
          startTime: Date.now(),
          fromNode,
          toNode,
        });
        return next;
      });

      // Clear existing timeout for this edge if any (reset animation)
      const existingTimeout = timeoutsRef.current.get(edgeId);
      if (existingTimeout) {
        clearTimeout(existingTimeout);
      }

      // Set timeout to remove animation after duration
      const timeout = setTimeout(() => {
        setAnimatingEdges((prev) => {
          const next = new Map(prev);
          next.delete(edgeId);
          return next;
        });
        timeoutsRef.current.delete(edgeId);
        onAnimationComplete?.(edgeId, fromNode, toNode);
      }, duration);

      timeoutsRef.current.set(edgeId, timeout);
    },
    [duration, onAnimationComplete]
  );

  /**
   * Trigger animation by finding edge from source/target node IDs
   */
  const triggerAnimationByNodes = useCallback(
    (fromNodeId: string, toNodeId: string) => {
      const edge = edges.find(
        (e) => e.source === fromNodeId && e.target === toNodeId
      );
      if (edge) {
        triggerAnimation(edge.id, fromNodeId, toNodeId);
      }
    },
    [edges, triggerAnimation]
  );

  /**
   * Check if a specific edge is currently animating
   */
  const isAnimating = useCallback(
    (edgeId: string): boolean => {
      return animatingEdges.has(edgeId);
    },
    [animatingEdges]
  );

  /**
   * Get animation progress (0-1) for an edge
   * Returns 0 if edge is not animating
   */
  const getAnimationProgress = useCallback(
    (edgeId: string): number => {
      const edgeData = animatingEdges.get(edgeId);
      if (!edgeData) return 0;

      const elapsed = Date.now() - edgeData.startTime;
      return Math.min(1, Math.max(0, elapsed / duration));
    },
    [animatingEdges, duration]
  );

  return {
    animatingEdges,
    triggerAnimation,
    triggerAnimationByNodes,
    isAnimating,
    getAnimationProgress,
  };
}
