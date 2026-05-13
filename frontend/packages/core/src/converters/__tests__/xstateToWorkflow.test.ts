import { describe, it, expect, beforeEach } from 'vitest';
import { xstateToWorkflow } from '../xstateToWorkflow';
import type { XStateMachineConfig } from '../../types';

describe('xstateToWorkflow', () => {
  describe('basic conversion', () => {
    it('should convert a simple two-state machine', () => {
      const xstate: XStateMachineConfig = {
        id: 'simple',
        version: '1',
        initial: 'idle',
        states: {
          idle: {
            on: { START: 'running' },
          },
          running: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      expect(result.id).toBe('simple');
      expect(result.nodes).toHaveLength(2);
      expect(result.edges).toHaveLength(1);

      const idleNode = result.nodes.find((n) => n.data.label === 'idle');
      const runningNode = result.nodes.find((n) => n.data.label === 'running');

      expect(idleNode?.data.isInitial).toBe(true);
      expect(runningNode?.data.isInitial).toBe(false);
    });

    it('should preserve context', () => {
      const xstate: XStateMachineConfig = {
        id: 'with-context',
        version: '1',
        initial: 'idle',
        context: { count: 0, items: [] },
        states: {
          idle: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      expect(result.context).toEqual({ count: 0, items: [] });
    });

    it('should parse version as integer', () => {
      const xstate: XStateMachineConfig = {
        id: 'versioned',
        version: '5',
        initial: 'start',
        states: { start: {} },
      };

      const result = xstateToWorkflow(xstate);

      expect(result.version).toBe(5);
    });
  });

  describe('state types', () => {
    it('should identify final states', () => {
      const xstate: XStateMachineConfig = {
        id: 'with-final',
        version: '1',
        initial: 'active',
        states: {
          active: { on: { DONE: 'completed' } },
          completed: { type: 'final' },
        },
      };

      const result = xstateToWorkflow(xstate);

      const completedNode = result.nodes.find((n) => n.data.label === 'completed');
      expect(completedNode?.data.xstateType).toBe('final');
      expect(completedNode?.type).toBe('final');
    });

    it('should identify parallel states', () => {
      const xstate: XStateMachineConfig = {
        id: 'with-parallel',
        version: '1',
        initial: 'processing',
        states: {
          processing: {
            type: 'parallel',
            states: {
              upload: { initial: 'pending', states: { pending: {}, done: {} } },
              validation: { initial: 'pending', states: { pending: {}, done: {} } },
            },
          },
        },
      };

      const result = xstateToWorkflow(xstate);

      const processingNode = result.nodes.find((n) => n.data.label === 'processing');
      expect(processingNode?.data.xstateType).toBe('parallel');
    });

    it('should identify history states', () => {
      const xstate: XStateMachineConfig = {
        id: 'with-history',
        version: '1',
        initial: 'active',
        states: {
          active: {},
          hist: { type: 'history', history: 'deep' },
        },
      };

      const result = xstateToWorkflow(xstate);

      const histNode = result.nodes.find((n) => n.data.label === 'hist');
      expect(histNode?.data.xstateType).toBe('history');
      expect(histNode?.data.historyType).toBe('deep');
    });

    it('should identify compound states (states with children)', () => {
      const xstate: XStateMachineConfig = {
        id: 'compound',
        version: '1',
        initial: 'review',
        states: {
          review: {
            initial: 'technical',
            states: {
              technical: {},
              business: {},
            },
          },
        },
      };

      const result = xstateToWorkflow(xstate);

      const reviewNode = result.nodes.find((n) => n.data.label === 'review');
      expect(reviewNode?.data.xstateType).toBe('compound');
      expect(reviewNode?.data.initialChild).toBe('technical');
    });
  });

  describe('entry and exit actions', () => {
    it('should convert entry actions from string', () => {
      const xstate: XStateMachineConfig = {
        id: 'with-entry',
        version: '1',
        initial: 'active',
        states: {
          active: { entry: 'logEntry' },
        },
      };

      const result = xstateToWorkflow(xstate);

      const activeNode = result.nodes.find((n) => n.data.label === 'active');
      expect(activeNode?.data.entryActions).toEqual(['logEntry']);
    });

    it('should convert entry actions from array', () => {
      const xstate: XStateMachineConfig = {
        id: 'with-entry-array',
        version: '1',
        initial: 'active',
        states: {
          active: { entry: ['logEntry', 'sendNotification'] },
        },
      };

      const result = xstateToWorkflow(xstate);

      const activeNode = result.nodes.find((n) => n.data.label === 'active');
      expect(activeNode?.data.entryActions).toEqual(['logEntry', 'sendNotification']);
    });

    it('should convert exit actions', () => {
      const xstate: XStateMachineConfig = {
        id: 'with-exit',
        version: '1',
        initial: 'active',
        states: {
          active: { exit: ['cleanup', 'persist'] },
        },
      };

      const result = xstateToWorkflow(xstate);

      const activeNode = result.nodes.find((n) => n.data.label === 'active');
      expect(activeNode?.data.exitActions).toEqual(['cleanup', 'persist']);
    });
  });

  describe('event transitions', () => {
    it('should convert simple string transitions', () => {
      const xstate: XStateMachineConfig = {
        id: 'simple-transitions',
        version: '1',
        initial: 'idle',
        states: {
          idle: { on: { START: 'running' } },
          running: { on: { STOP: 'idle' } },
        },
      };

      const result = xstateToWorkflow(xstate);

      expect(result.edges).toHaveLength(2);

      const startEdge = result.edges.find((e) => e.data.event === 'START');
      expect(startEdge?.data.transitionType).toBe('event');
    });

    it('should convert object transitions with guards', () => {
      const xstate: XStateMachineConfig = {
        id: 'guarded',
        version: '1',
        initial: 'pending',
        states: {
          pending: {
            on: {
              APPROVE: { target: 'approved', guard: 'canApprove' },
            },
          },
          approved: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      const approveEdge = result.edges.find((e) => e.data.event === 'APPROVE');
      expect(approveEdge?.data.guard).toEqual({
        type: 'python',
        name: 'canApprove',
      });
    });

    it('should convert transitions with actions', () => {
      const xstate: XStateMachineConfig = {
        id: 'with-actions',
        version: '1',
        initial: 'draft',
        states: {
          draft: {
            on: {
              SUBMIT: {
                target: 'submitted',
                actions: ['validate', 'notify'],
              },
            },
          },
          submitted: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      const submitEdge = result.edges.find((e) => e.data.event === 'SUBMIT');
      expect(submitEdge?.data.actions).toEqual(['validate', 'notify']);
    });

    it('should convert multiple conditional transitions', () => {
      const xstate: XStateMachineConfig = {
        id: 'conditional',
        version: '1',
        initial: 'pending',
        states: {
          pending: {
            on: {
              REVIEW: [
                { target: 'approved', guard: 'isValid' },
                { target: 'rejected', guard: 'isInvalid' },
              ],
            },
          },
          approved: {},
          rejected: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      const reviewEdges = result.edges.filter((e) => e.data.event === 'REVIEW');
      expect(reviewEdges).toHaveLength(2);
    });
  });

  describe('delayed transitions', () => {
    it('should convert delayed transitions', () => {
      const xstate: XStateMachineConfig = {
        id: 'delayed',
        version: '1',
        initial: 'waiting',
        states: {
          waiting: {
            after: {
              5000: 'timeout',
            },
          },
          timeout: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      const delayedEdge = result.edges.find((e) => e.data.transitionType === 'delayed');
      // 5000ms is converted to 5 seconds by convertMsToHumanReadable
      expect(delayedEdge?.data.delay).toBe(5);
      expect(delayedEdge?.data.delayUnit).toBe('seconds');
    });

    it('should convert delayed transitions with guards', () => {
      const xstate: XStateMachineConfig = {
        id: 'delayed-guarded',
        version: '1',
        initial: 'waiting',
        states: {
          waiting: {
            after: {
              3000: { target: 'expired', guard: 'shouldExpire' },
            },
          },
          expired: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      const delayedEdge = result.edges.find((e) => e.data.transitionType === 'delayed');
      expect(delayedEdge?.data.guard?.name).toBe('shouldExpire');
    });
  });

  describe('always transitions', () => {
    it('should convert always transitions', () => {
      const xstate: XStateMachineConfig = {
        id: 'always',
        version: '1',
        initial: 'checking',
        states: {
          checking: {
            always: [{ target: 'done', guard: 'isReady' }],
          },
          done: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      const alwaysEdge = result.edges.find((e) => e.data.transitionType === 'always');
      expect(alwaysEdge).toBeDefined();
      expect(alwaysEdge?.data.guard?.name).toBe('isReady');
    });
  });

  describe('nested states', () => {
    it('should create child nodes with parentId', () => {
      const xstate: XStateMachineConfig = {
        id: 'nested',
        version: '1',
        initial: 'parent',
        states: {
          parent: {
            initial: 'child1',
            states: {
              child1: { on: { NEXT: 'child2' } },
              child2: {},
            },
          },
        },
      };

      const result = xstateToWorkflow(xstate);

      const parentNode = result.nodes.find((n) => n.data.label === 'parent');
      const child1Node = result.nodes.find((n) => n.data.label === 'child1');
      const child2Node = result.nodes.find((n) => n.data.label === 'child2');

      expect(parentNode).toBeDefined();
      expect(child1Node?.parentId).toBe(parentNode?.id);
      expect(child2Node?.parentId).toBe(parentNode?.id);
    });

    it('should handle deeply nested states', () => {
      const xstate: XStateMachineConfig = {
        id: 'deep-nested',
        version: '1',
        initial: 'level1',
        states: {
          level1: {
            initial: 'level2',
            states: {
              level2: {
                initial: 'level3',
                states: {
                  level3: {},
                },
              },
            },
          },
        },
      };

      const result = xstateToWorkflow(xstate);

      expect(result.nodes).toHaveLength(3);

      const level1 = result.nodes.find((n) => n.data.label === 'level1');
      const level2 = result.nodes.find((n) => n.data.label === 'level2');
      const level3 = result.nodes.find((n) => n.data.label === 'level3');

      expect(level2?.parentId).toBe(level1?.id);
      expect(level3?.parentId).toBe(level2?.id);
    });
  });

  describe('existing layout preservation', () => {
    it('should use existing positions when provided', () => {
      const xstate: XStateMachineConfig = {
        id: 'positioned',
        version: '1',
        initial: 'start',
        states: {
          start: { on: { GO: 'end' } },
          end: {},
        },
      };

      const existingLayout = {
        id: 'positioned',
        name: 'Positioned',
        version: 1,
        nodes: [
          {
            id: 'old1',
            type: 'atomic' as const,
            position: { x: 500, y: 300 },
            data: { label: 'start', xstateType: 'atomic' as const, isInitial: true },
          },
          {
            id: 'old2',
            type: 'atomic' as const,
            position: { x: 800, y: 300 },
            data: { label: 'end', xstateType: 'atomic' as const, isInitial: false },
          },
        ],
        edges: [],
      };

      const result = xstateToWorkflow(xstate, existingLayout);

      const startNode = result.nodes.find((n) => n.data.label === 'start');
      const endNode = result.nodes.find((n) => n.data.label === 'end');

      expect(startNode?.position).toEqual({ x: 500, y: 300 });
      expect(endNode?.position).toEqual({ x: 800, y: 300 });
    });

    it('should auto-layout new nodes when no existing position', () => {
      const xstate: XStateMachineConfig = {
        id: 'auto-layout',
        version: '1',
        initial: 'a',
        states: {
          a: { on: { GO: 'b' } },
          b: { on: { GO: 'c' } },
          c: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      // All nodes should have valid positions
      for (const node of result.nodes) {
        expect(node.position.x).toBeGreaterThanOrEqual(0);
        expect(node.position.y).toBeGreaterThanOrEqual(0);
      }

      // Nodes should have different positions
      const positions = result.nodes.map((n) => `${n.position.x},${n.position.y}`);
      const uniquePositions = new Set(positions);
      expect(uniquePositions.size).toBe(result.nodes.length);
    });
  });

  describe('edge cases', () => {
    it('should handle empty states object', () => {
      const xstate: XStateMachineConfig = {
        id: 'empty',
        version: '1',
        initial: '',
        states: {},
      };

      const result = xstateToWorkflow(xstate);

      expect(result.nodes).toHaveLength(0);
      expect(result.edges).toHaveLength(0);
    });

    it('should handle machine with no transitions', () => {
      const xstate: XStateMachineConfig = {
        id: 'no-transitions',
        version: '1',
        initial: 'only',
        states: {
          only: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      expect(result.nodes).toHaveLength(1);
      expect(result.edges).toHaveLength(0);
    });

    it('should handle self-transitions', () => {
      const xstate: XStateMachineConfig = {
        id: 'self-transition',
        version: '1',
        initial: 'loop',
        states: {
          loop: { on: { RETRY: 'loop' } },
        },
      };

      const result = xstateToWorkflow(xstate);

      const retryEdge = result.edges.find((e) => e.data.event === 'RETRY');
      expect(retryEdge?.source).toBe(retryEdge?.target);
    });
  });

  describe('allowsSubmit property', () => {
    it('should read allowsSubmit from state meta', () => {
      const xstate: XStateMachineConfig = {
        id: 'submit-workflow',
        version: '1',
        initial: 'draft',
        states: {
          draft: {
            on: { APPROVE: 'approved' },
          },
          approved: {
            meta: {
              allowsSubmit: true,
            },
          },
        },
      };

      const result = xstateToWorkflow(xstate);

      const approvedNode = result.nodes.find((n) => n.data.label === 'approved');
      expect(approvedNode?.data.allowsSubmit).toBe(true);
    });

    it('should default allowsSubmit to undefined when not in meta', () => {
      const xstate: XStateMachineConfig = {
        id: 'no-submit-workflow',
        version: '1',
        initial: 'draft',
        states: {
          draft: {},
        },
      };

      const result = xstateToWorkflow(xstate);

      const draftNode = result.nodes.find((n) => n.data.label === 'draft');
      expect(draftNode?.data.allowsSubmit).toBeUndefined();
    });
  });
});
