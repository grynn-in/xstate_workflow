import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useUndoRedo } from '../useUndoRedo';

describe('useUndoRedo', () => {
  // Sample workflow state type for testing
  interface TestState {
    nodes: Array<{ id: string; label: string }>;
    edges: Array<{ id: string; source: string; target: string }>;
  }

  const initialState: TestState = {
    nodes: [{ id: 'n1', label: 'Node 1' }],
    edges: [],
  };

  it('should initialize with the provided initial state', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    expect(result.current.state).toEqual(initialState);
  });

  it('should not be able to undo initially', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    expect(result.current.canUndo).toBe(false);
  });

  it('should not be able to redo initially', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    expect(result.current.canRedo).toBe(false);
  });

  it('should update state when setState is called', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const newState: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    act(() => {
      result.current.setState(newState);
    });

    expect(result.current.state).toEqual(newState);
  });

  it('should be able to undo after state change', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const newState: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    act(() => {
      result.current.setState(newState);
    });

    expect(result.current.canUndo).toBe(true);
  });

  it('should restore previous state on undo', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const newState: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    act(() => {
      result.current.setState(newState);
    });

    act(() => {
      result.current.undo();
    });

    expect(result.current.state).toEqual(initialState);
  });

  it('should be able to redo after undo', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const newState: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    act(() => {
      result.current.setState(newState);
    });

    act(() => {
      result.current.undo();
    });

    expect(result.current.canRedo).toBe(true);
  });

  it('should restore undone state on redo', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const newState: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    act(() => {
      result.current.setState(newState);
    });

    act(() => {
      result.current.undo();
    });

    act(() => {
      result.current.redo();
    });

    expect(result.current.state).toEqual(newState);
  });

  it('should clear redo stack when new change is made after undo', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const state1: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    const state2: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n3', label: 'Node 3' }],
      edges: [],
    };

    act(() => {
      result.current.setState(state1);
    });

    act(() => {
      result.current.undo();
    });

    expect(result.current.canRedo).toBe(true);

    act(() => {
      result.current.setState(state2);
    });

    expect(result.current.canRedo).toBe(false);
  });

  it('should handle multiple undo operations', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const state1: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    const state2: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }, { id: 'n3', label: 'Node 3' }],
      edges: [],
    };

    act(() => {
      result.current.setState(state1);
    });

    act(() => {
      result.current.setState(state2);
    });

    expect(result.current.state).toEqual(state2);

    act(() => {
      result.current.undo();
    });

    expect(result.current.state).toEqual(state1);

    act(() => {
      result.current.undo();
    });

    expect(result.current.state).toEqual(initialState);
    expect(result.current.canUndo).toBe(false);
  });

  it('should handle multiple redo operations', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const state1: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    const state2: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }, { id: 'n2', label: 'Node 2' }, { id: 'n3', label: 'Node 3' }],
      edges: [],
    };

    act(() => {
      result.current.setState(state1);
      result.current.setState(state2);
    });

    act(() => {
      result.current.undo();
      result.current.undo();
    });

    act(() => {
      result.current.redo();
    });

    expect(result.current.state).toEqual(state1);

    act(() => {
      result.current.redo();
    });

    expect(result.current.state).toEqual(state2);
    expect(result.current.canRedo).toBe(false);
  });

  it('should respect maxHistorySize option', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState, maxHistorySize: 3 })
    );

    const states: TestState[] = [
      { nodes: [{ id: 'n1', label: '1' }], edges: [] },
      { nodes: [{ id: 'n2', label: '2' }], edges: [] },
      { nodes: [{ id: 'n3', label: '3' }], edges: [] },
      { nodes: [{ id: 'n4', label: '4' }], edges: [] },
      { nodes: [{ id: 'n5', label: '5' }], edges: [] },
    ];

    // Apply all states
    states.forEach((state) => {
      act(() => {
        result.current.setState(state);
      });
    });

    // Should only be able to undo maxHistorySize times (3)
    // Current state is n5, can undo to n4, n3, n2 (3 undos)
    let undoCount = 0;
    while (result.current.canUndo) {
      act(() => {
        result.current.undo();
      });
      undoCount++;
    }

    expect(undoCount).toBe(3);
  });

  it('should provide history length', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    expect(result.current.historyLength).toBe(1);

    act(() => {
      result.current.setState({
        nodes: [{ id: 'n2', label: 'Node 2' }],
        edges: [],
      });
    });

    expect(result.current.historyLength).toBe(2);
  });

  it('should provide current history index', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    expect(result.current.currentIndex).toBe(0);

    act(() => {
      result.current.setState({
        nodes: [{ id: 'n2', label: 'Node 2' }],
        edges: [],
      });
    });

    expect(result.current.currentIndex).toBe(1);

    act(() => {
      result.current.undo();
    });

    expect(result.current.currentIndex).toBe(0);
  });

  it('should support reset to clear history', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    act(() => {
      result.current.setState({
        nodes: [{ id: 'n2', label: 'Node 2' }],
        edges: [],
      });
      result.current.setState({
        nodes: [{ id: 'n3', label: 'Node 3' }],
        edges: [],
      });
    });

    const resetState: TestState = {
      nodes: [{ id: 'reset', label: 'Reset' }],
      edges: [],
    };

    act(() => {
      result.current.reset(resetState);
    });

    expect(result.current.state).toEqual(resetState);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.historyLength).toBe(1);
  });

  it('should call onChange callback when state changes', () => {
    const onChange = vi.fn();
    const { result } = renderHook(() =>
      useUndoRedo({ initialState, onChange })
    );

    const newState: TestState = {
      nodes: [{ id: 'n2', label: 'Node 2' }],
      edges: [],
    };

    act(() => {
      result.current.setState(newState);
    });

    expect(onChange).toHaveBeenCalledWith(newState);
  });

  it('should call onChange on undo', () => {
    const onChange = vi.fn();
    const { result } = renderHook(() =>
      useUndoRedo({ initialState, onChange })
    );

    act(() => {
      result.current.setState({
        nodes: [{ id: 'n2', label: 'Node 2' }],
        edges: [],
      });
    });

    onChange.mockClear();

    act(() => {
      result.current.undo();
    });

    expect(onChange).toHaveBeenCalledWith(initialState);
  });

  it('should do nothing when undo called with empty history', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const stateBefore = result.current.state;

    act(() => {
      result.current.undo();
    });

    expect(result.current.state).toEqual(stateBefore);
  });

  it('should do nothing when redo called with empty future', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const stateBefore = result.current.state;

    act(() => {
      result.current.redo();
    });

    expect(result.current.state).toEqual(stateBefore);
  });

  it('should skip duplicate consecutive states', () => {
    const { result } = renderHook(() =>
      useUndoRedo({ initialState })
    );

    const sameState: TestState = {
      nodes: [{ id: 'n1', label: 'Node 1' }],
      edges: [],
    };

    act(() => {
      result.current.setState(sameState);
    });

    // Should not add duplicate to history
    expect(result.current.historyLength).toBe(1);
    expect(result.current.canUndo).toBe(false);
  });
});
