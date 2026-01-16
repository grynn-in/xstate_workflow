import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useHelperLines } from '../useHelperLines';

describe('useHelperLines', () => {
  // Helper to create a node with position and dimensions
  const createNode = (
    id: string,
    x: number,
    y: number,
    width = 150,
    height = 40
  ) => ({
    id,
    position: { x, y },
    measured: { width, height },
  });

  describe('initialization', () => {
    it('should initialize with no helper lines', () => {
      const { result } = renderHook(() =>
        useHelperLines({
          nodes: [createNode('n1', 100, 100)],
        })
      );

      expect(result.current.horizontalLines).toEqual([]);
      expect(result.current.verticalLines).toEqual([]);
      expect(result.current.hasActiveLines).toBe(false);
    });
  });

  describe('horizontal alignment detection', () => {
    it('should detect top edge alignment', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 300, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Simulate dragging n2 to align its top with n1's top
      act(() => {
        result.current.onNodeDrag('n2', { x: 300, y: 100 });
      });

      expect(result.current.horizontalLines).toContainEqual(
        expect.objectContaining({ y: 100, type: 'top' })
      );
    });

    it('should detect center horizontal alignment', () => {
      const nodes = [
        createNode('n1', 100, 100, 150, 40), // center Y = 120
        createNode('n2', 300, 200, 150, 40),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n2 so its center aligns with n1's center (y=100 means center at 120)
      act(() => {
        result.current.onNodeDrag('n2', { x: 300, y: 100 });
      });

      expect(result.current.horizontalLines).toContainEqual(
        expect.objectContaining({ y: 120, type: 'center' })
      );
    });

    it('should detect bottom edge alignment', () => {
      const nodes = [
        createNode('n1', 100, 100, 150, 40), // bottom = 140
        createNode('n2', 300, 200, 150, 40),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n2 so its bottom aligns with n1's bottom
      act(() => {
        result.current.onNodeDrag('n2', { x: 300, y: 100 });
      });

      expect(result.current.horizontalLines).toContainEqual(
        expect.objectContaining({ y: 140, type: 'bottom' })
      );
    });
  });

  describe('vertical alignment detection', () => {
    it('should detect left edge alignment', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 300),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n2 to align its left with n1's left
      act(() => {
        result.current.onNodeDrag('n2', { x: 100, y: 300 });
      });

      expect(result.current.verticalLines).toContainEqual(
        expect.objectContaining({ x: 100, type: 'left' })
      );
    });

    it('should detect center vertical alignment', () => {
      const nodes = [
        createNode('n1', 100, 100, 150, 40), // center X = 175
        createNode('n2', 200, 300, 150, 40),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n2 so its center aligns with n1's center
      act(() => {
        result.current.onNodeDrag('n2', { x: 100, y: 300 });
      });

      expect(result.current.verticalLines).toContainEqual(
        expect.objectContaining({ x: 175, type: 'center' })
      );
    });

    it('should detect right edge alignment', () => {
      const nodes = [
        createNode('n1', 100, 100, 150, 40), // right = 250
        createNode('n2', 200, 300, 150, 40),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n2 so its right aligns with n1's right
      act(() => {
        result.current.onNodeDrag('n2', { x: 100, y: 300 });
      });

      expect(result.current.verticalLines).toContainEqual(
        expect.objectContaining({ x: 250, type: 'right' })
      );
    });
  });

  describe('threshold behavior', () => {
    it('should detect alignment within threshold', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 10 })
      );

      // Drag n2 to be 8px away from alignment (within threshold of 10)
      act(() => {
        result.current.onNodeDrag('n2', { x: 108, y: 200 });
      });

      expect(result.current.verticalLines.length).toBeGreaterThan(0);
    });

    it('should NOT detect alignment outside threshold', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n2 to be 20px away from alignment (outside threshold of 5)
      act(() => {
        result.current.onNodeDrag('n2', { x: 120, y: 200 });
      });

      // Should not have lines for left edge alignment
      expect(result.current.verticalLines.filter(l => l.type === 'left')).toHaveLength(0);
    });

    it('should use default threshold of 5 when not specified', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes })
      );

      // Drag n2 to be 4px away (within default threshold of 5)
      act(() => {
        result.current.onNodeDrag('n2', { x: 104, y: 200 });
      });

      expect(result.current.verticalLines.length).toBeGreaterThan(0);
    });
  });

  describe('snapping', () => {
    it('should return snapped position when enabled', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 10, enableSnapping: true })
      );

      // Drag n2 close to alignment
      act(() => {
        result.current.onNodeDrag('n2', { x: 105, y: 200 });
      });

      // Should snap to exact alignment
      expect(result.current.snappedPosition).toEqual({ x: 100, y: 200 });
    });

    it('should NOT snap when disabled', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 10, enableSnapping: false })
      );

      act(() => {
        result.current.onNodeDrag('n2', { x: 105, y: 200 });
      });

      expect(result.current.snappedPosition).toBeNull();
    });

    it('should snap to both axes independently', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 10, enableSnapping: true })
      );

      // Drag n2 close to alignment on both axes
      act(() => {
        result.current.onNodeDrag('n2', { x: 103, y: 102 });
      });

      expect(result.current.snappedPosition).toEqual({ x: 100, y: 100 });
    });
  });

  describe('drag end behavior', () => {
    it('should clear helper lines on drag end', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Start dragging with alignment
      act(() => {
        result.current.onNodeDrag('n2', { x: 100, y: 200 });
      });

      expect(result.current.hasActiveLines).toBe(true);

      // End drag
      act(() => {
        result.current.onNodeDragEnd();
      });

      expect(result.current.horizontalLines).toEqual([]);
      expect(result.current.verticalLines).toEqual([]);
      expect(result.current.hasActiveLines).toBe(false);
    });

    it('should clear snapped position on drag end', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 10, enableSnapping: true })
      );

      act(() => {
        result.current.onNodeDrag('n2', { x: 105, y: 200 });
      });

      expect(result.current.snappedPosition).not.toBeNull();

      act(() => {
        result.current.onNodeDragEnd();
      });

      expect(result.current.snappedPosition).toBeNull();
    });
  });

  describe('multiple node alignment', () => {
    it('should detect alignment with multiple nodes', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 100, 300), // Same X as n1
        createNode('n3', 400, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n3 to align with n1 and n2's left edge
      act(() => {
        result.current.onNodeDrag('n3', { x: 100, y: 200 });
      });

      // Should show vertical line at x=100
      expect(result.current.verticalLines).toContainEqual(
        expect.objectContaining({ x: 100, type: 'left' })
      );
    });

    it('should not compare node with itself', () => {
      const nodes = [
        createNode('n1', 100, 100),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n1 - should not create alignment lines with itself
      act(() => {
        result.current.onNodeDrag('n1', { x: 100, y: 100 });
      });

      expect(result.current.horizontalLines).toEqual([]);
      expect(result.current.verticalLines).toEqual([]);
    });
  });

  describe('line extent calculation', () => {
    it('should calculate horizontal line extent across aligned nodes', () => {
      const nodes = [
        createNode('n1', 100, 100, 150, 40),
        createNode('n2', 400, 200, 150, 40),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n2 to align top
      act(() => {
        result.current.onNodeDrag('n2', { x: 400, y: 100 });
      });

      const topLine = result.current.horizontalLines.find(l => l.type === 'top');
      expect(topLine).toBeDefined();
      // Line should span from left of n1 to right of n2
      expect(topLine!.x1).toBeLessThanOrEqual(100);
      expect(topLine!.x2).toBeGreaterThanOrEqual(550); // 400 + 150
    });

    it('should calculate vertical line extent across aligned nodes', () => {
      const nodes = [
        createNode('n1', 100, 100, 150, 40),
        createNode('n2', 200, 400, 150, 40),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5 })
      );

      // Drag n2 to align left
      act(() => {
        result.current.onNodeDrag('n2', { x: 100, y: 400 });
      });

      const leftLine = result.current.verticalLines.find(l => l.type === 'left');
      expect(leftLine).toBeDefined();
      // Line should span from top of n1 to bottom of n2
      expect(leftLine!.y1).toBeLessThanOrEqual(100);
      expect(leftLine!.y2).toBeGreaterThanOrEqual(440); // 400 + 40
    });
  });

  describe('nodes without measurements', () => {
    it('should handle nodes without measured dimensions', () => {
      const nodeWithoutMeasured = {
        id: 'n1',
        position: { x: 100, y: 100 },
        // No measured property
      };

      const nodeWithMeasured = createNode('n2', 200, 200);

      const { result } = renderHook(() =>
        useHelperLines({
          nodes: [nodeWithoutMeasured, nodeWithMeasured],
          threshold: 5,
          defaultNodeWidth: 150,
          defaultNodeHeight: 40,
        })
      );

      // Should not throw and should use default dimensions
      act(() => {
        result.current.onNodeDrag('n2', { x: 100, y: 200 });
      });

      expect(result.current.verticalLines.length).toBeGreaterThan(0);
    });
  });

  describe('disabled state', () => {
    it('should not detect lines when disabled', () => {
      const nodes = [
        createNode('n1', 100, 100),
        createNode('n2', 200, 200),
      ];

      const { result } = renderHook(() =>
        useHelperLines({ nodes, threshold: 5, enabled: false })
      );

      act(() => {
        result.current.onNodeDrag('n2', { x: 100, y: 100 });
      });

      expect(result.current.horizontalLines).toEqual([]);
      expect(result.current.verticalLines).toEqual([]);
    });
  });
});
