import { useCallback, useState, useMemo } from 'react';

/**
 * Position type
 */
interface Position {
  x: number;
  y: number;
}

/**
 * Node-like structure with position and optional measured dimensions
 */
interface NodeLike {
  id: string;
  position: Position;
  measured?: {
    width?: number;
    height?: number;
  };
}

/**
 * Horizontal helper line (for vertical alignment of nodes)
 */
export interface HorizontalLine {
  /** Y position of the line */
  y: number;
  /** Start X of the line */
  x1: number;
  /** End X of the line */
  x2: number;
  /** Type of alignment */
  type: 'top' | 'center' | 'bottom';
}

/**
 * Vertical helper line (for horizontal alignment of nodes)
 */
export interface VerticalLine {
  /** X position of the line */
  x: number;
  /** Start Y of the line */
  y1: number;
  /** End Y of the line */
  y2: number;
  /** Type of alignment */
  type: 'left' | 'center' | 'right';
}

/**
 * Options for useHelperLines hook
 */
export interface UseHelperLinesOptions {
  /** All nodes in the workflow */
  nodes: NodeLike[];
  /** Distance threshold for alignment detection (default: 5) */
  threshold?: number;
  /** Whether snapping is enabled (default: false) */
  enableSnapping?: boolean;
  /** Whether helper lines are enabled (default: true) */
  enabled?: boolean;
  /** Default node width when measured is not available */
  defaultNodeWidth?: number;
  /** Default node height when measured is not available */
  defaultNodeHeight?: number;
}

/**
 * Return type for useHelperLines hook
 */
export interface UseHelperLinesReturn {
  /** Currently active horizontal lines */
  horizontalLines: HorizontalLine[];
  /** Currently active vertical lines */
  verticalLines: VerticalLine[];
  /** Whether any helper lines are active */
  hasActiveLines: boolean;
  /** Snapped position if snapping is enabled and alignment found */
  snappedPosition: Position | null;
  /** Call when node drag starts/moves */
  onNodeDrag: (nodeId: string, position: Position) => void;
  /** Call when node drag ends */
  onNodeDragEnd: () => void;
}

/**
 * Get node bounds (left, right, top, bottom, centerX, centerY)
 */
function getNodeBounds(
  node: NodeLike,
  position: Position,
  defaultWidth: number,
  defaultHeight: number
) {
  const width = node.measured?.width ?? defaultWidth;
  const height = node.measured?.height ?? defaultHeight;

  return {
    left: position.x,
    right: position.x + width,
    top: position.y,
    bottom: position.y + height,
    centerX: position.x + width / 2,
    centerY: position.y + height / 2,
    width,
    height,
  };
}

/**
 * Hook for displaying alignment helper lines when dragging nodes.
 *
 * Shows visual guides when a dragged node aligns with other nodes:
 * - Horizontal lines for top/center/bottom alignment
 * - Vertical lines for left/center/right alignment
 * - Optional snapping to aligned positions
 *
 * @example
 * ```tsx
 * const {
 *   horizontalLines,
 *   verticalLines,
 *   hasActiveLines,
 *   snappedPosition,
 *   onNodeDrag,
 *   onNodeDragEnd,
 * } = useHelperLines({
 *   nodes,
 *   threshold: 5,
 *   enableSnapping: true,
 * });
 *
 * // In ReactFlow's onNodeDrag:
 * const handleNodeDrag = (event, node) => {
 *   onNodeDrag(node.id, node.position);
 *   if (snappedPosition) {
 *     // Apply snapped position
 *   }
 * };
 * ```
 */
