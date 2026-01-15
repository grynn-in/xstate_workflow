import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCopyPaste } from '../useCopyPaste';
import type { WorkflowNode, WorkflowEdge } from '@xstate-workflow/core';

describe('useCopyPaste', () => {
  // Sample nodes for testing
  const createNode = (id: string, x: number, y: number, label?: string): WorkflowNode => ({
    id,
    type: 'atomic',
    position: { x, y },
    data: {
      label: label || `Node ${id}`,
      xstateType: 'atomic',
    },
  });

  // Sample edges for testing
  const createEdge = (id: string, source: string, target: string): WorkflowEdge => ({
    id,
    source,
    target,
    type: 'transition',
    data: {
      event: 'TRANSITION',
      transitionType: 'event',
    },
  });

  const node1 = createNode('n1', 100, 100, 'Node 1');
  const node2 = createNode('n2', 200, 200, 'Node 2');
  const node3 = createNode('n3', 300, 300, 'Node 3');
  const edge1 = createEdge('e1', 'n1', 'n2');
  const edge2 = createEdge('e2', 'n2', 'n3');

  describe('initialization', () => {
    it('should initialize with empty clipboard', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
        })
      );

      expect(result.current.clipboardNodes).toEqual([]);
      expect(result.current.clipboardEdges).toEqual([]);
      expect(result.current.hasClipboardContent).toBe(false);
    });

    it('should not be able to paste initially', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
        })
      );

      expect(result.current.canPaste).toBe(false);
    });
  });

  describe('copy', () => {
    it('should copy a single selected node', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: ['n1'],
        })
      );

      act(() => {
        result.current.copy();
      });

      expect(result.current.clipboardNodes).toHaveLength(1);
      expect(result.current.clipboardNodes[0].id).toBe('n1');
      expect(result.current.hasClipboardContent).toBe(true);
    });

    it('should copy multiple selected nodes', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2, node3],
          edges: [edge1, edge2],
          selectedNodeIds: ['n1', 'n2'],
        })
      );

      act(() => {
        result.current.copy();
      });

      expect(result.current.clipboardNodes).toHaveLength(2);
      expect(result.current.clipboardNodes.map((n) => n.id)).toContain('n1');
      expect(result.current.clipboardNodes.map((n) => n.id)).toContain('n2');
    });

    it('should copy edges between selected nodes', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2, node3],
          edges: [edge1, edge2],
          selectedNodeIds: ['n1', 'n2'],
        })
      );

      act(() => {
        result.current.copy();
      });

      // edge1 connects n1->n2 (both selected), should be copied
      // edge2 connects n2->n3 (n3 not selected), should NOT be copied
      expect(result.current.clipboardEdges).toHaveLength(1);
      expect(result.current.clipboardEdges[0].id).toBe('e1');
    });

    it('should not copy edges if only one endpoint is selected', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: ['n1'], // Only n1 selected, not n2
        })
      );

      act(() => {
        result.current.copy();
      });

      expect(result.current.clipboardEdges).toHaveLength(0);
    });

    it('should do nothing if no nodes are selected', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: [],
        })
      );

      act(() => {
        result.current.copy();
      });

      expect(result.current.clipboardNodes).toHaveLength(0);
      expect(result.current.hasClipboardContent).toBe(false);
    });

    it('should call onCopy callback after copying', () => {
      const onCopy = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: ['n1'],
          onCopy,
        })
      );

      act(() => {
        result.current.copy();
      });

      expect(onCopy).toHaveBeenCalledWith(
        expect.arrayContaining([expect.objectContaining({ id: 'n1' })]),
        expect.any(Array)
      );
    });
  });

  describe('paste', () => {
    it('should paste copied nodes with offset position', () => {
      const onPaste = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: ['n1'],
          onPaste,
          pasteOffset: { x: 50, y: 50 },
        })
      );

      // Copy first
      act(() => {
        result.current.copy();
      });

      // Then paste
      act(() => {
        result.current.paste();
      });

      expect(onPaste).toHaveBeenCalled();
      const [pastedNodes] = onPaste.mock.calls[0];

      // Pasted node should have different ID and offset position
      expect(pastedNodes[0].id).not.toBe('n1');
      expect(pastedNodes[0].position.x).toBe(150); // 100 + 50
      expect(pastedNodes[0].position.y).toBe(150); // 100 + 50
    });

    it('should generate new IDs for pasted nodes', () => {
      const onPaste = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: ['n1', 'n2'],
          onPaste,
        })
      );

      act(() => {
        result.current.copy();
      });

      act(() => {
        result.current.paste();
      });

      const [pastedNodes] = onPaste.mock.calls[0];
      expect(pastedNodes[0].id).not.toBe('n1');
      expect(pastedNodes[1].id).not.toBe('n2');
      // Both should have unique new IDs
      expect(pastedNodes[0].id).not.toBe(pastedNodes[1].id);
    });

    it('should update edge references to new node IDs', () => {
      const onPaste = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: ['n1', 'n2'],
          onPaste,
        })
      );

      act(() => {
        result.current.copy();
      });

      act(() => {
        result.current.paste();
      });

      const [pastedNodes, pastedEdges] = onPaste.mock.calls[0];
      const newN1Id = pastedNodes.find((n: WorkflowNode) => n.data?.label === 'Node 1')?.id;
      const newN2Id = pastedNodes.find((n: WorkflowNode) => n.data?.label === 'Node 2')?.id;

      // Edge should reference the new node IDs
      expect(pastedEdges[0].source).toBe(newN1Id);
      expect(pastedEdges[0].target).toBe(newN2Id);
      expect(pastedEdges[0].id).not.toBe('e1');
    });

    it('should do nothing if clipboard is empty', () => {
      const onPaste = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: [],
          onPaste,
        })
      );

      act(() => {
        result.current.paste();
      });

      expect(onPaste).not.toHaveBeenCalled();
    });

    it('should allow multiple pastes from same copy', () => {
      const onPaste = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1],
          edges: [],
          selectedNodeIds: ['n1'],
          onPaste,
          pasteOffset: { x: 50, y: 50 },
        })
      );

      act(() => {
        result.current.copy();
      });

      // First paste
      act(() => {
        result.current.paste();
      });

      // Second paste
      act(() => {
        result.current.paste();
      });

      expect(onPaste).toHaveBeenCalledTimes(2);

      // Each paste should have unique IDs
      const firstPasteNodes = onPaste.mock.calls[0][0];
      const secondPasteNodes = onPaste.mock.calls[1][0];
      expect(firstPasteNodes[0].id).not.toBe(secondPasteNodes[0].id);
    });

    it('should paste at specified position when provided', () => {
      const onPaste = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: ['n1', 'n2'],
          onPaste,
        })
      );

      act(() => {
        result.current.copy();
      });

      // Paste at specific position
      act(() => {
        result.current.pasteAt({ x: 500, y: 500 });
      });

      const [pastedNodes] = onPaste.mock.calls[0];
      // Nodes should be positioned relative to the paste point
      // The first node's position becomes the reference
      expect(pastedNodes[0].position.x).toBe(500);
      expect(pastedNodes[0].position.y).toBe(500);
      // Second node should maintain relative offset
      expect(pastedNodes[1].position.x).toBe(600); // 500 + (200-100)
      expect(pastedNodes[1].position.y).toBe(600); // 500 + (200-100)
    });
  });

  describe('cut', () => {
    it('should copy and call onCut callback', () => {
      const onCut = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: ['n1'],
          onCut,
        })
      );

      act(() => {
        result.current.cut();
      });

      expect(result.current.clipboardNodes).toHaveLength(1);
      expect(onCut).toHaveBeenCalledWith(['n1']);
    });

    it('should include edges for deletion when cutting', () => {
      const onCut = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2, node3],
          edges: [edge1, edge2],
          selectedNodeIds: ['n2'],
          onCut,
        })
      );

      act(() => {
        result.current.cut();
      });

      // onCut should be called with node IDs to delete
      // The caller is responsible for also deleting connected edges
      expect(onCut).toHaveBeenCalledWith(['n2']);
    });

    it('should do nothing if no nodes are selected', () => {
      const onCut = vi.fn();
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edge1],
          selectedNodeIds: [],
          onCut,
        })
      );

      act(() => {
        result.current.cut();
      });

      expect(onCut).not.toHaveBeenCalled();
      expect(result.current.clipboardNodes).toHaveLength(0);
    });
  });

  describe('clipboard state', () => {
    it('should update canPaste when clipboard has content', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1],
          edges: [],
          selectedNodeIds: ['n1'],
        })
      );

      expect(result.current.canPaste).toBe(false);

      act(() => {
        result.current.copy();
      });

      expect(result.current.canPaste).toBe(true);
    });

    it('should clear clipboard', () => {
      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1],
          edges: [],
          selectedNodeIds: ['n1'],
        })
      );

      act(() => {
        result.current.copy();
      });

      expect(result.current.hasClipboardContent).toBe(true);

      act(() => {
        result.current.clearClipboard();
      });

      expect(result.current.hasClipboardContent).toBe(false);
      expect(result.current.canPaste).toBe(false);
    });
  });

  describe('preserving node properties', () => {
    it('should preserve node data when copying', () => {
      const nodeWithData = createNode('n1', 100, 100, 'Custom Label');
      nodeWithData.data = {
        ...nodeWithData.data,
        isInitial: true,
        description: 'Test description',
      };

      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [nodeWithData],
          edges: [],
          selectedNodeIds: ['n1'],
        })
      );

      act(() => {
        result.current.copy();
      });

      expect(result.current.clipboardNodes[0].data?.label).toBe('Custom Label');
      expect(result.current.clipboardNodes[0].data?.description).toBe('Test description');
    });

    it('should NOT preserve isInitial flag when pasting', () => {
      const onPaste = vi.fn();
      const initialNode = createNode('n1', 100, 100, 'Initial');
      initialNode.data = { ...initialNode.data, isInitial: true };

      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [initialNode],
          edges: [],
          selectedNodeIds: ['n1'],
          onPaste,
        })
      );

      act(() => {
        result.current.copy();
      });

      act(() => {
        result.current.paste();
      });

      const [pastedNodes] = onPaste.mock.calls[0];
      // Pasted node should not be initial (only one initial node allowed)
      expect(pastedNodes[0].data?.isInitial).toBe(false);
    });

    it('should preserve edge data when copying', () => {
      const edgeWithData: WorkflowEdge = {
        ...edge1,
        data: {
          event: 'CUSTOM_EVENT',
          transitionType: 'event',
          guard: 'someGuard',
        },
      };

      const { result } = renderHook(() =>
        useCopyPaste({
          nodes: [node1, node2],
          edges: [edgeWithData],
          selectedNodeIds: ['n1', 'n2'],
        })
      );

      act(() => {
        result.current.copy();
      });

      expect(result.current.clipboardEdges[0].data?.event).toBe('CUSTOM_EVENT');
      expect(result.current.clipboardEdges[0].data?.guard).toBe('someGuard');
    });
  });

  describe('selection updates', () => {
    it('should handle selection changes', () => {
      const { result, rerender } = renderHook(
        ({ selectedNodeIds }) =>
          useCopyPaste({
            nodes: [node1, node2],
            edges: [edge1],
            selectedNodeIds,
          }),
        { initialProps: { selectedNodeIds: ['n1'] } }
      );

      act(() => {
        result.current.copy();
      });

      expect(result.current.clipboardNodes).toHaveLength(1);
      expect(result.current.clipboardNodes[0].id).toBe('n1');

      // Change selection and copy again
      rerender({ selectedNodeIds: ['n2'] });

      act(() => {
        result.current.copy();
      });

      expect(result.current.clipboardNodes).toHaveLength(1);
      expect(result.current.clipboardNodes[0].id).toBe('n2');
    });
  });
});
