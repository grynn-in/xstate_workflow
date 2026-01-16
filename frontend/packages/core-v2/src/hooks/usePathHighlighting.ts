import { useMemo } from 'react';

/**
 * Transition log entry structure
 */
interface TransitionLogEntry {
  from_state: string;
  to_state: string;
  event?: string;
  timestamp?: string;
  user?: string;
}

/**
 * Edge structure for path analysis
 */
interface EdgeLike {
  id: string;
  source: string;
  target: string;
}

/**
 * Node structure for label matching
 */
interface NodeLike {
  id: string;
  data?: {
    label?: string;
  };
}

/**
 * Path statistics
 */
export interface PathStats {
  /** Total number of transitions in the log */
  totalTransitions: number;
  /** Number of unique edges visited */
  uniqueEdgesVisited: number;
  /** Number of unique nodes visited */
  uniqueNodesVisited: number;
}

/**
 * Options for usePathHighlighting hook
 */
export interface UsePathHighlightingOptions {
  /** All edges in the workflow */
  edges: EdgeLike[];
  /** All nodes in the workflow (for label matching) */
  nodes: NodeLike[];
  /** Transition history log */
  transitionLog: TransitionLogEntry[];
  /** Current state name */
  currentState: string;
}

/**
 * Return type for usePathHighlighting hook
 */
export interface UsePathHighlightingReturn {
  /** IDs of edges that have been traversed */
  visitedEdgeIds: string[];
  /** IDs of edges that have NOT been traversed */
  unvisitedEdgeIds: string[];
  /** IDs of nodes that have been visited */
  visitedNodeIds: string[];
  /** Map of edge ID to sequence number (order of traversal) */
  edgeSequenceMap: Map<string, number>;
  /** ID of the most recently traversed edge */
  currentEdgeId: string | undefined;
  /** Check if an edge has been visited */
  isEdgeVisited: (edgeId: string) => boolean;
  /** Get sequence number for an edge */
  getEdgeSequence: (edgeId: string) => number | undefined;
  /** Path statistics */
  pathStats: PathStats;
}

/**
 * Normalize a state name for comparison.
 * Handles case-insensitive matching and underscore/space variations.
 */
function normalizeStateName(name: string): string {
  return name.toLowerCase().replace(/[\s_-]+/g, '_');
}

/**
 * Find a node ID by state name, checking both ID and label.
 */
function findNodeIdByState(nodes: NodeLike[], stateName: string): string | undefined {
  const normalized = normalizeStateName(stateName);

  // First try exact ID match
  const byId = nodes.find((n) => normalizeStateName(n.id) === normalized);
  if (byId) return byId.id;

  // Then try label match
  const byLabel = nodes.find(
    (n) => n.data?.label && normalizeStateName(n.data.label) === normalized
  );
  if (byLabel) return byLabel.id;

  return undefined;
}

/**
 * Find an edge by source and target node IDs.
 */
function findEdge(edges: EdgeLike[], sourceId: string, targetId: string): EdgeLike | undefined {
  return edges.find((e) => e.source === sourceId && e.target === targetId);
}

/**
 * Hook for computing path highlighting data from transition history.
 *
 * Analyzes the transition log to determine:
 * - Which edges have been traversed (visited)
 * - The sequence number of each transition
 * - Which nodes have been visited
 * - Path statistics
 *
 * @example
 * ```tsx
 * const {
 *   visitedEdgeIds,
 *   edgeSequenceMap,
 *   isEdgeVisited,
 *   getEdgeSequence,
 * } = usePathHighlighting({
 *   edges,
 *   nodes,
 *   transitionLog,
 *   currentState,
 * });
 *
 * // In edge component:
 * const sequence = getEdgeSequence(edge.id);
 * const isVisited = isEdgeVisited(edge.id);
 * ```
 */
export function usePathHighlighting(
  options: UsePathHighlightingOptions
): UsePathHighlightingReturn {
  const { edges, nodes, transitionLog, currentState: _currentState } = options;

  // Compute all path highlighting data
  const pathData = useMemo(() => {
    const visitedEdgeIds: string[] = [];
    const edgeSequenceMap = new Map<string, number>();
    const visitedNodeSet = new Set<string>();
    let currentEdgeId: string | undefined;

    // Process each transition in order
    transitionLog.forEach((transition, index) => {
      const fromNodeId = findNodeIdByState(nodes, transition.from_state);
      const toNodeId = findNodeIdByState(nodes, transition.to_state);

      if (fromNodeId && toNodeId) {
        // Add nodes to visited set
        visitedNodeSet.add(fromNodeId);
        visitedNodeSet.add(toNodeId);

        // Find the edge for this transition
        const edge = findEdge(edges, fromNodeId, toNodeId);
        if (edge) {
          // Add to visited edges if not already there
          if (!visitedEdgeIds.includes(edge.id)) {
            visitedEdgeIds.push(edge.id);
          }

          // Update sequence number (using 1-based indexing, last occurrence wins)
          edgeSequenceMap.set(edge.id, index + 1);

          // Track the most recent edge
          currentEdgeId = edge.id;
        }
      }
    });

    // Compute unvisited edges
    const unvisitedEdgeIds = edges
      .filter((e) => !visitedEdgeIds.includes(e.id))
      .map((e) => e.id);

    // Compute visited nodes array
    const visitedNodeIds = Array.from(visitedNodeSet);

    // Compute stats
    const pathStats: PathStats = {
      totalTransitions: transitionLog.length,
      uniqueEdgesVisited: visitedEdgeIds.length,
      uniqueNodesVisited: visitedNodeIds.length,
    };

    return {
      visitedEdgeIds,
      unvisitedEdgeIds,
      visitedNodeIds,
      edgeSequenceMap,
      currentEdgeId,
      pathStats,
    };
  }, [edges, nodes, transitionLog]);

  // Helper functions
  const isEdgeVisited = (edgeId: string): boolean => {
    return pathData.visitedEdgeIds.includes(edgeId);
  };

  const getEdgeSequence = (edgeId: string): number | undefined => {
    return pathData.edgeSequenceMap.get(edgeId);
  };

  return {
    visitedEdgeIds: pathData.visitedEdgeIds,
    unvisitedEdgeIds: pathData.unvisitedEdgeIds,
    visitedNodeIds: pathData.visitedNodeIds,
    edgeSequenceMap: pathData.edgeSequenceMap,
    currentEdgeId: pathData.currentEdgeId,
    isEdgeVisited,
    getEdgeSequence,
    pathStats: pathData.pathStats,
  };
}
