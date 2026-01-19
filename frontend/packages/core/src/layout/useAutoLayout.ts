/**
 * Auto-layout hook for React Flow workflows
 *
 * Based on React Flow Pro example pattern:
 * - Monitors node/edge changes
 * - Triggers layout when nodes are initialized (have dimensions)
 * - Handles opacity transitions for smooth appearance
 */

import { useEffect, useRef, useCallback } from 'react';
import {
  useReactFlow,
  useNodesInitialized,
  useStore,
  type Node,
  type Edge,
} from '@xyflow/react';

import { elkLayout } from './elk';
import {
  getSourceHandlePosition,
  getTargetHandlePosition,
  type LayoutOptions,
  type LayoutDirection,
} from './index';

export interface UseAutoLayoutOptions {
  /** Layout direction */
  direction?: LayoutDirection;
  /** Spacing as [nodeToNode, betweenLayers] */
  spacing?: [number, number];
  /** Whether to run layout automatically on changes */
  auto?: boolean;
}

interface ElementsState {
  nodeCount: number;
  edgeCount: number;
  nodeIds: string;
  edgeConnections: string;
}

/**
 * Custom equality function to detect meaningful changes
 * Only triggers layout when structural changes occur (new nodes/edges, connection changes)
 */
function compareElements(a: ElementsState, b: ElementsState): boolean {
  return (
    a.nodeCount === b.nodeCount &&
    a.edgeCount === b.edgeCount &&
    a.nodeIds === b.nodeIds &&
    a.edgeConnections === b.edgeConnections
  );
}

/**
 * Select function to extract relevant state for comparison
 */
function selectElements(state: { nodes: Node[]; edges: Edge[] }): ElementsState {
  return {
    nodeCount: state.nodes.length,
    edgeCount: state.edges.length,
    nodeIds: state.nodes.map((n) => n.id).sort().join(','),
    edgeConnections: state.edges.map((e) => `${e.source}->${e.target}`).sort().join(','),
  };
}

/**
 * Hook to automatically layout workflow nodes using ELK
 *
 * @example
 * ```tsx
 * function WorkflowBuilder() {
 *   const { runLayout } = useAutoLayout({
 *     direction: 'LR',
 *     spacing: [120, 200],
 *     auto: false, // Manual layout only
 *   });
 *
 *   return (
 *     <button onClick={runLayout}>Auto Layout</button>
 *   );
 * }
 * ```
 */
export function useAutoLayout(options: UseAutoLayoutOptions = {}) {
  const { direction = 'LR', spacing = [120, 200], auto = false } = options;

  const { setNodes, setEdges, getNodes, getEdges, fitView } = useReactFlow();
  const nodesInitialized = useNodesInitialized();

  // Track elements for change detection
  const elements = useStore(selectElements, compareElements);

  // Track if we're currently running a layout
  const isLayouting = useRef(false);
  const lastLayoutRef = useRef<string>('');

  /**
   * Run the layout algorithm
   */
  const runLayout = useCallback(async () => {
    if (isLayouting.current) return;

    const nodes = getNodes();
    const edges = getEdges();

    if (nodes.length === 0) return;

    // Create a fingerprint of current state to avoid duplicate layouts
    const fingerprint = `${nodes.map((n) => n.id).join(',')}|${edges.map((e) => `${e.source}->${e.target}`).join(',')}`;
    if (fingerprint === lastLayoutRef.current) return;

    isLayouting.current = true;
    lastLayoutRef.current = fingerprint;

    try {
      const layoutOptions: LayoutOptions = {
        direction,
        spacing,
      };

      const { nodes: layoutNodes, edges: layoutEdges } = await elkLayout(
        nodes.map((n) => ({ ...n })),
        edges.map((e) => ({ ...e })),
        layoutOptions
      );

      // Update handle positions based on direction
      const sourcePosition = getSourceHandlePosition(direction);
      const targetPosition = getTargetHandlePosition(direction);

      const finalNodes = layoutNodes.map((node) => ({
        ...node,
        sourcePosition,
        targetPosition,
        // Ensure opacity is set for visibility
        style: { ...node.style, opacity: 1 },
      }));

      setNodes(finalNodes);
      setEdges(layoutEdges);

      // Fit view after layout with a small delay for rendering
      setTimeout(() => {
        fitView({ padding: 0.2, duration: 200 });
      }, 50);
    } catch (error) {
      console.error('ELK layout error:', error);
    } finally {
      isLayouting.current = false;
    }
  }, [direction, spacing, getNodes, getEdges, setNodes, setEdges, fitView]);

  // Auto-layout when enabled and nodes are initialized
  useEffect(() => {
    if (!auto) return;
    if (!nodesInitialized) return;
    if (elements.nodeCount === 0) return;

    // Run layout on structural changes
    runLayout();
  }, [auto, nodesInitialized, elements, runLayout]);

  return {
    /** Manually trigger the layout algorithm */
    runLayout,
    /** Whether nodes have been initialized (have dimensions) */
    nodesInitialized,
  };
}