export function useHelperLines(options: UseHelperLinesOptions): UseHelperLinesReturn {
  const {
    nodes,
    threshold = 5,
    enableSnapping = false,
    enabled = true,
    defaultNodeWidth = 150,
    defaultNodeHeight = 40,
  } = options;

  const [horizontalLines, setHorizontalLines] = useState<HorizontalLine[]>([]);
  const [verticalLines, setVerticalLines] = useState<VerticalLine[]>([]);
  const [snappedPosition, setSnappedPosition] = useState<Position | null>(null);

  // Create a map of nodes for quick lookup
  const nodeMap = useMemo(() => {
    const map = new Map<string, NodeLike>();
    nodes.forEach((node) => map.set(node.id, node));
    return map;
  }, [nodes]);

  /**
   * Handle node drag - compute helper lines
   */
  const onNodeDrag = useCallback(
    (nodeId: string, position: Position) => {
      if (!enabled) {
        setHorizontalLines([]);
        setVerticalLines([]);
        setSnappedPosition(null);
        return;
      }

      const draggedNode = nodeMap.get(nodeId);
      if (!draggedNode) return;

      const draggedBounds = getNodeBounds(draggedNode, position, defaultNodeWidth, defaultNodeHeight);

      const newHorizontalLines: HorizontalLine[] = [];
      const newVerticalLines: VerticalLine[] = [];
      let snapX: number | null = null;
      let snapY: number | null = null;

      // Check alignment with each other node
      nodes.forEach((otherNode) => {
        if (otherNode.id === nodeId) return; // Skip self

        const otherBounds = getNodeBounds(
          otherNode,
          otherNode.position,
          defaultNodeWidth,
          defaultNodeHeight
        );

        // === Horizontal alignments (Y axis) ===

        // Top-to-top alignment
        if (Math.abs(draggedBounds.top - otherBounds.top) <= threshold) {
          newHorizontalLines.push({
            y: otherBounds.top,
            x1: Math.min(draggedBounds.left, otherBounds.left),
            x2: Math.max(draggedBounds.right, otherBounds.right),
            type: 'top',
          });
          if (enableSnapping && snapY === null) {
            snapY = otherBounds.top;
          }
        }

        // Center-to-center horizontal alignment
        if (Math.abs(draggedBounds.centerY - otherBounds.centerY) <= threshold) {
          newHorizontalLines.push({
            y: otherBounds.centerY,
            x1: Math.min(draggedBounds.left, otherBounds.left),
            x2: Math.max(draggedBounds.right, otherBounds.right),
            type: 'center',
          });
          if (enableSnapping && snapY === null) {
            snapY = otherBounds.centerY - draggedBounds.height / 2;
          }
        }

        // Bottom-to-bottom alignment
        if (Math.abs(draggedBounds.bottom - otherBounds.bottom) <= threshold) {
          newHorizontalLines.push({
            y: otherBounds.bottom,
            x1: Math.min(draggedBounds.left, otherBounds.left),
            x2: Math.max(draggedBounds.right, otherBounds.right),
            type: 'bottom',
          });
          if (enableSnapping && snapY === null) {
            snapY = otherBounds.bottom - draggedBounds.height;
          }
        }

        // === Vertical alignments (X axis) ===

        // Left-to-left alignment
        if (Math.abs(draggedBounds.left - otherBounds.left) <= threshold) {
          newVerticalLines.push({
            x: otherBounds.left,
            y1: Math.min(draggedBounds.top, otherBounds.top),
            y2: Math.max(draggedBounds.bottom, otherBounds.bottom),
            type: 'left',
          });
          if (enableSnapping && snapX === null) {
            snapX = otherBounds.left;
          }
        }

        // Center-to-center vertical alignment
        if (Math.abs(draggedBounds.centerX - otherBounds.centerX) <= threshold) {
          newVerticalLines.push({
            x: otherBounds.centerX,
            y1: Math.min(draggedBounds.top, otherBounds.top),
            y2: Math.max(draggedBounds.bottom, otherBounds.bottom),
            type: 'center',
          });
          if (enableSnapping && snapX === null) {
            snapX = otherBounds.centerX - draggedBounds.width / 2;
          }
        }

        // Right-to-right alignment
        if (Math.abs(draggedBounds.right - otherBounds.right) <= threshold) {
          newVerticalLines.push({
            x: otherBounds.right,
            y1: Math.min(draggedBounds.top, otherBounds.top),
            y2: Math.max(draggedBounds.bottom, otherBounds.bottom),
            type: 'right',
          });
          if (enableSnapping && snapX === null) {
            snapX = otherBounds.right - draggedBounds.width;
          }
        }
      });

      setHorizontalLines(newHorizontalLines);
      setVerticalLines(newVerticalLines);

      // Set snapped position if snapping is enabled
      if (enableSnapping && (snapX !== null || snapY !== null)) {
        setSnappedPosition({
          x: snapX ?? position.x,
          y: snapY ?? position.y,
        });
      } else {
        setSnappedPosition(null);
      }
    },
    [enabled, nodeMap, nodes, threshold, enableSnapping, defaultNodeWidth, defaultNodeHeight]
  );

  /**
   * Handle node drag end - clear helper lines
   */
  const onNodeDragEnd = useCallback(() => {
    setHorizontalLines([]);
    setVerticalLines([]);
    setSnappedPosition(null);
  }, []);

  const hasActiveLines = horizontalLines.length > 0 || verticalLines.length > 0;

  return {
    horizontalLines,
    verticalLines,
    hasActiveLines,
    snappedPosition,
    onNodeDrag,
    onNodeDragEnd,
  };
}
