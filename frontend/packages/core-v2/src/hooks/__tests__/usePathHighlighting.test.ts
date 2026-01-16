import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { usePathHighlighting } from '../usePathHighlighting';

describe('usePathHighlighting', () => {
  const sampleEdges = [
    { id: 'e1', source: 'start', target: 'pending' },
    { id: 'e2', source: 'pending', target: 'approved' },
    { id: 'e3', source: 'pending', target: 'rejected' },
    { id: 'e4', source: 'approved', target: 'completed' },
  ];

  const sampleNodes = [
    { id: 'start', data: { label: 'Start' } },
    { id: 'pending', data: { label: 'Pending' } },
    { id: 'approved', data: { label: 'Approved' } },
    { id: 'rejected', data: { label: 'Rejected' } },
    { id: 'completed', data: { label: 'Completed' } },
  ];

  it('should return empty path data when no transition log', () => {
    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog: [],
        currentState: 'start',
      })
    );

    expect(result.current.visitedEdgeIds).toEqual([]);
    expect(result.current.edgeSequenceMap.size).toBe(0);
  });

  it('should mark edges as visited based on transition log', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'pending',
      })
    );

    expect(result.current.visitedEdgeIds).toContain('e1');
    expect(result.current.visitedEdgeIds).not.toContain('e2');
  });

  it('should assign sequence numbers to visited edges', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
      { from_state: 'pending', to_state: 'approved', event: 'APPROVE' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'approved',
      })
    );

    expect(result.current.edgeSequenceMap.get('e1')).toBe(1);
    expect(result.current.edgeSequenceMap.get('e2')).toBe(2);
  });

  it('should identify unvisited edges', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'pending',
      })
    );

    expect(result.current.unvisitedEdgeIds).toContain('e2');
    expect(result.current.unvisitedEdgeIds).toContain('e3');
    expect(result.current.unvisitedEdgeIds).toContain('e4');
    expect(result.current.unvisitedEdgeIds).not.toContain('e1');
  });

  it('should provide isEdgeVisited helper function', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'pending',
      })
    );

    expect(result.current.isEdgeVisited('e1')).toBe(true);
    expect(result.current.isEdgeVisited('e2')).toBe(false);
  });

  it('should provide getEdgeSequence helper function', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
      { from_state: 'pending', to_state: 'approved', event: 'APPROVE' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'approved',
      })
    );

    expect(result.current.getEdgeSequence('e1')).toBe(1);
    expect(result.current.getEdgeSequence('e2')).toBe(2);
    expect(result.current.getEdgeSequence('e3')).toBeUndefined();
  });

  it('should handle transitions with state names matching node labels', () => {
    const transitionLog = [
      { from_state: 'Start', to_state: 'Pending', event: 'SUBMIT' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'pending',
      })
    );

    // Should match by label (case-insensitive) or id
    expect(result.current.visitedEdgeIds).toContain('e1');
  });

  it('should handle multiple transitions through same edge', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
      { from_state: 'pending', to_state: 'start', event: 'RESET' }, // Go back
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' }, // Same edge again
    ];

    // Add reverse edge for this test
    const edgesWithReverse = [
      ...sampleEdges,
      { id: 'e5', source: 'pending', target: 'start' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: edgesWithReverse,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'pending',
      })
    );

    // e1 should have sequence 1 (first time) or 3 (last time) depending on strategy
    // Using "last occurrence" strategy for sequence numbers
    expect(result.current.getEdgeSequence('e1')).toBe(3);
    expect(result.current.getEdgeSequence('e5')).toBe(2);
  });

  it('should return visited node IDs', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
      { from_state: 'pending', to_state: 'approved', event: 'APPROVE' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'approved',
      })
    );

    expect(result.current.visitedNodeIds).toContain('start');
    expect(result.current.visitedNodeIds).toContain('pending');
    expect(result.current.visitedNodeIds).toContain('approved');
    expect(result.current.visitedNodeIds).not.toContain('rejected');
  });

  it('should identify current edge (last transition)', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
      { from_state: 'pending', to_state: 'approved', event: 'APPROVE' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'approved',
      })
    );

    expect(result.current.currentEdgeId).toBe('e2');
  });

  it('should return undefined currentEdgeId when no transitions', () => {
    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog: [],
        currentState: 'start',
      })
    );

    expect(result.current.currentEdgeId).toBeUndefined();
  });

  it('should handle empty edges array', () => {
    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: [],
        nodes: sampleNodes,
        transitionLog: [{ from_state: 'start', to_state: 'pending', event: 'SUBMIT' }],
        currentState: 'pending',
      })
    );

    expect(result.current.visitedEdgeIds).toEqual([]);
    expect(result.current.edgeSequenceMap.size).toBe(0);
  });

  it('should provide path statistics', () => {
    const transitionLog = [
      { from_state: 'start', to_state: 'pending', event: 'SUBMIT' },
      { from_state: 'pending', to_state: 'approved', event: 'APPROVE' },
    ];

    const { result } = renderHook(() =>
      usePathHighlighting({
        edges: sampleEdges,
        nodes: sampleNodes,
        transitionLog,
        currentState: 'approved',
      })
    );

    expect(result.current.pathStats.totalTransitions).toBe(2);
    expect(result.current.pathStats.uniqueEdgesVisited).toBe(2);
    expect(result.current.pathStats.uniqueNodesVisited).toBe(3);
  });
});
