import { useCallback, useState, useMemo } from 'react';
import type { WorkflowNode, WorkflowEdge } from '@xstate-workflow/core';

/**
 * Position type for node placement
 */
interface Position {
  x: number;
  y: number;
}

/**
 * Options for useCopyPaste hook
 */
export interface UseCopyPasteOptions {
  /** All nodes in the workflow */
  nodes: WorkflowNode[];
  /** All edges in the workflow */
  edges: WorkflowEdge[];
  /** IDs of currently selected nodes */
  selectedNodeIds?: string[];
  /** Offset for paste position (default: { x: 50, y: 50 }) */
  pasteOffset?: Position;
  /** Callback when nodes are copied */
  onCopy?: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
  /** Callback when nodes are pasted - receives new nodes and edges to add */
  onPaste?: (nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
  /** Callback when nodes are cut - receives node IDs to delete */
  onCut?: (nodeIds: string[]) => void;
}

/**
 * Return type for useCopyPaste hook
 */
export interface UseCopyPasteReturn {
  /** Copy currently selected nodes and their connecting edges */
  copy: () => void;
  /** Paste clipboard contents with default offset */
  paste: () => void;
  /** Paste clipboard contents at specific position */
  pasteAt: (position: Position) => void;
  /** Cut (copy + delete) currently selected nodes */
  cut: () => void;
  /** Clear the clipboard */
  clearClipboard: () => void;
  /** Nodes currently in clipboard */
  clipboardNodes: WorkflowNode[];
  /** Edges currently in clipboard */
  clipboardEdges: WorkflowEdge[];
  /** Whether clipboard has content */
  hasClipboardContent: boolean;
  /** Whether paste is possible */
  canPaste: boolean;
}

/**
 * Generate a unique ID for pasted elements
 */
let pasteIdCounter = 0;
function generatePasteId(prefix: string): string {
  return `${prefix}_paste_${Date.now()}_${++pasteIdCounter}`;
}

/**
 * Deep clone an object
 */
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Hook for copy/paste functionality in the workflow builder.
 *
 * Supports:
 * - Copying selected nodes and edges between them
 * - Pasting with automatic ID generation
 * - Pasting at specific positions or with offset
 * - Cut (copy + delete)
 * - Preserving node/edge data (except isInitial flag)
 *
 * @example
 * ```tsx
 * const {
 *   copy,
 *   paste,
 *   cut,
 *   canPaste,
 * } = useCopyPaste({
 *   nodes,
 *   edges,
 *   selectedNodeIds: [selectedNode?.id].filter(Boolean),
 *   onPaste: (newNodes, newEdges) => {
 *     setNodes([...nodes, ...newNodes]);
 *     setEdges([...edges, ...newEdges]);
 *   },
 *   onCut: (nodeIds) => {
 *     setNodes(nodes.filter(n => !nodeIds.includes(n.id)));
 *     setEdges(edges.filter(e => !nodeIds.includes(e.source) && !nodeIds.includes(e.target)));
 *   },
 * });
 *
 * // Keyboard shortcuts
 * useEffect(() => {
 *   const handleKeyDown = (e) => {
 *     if (e.ctrlKey && e.key === 'c') copy();
 *     if (e.ctrlKey && e.key === 'v') paste();
 *     if (e.ctrlKey && e.key === 'x') cut();
 *   };
 *   window.addEventListener('keydown', handleKeyDown);
 *   return () => window.removeEventListener('keydown', handleKeyDown);
 * }, [copy, paste, cut]);
 * ```
 */
export function useCopyPaste(options: UseCopyPasteOptions): UseCopyPasteReturn {
  const {
    nodes,
    edges,
    selectedNodeIds = [],
    pasteOffset = { x: 50, y: 50 },
    onCopy,
    onPaste,
    onCut,
  } = options;

  // Clipboard state
  const [clipboardNodes, setClipboardNodes] = useState<WorkflowNode[]>([]);
  const [clipboardEdges, setClipboardEdges] = useState<WorkflowEdge[]>([]);

  // Computed state
  const hasClipboardContent = clipboardNodes.length > 0;
  const canPaste = hasClipboardContent;

  /**
   * Copy selected nodes and edges between them to clipboard
   */
  const copy = useCallback(() => {
    if (selectedNodeIds.length === 0) {
      return;
    }

    // Find selected nodes
    const selectedNodes = nodes.filter((n) => selectedNodeIds.includes(n.id));
    if (selectedNodes.length === 0) {
      return;
    }

    // Find edges where BOTH source and target are in selection
    const selectedEdges = edges.filter(
      (e) => selectedNodeIds.includes(e.source) && selectedNodeIds.includes(e.target)
    );

    // Deep clone to avoid reference issues
    const copiedNodes = deepClone(selectedNodes);
    const copiedEdges = deepClone(selectedEdges);

    setClipboardNodes(copiedNodes);
    setClipboardEdges(copiedEdges);

    onCopy?.(copiedNodes, copiedEdges);
  }, [nodes, edges, selectedNodeIds, onCopy]);

  /**
   * Create new nodes and edges with unique IDs and updated positions
   */
  const createPastedElements = useCallback(
    (targetPosition?: Position): { nodes: WorkflowNode[]; edges: WorkflowEdge[] } => {
      if (clipboardNodes.length === 0) {
        return { nodes: [], edges: [] };
      }

      // Create ID mapping for nodes (old ID -> new ID)
      const idMap = new Map<string, string>();
      clipboardNodes.forEach((node) => {
        idMap.set(node.id, generatePasteId('node'));
      });

      // Calculate position offset
      // If targetPosition is provided, use it as the base for the first node
      // Otherwise use pasteOffset from original positions
      let offsetX = pasteOffset.x;
      let offsetY = pasteOffset.y;

      if (targetPosition && clipboardNodes.length > 0) {
        // Find the minimum position (top-left corner of selection)
        const minX = Math.min(...clipboardNodes.map((n) => n.position.x));
        const minY = Math.min(...clipboardNodes.map((n) => n.position.y));
        offsetX = targetPosition.x - minX;
        offsetY = targetPosition.y - minY;
      }

      // Create new nodes with new IDs and offset positions
      const newNodes: WorkflowNode[] = clipboardNodes.map((node) => ({
        ...deepClone(node),
        id: idMap.get(node.id)!,
        position: {
          x: node.position.x + offsetX,
          y: node.position.y + offsetY,
        },
        data: {
          ...node.data,
          // Never copy isInitial flag - only one initial state allowed
          isInitial: false,
        },
      }));

      // Create new edges with new IDs and updated source/target references
      const newEdges: WorkflowEdge[] = clipboardEdges.map((edge) => ({
        ...deepClone(edge),
        id: generatePasteId('edge'),
        source: idMap.get(edge.source)!,
        target: idMap.get(edge.target)!,
      }));

      return { nodes: newNodes, edges: newEdges };
    },
    [clipboardNodes, clipboardEdges, pasteOffset]
  );

  /**
   * Paste clipboard contents with default offset
   */
  const paste = useCallback(() => {
    if (!canPaste) {
      return;
    }

    const { nodes: newNodes, edges: newEdges } = createPastedElements();
    onPaste?.(newNodes, newEdges);
  }, [canPaste, createPastedElements, onPaste]);

  /**
   * Paste clipboard contents at specific position
   */
  const pasteAt = useCallback(
    (position: Position) => {
      if (!canPaste) {
        return;
      }

      const { nodes: newNodes, edges: newEdges } = createPastedElements(position);
      onPaste?.(newNodes, newEdges);
    },
    [canPaste, createPastedElements, onPaste]
  );

  /**
   * Cut (copy + delete) selected nodes
   */
  const cut = useCallback(() => {
    if (selectedNodeIds.length === 0) {
      return;
    }

    // First copy to clipboard
    copy();

    // Then notify parent to delete
    onCut?.(selectedNodeIds);
  }, [selectedNodeIds, copy, onCut]);

  /**
   * Clear the clipboard
   */
  const clearClipboard = useCallback(() => {
    setClipboardNodes([]);
    setClipboardEdges([]);
  }, []);

  return {
    copy,
    paste,
    pasteAt,
    cut,
    clearClipboard,
    clipboardNodes,
    clipboardEdges,
    hasClipboardContent,
    canPaste,
  };
}
