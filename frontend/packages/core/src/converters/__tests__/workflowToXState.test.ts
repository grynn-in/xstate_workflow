import { describe, it, expect } from 'vitest';
import { workflowToXState } from '../workflowToXState';
import type { WorkflowBuilderConfig, WorkflowNode, WorkflowEdge } from '../../types';

describe('workflowToXState', () => {
  describe('basic conversion', () => {
    it('should convert a simple two-state workflow', () => {
      const config: WorkflowBuilderConfig = {
        id: 'simple-workflow',
        name: 'Simple Workflow',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'draft', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'published', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: { event: 'PUBLISH', transitionType: 'event' },
          },
        ],
      };

      const result = workflowToXState(config);

      expect(result.id).toBe('simple-workflow');
      expect(result.initial).toBe('draft');
      expect(result.states.draft).toBeDefined();
      expect(result.states.published).toBeDefined();
      expect(result.states.draft.on?.PUBLISH).toBe('published');
    });

    it('should throw error when no initial state is found', () => {
      const config: WorkflowBuilderConfig = {
        id: 'no-initial',
        name: 'No Initial',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'state1', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [],
      };

      expect(() => workflowToXState(config)).toThrow('No initial state found');
    });

    it('should preserve context data', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-context',
        name: 'With Context',
        version: 1,
        context: { count: 0, user: null },
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'idle', xstateType: 'atomic', isInitial: true },
          },
        ],
        edges: [],
      };

      const result = workflowToXState(config);

      expect(result.context).toEqual({ count: 0, user: null });
    });
  });

  describe('state types', () => {
    it('should convert final state type', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-final',
        name: 'With Final',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'start', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'final',
            position: { x: 200, y: 0 },
            data: { label: 'completed', xstateType: 'final', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: { event: 'COMPLETE', transitionType: 'event' },
          },
        ],
      };

      const result = workflowToXState(config);

      expect(result.states.completed.type).toBe('final');
    });

    it('should convert parallel state type', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-parallel',
        name: 'With Parallel',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'parallel',
            position: { x: 0, y: 0 },
            data: { label: 'processing', xstateType: 'parallel', isInitial: true },
          },
        ],
        edges: [],
      };

      const result = workflowToXState(config);

      expect(result.states.processing.type).toBe('parallel');
    });

    it('should convert history state with shallow type', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-history',
        name: 'With History',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'main', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'history',
            position: { x: 200, y: 0 },
            data: { label: 'hist', xstateType: 'history', isInitial: false, historyType: 'shallow' },
          },
        ],
        edges: [],
      };

      const result = workflowToXState(config);

      expect(result.states.hist.type).toBe('history');
      expect(result.states.hist.history).toBe('shallow');
    });

    it('should convert history state with deep type', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-deep-history',
        name: 'With Deep History',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'main', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'history',
            position: { x: 200, y: 0 },
            data: { label: 'hist', xstateType: 'history', isInitial: false, historyType: 'deep' },
          },
        ],
        edges: [],
      };

      const result = workflowToXState(config);

      expect(result.states.hist.history).toBe('deep');
    });
  });

  describe('entry and exit actions', () => {
    it('should include entry actions', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-entry',
        name: 'With Entry',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: {
              label: 'active',
              xstateType: 'atomic',
              isInitial: true,
              entryActions: ['logEntry', 'sendNotification'],
            },
          },
        ],
        edges: [],
      };

      const result = workflowToXState(config);

      expect(result.states.active.entry).toEqual(['logEntry', 'sendNotification']);
    });

    it('should include exit actions', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-exit',
        name: 'With Exit',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: {
              label: 'active',
              xstateType: 'atomic',
              isInitial: true,
              exitActions: ['cleanup', 'saveState'],
            },
          },
        ],
        edges: [],
      };

      const result = workflowToXState(config);

      expect(result.states.active.exit).toEqual(['cleanup', 'saveState']);
    });
  });

  describe('transitions', () => {
    it('should convert transitions with guards', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-guards',
        name: 'With Guards',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'pending', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'approved', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              event: 'APPROVE',
              transitionType: 'event',
              guard: { type: 'python', name: 'canApprove' },
            },
          },
        ],
      };

      const result = workflowToXState(config);

      const transition = result.states.pending.on?.APPROVE;
      expect(transition).toEqual({
        target: 'approved',
        guard: 'canApprove',
      });
    });

    it('should convert transitions with actions', () => {
      const config: WorkflowBuilderConfig = {
        id: 'with-actions',
        name: 'With Actions',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'draft', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'submitted', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              event: 'SUBMIT',
              transitionType: 'event',
              actions: ['validateForm', 'sendEmail'],
            },
          },
        ],
      };

      const result = workflowToXState(config);

      const transition = result.states.draft.on?.SUBMIT;
      expect(transition).toEqual({
        target: 'submitted',
        actions: ['validateForm', 'sendEmail'],
      });
    });

    it('should convert multiple conditional transitions for same event', () => {
      const config: WorkflowBuilderConfig = {
        id: 'conditional',
        name: 'Conditional',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'pending', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'approved', xstateType: 'atomic', isInitial: false },
          },
          {
            id: 'node3',
            type: 'atomic',
            position: { x: 200, y: 100 },
            data: { label: 'rejected', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              event: 'REVIEW',
              transitionType: 'event',
              guard: { type: 'python', name: 'isValid' },
            },
          },
          {
            id: 'edge2',
            source: 'node1',
            target: 'node3',
            type: 'transition',
            data: {
              event: 'REVIEW',
              transitionType: 'event',
              guard: { type: 'python', name: 'isInvalid' },
            },
          },
        ],
      };

      const result = workflowToXState(config);

      const transitions = result.states.pending.on?.REVIEW;
      expect(Array.isArray(transitions)).toBe(true);
      expect(transitions).toHaveLength(2);
    });
  });

  describe('delayed transitions', () => {
    it('should convert delayed transitions in milliseconds', () => {
      const config: WorkflowBuilderConfig = {
        id: 'delayed-ms',
        name: 'Delayed MS',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'waiting', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'timeout', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              transitionType: 'delayed',
              delay: 5000,
              delayUnit: 'ms',
            },
          },
        ],
      };

      const result = workflowToXState(config);

      expect(result.states.waiting.after?.[5000]).toBe('timeout');
    });

    it('should convert delayed transitions in seconds', () => {
      const config: WorkflowBuilderConfig = {
        id: 'delayed-seconds',
        name: 'Delayed Seconds',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'waiting', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'timeout', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              transitionType: 'delayed',
              delay: 30,
              delayUnit: 'seconds',
            },
          },
        ],
      };

      const result = workflowToXState(config);

      expect(result.states.waiting.after?.[30000]).toBe('timeout');
    });

    it('should convert delayed transitions in minutes', () => {
      const config: WorkflowBuilderConfig = {
        id: 'delayed-minutes',
        name: 'Delayed Minutes',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'waiting', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'expired', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              transitionType: 'delayed',
              delay: 5,
              delayUnit: 'minutes',
            },
          },
        ],
      };

      const result = workflowToXState(config);

      expect(result.states.waiting.after?.[300000]).toBe('expired');
    });

    it('should convert delayed transitions in hours', () => {
      const config: WorkflowBuilderConfig = {
        id: 'delayed-hours',
        name: 'Delayed Hours',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'waiting', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'expired', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              transitionType: 'delayed',
              delay: 2,
              delayUnit: 'hours',
            },
          },
        ],
      };

      const result = workflowToXState(config);

      expect(result.states.waiting.after?.[7200000]).toBe('expired');
    });
  });

  describe('always transitions', () => {
    it('should convert always transitions', () => {
      const config: WorkflowBuilderConfig = {
        id: 'always',
        name: 'Always',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'checking', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'done', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              transitionType: 'always',
              guard: { type: 'python', name: 'isReady' },
            },
          },
        ],
      };

      const result = workflowToXState(config);

      expect(result.states.checking.always).toBeDefined();
      expect(result.states.checking.always).toHaveLength(1);
      expect(result.states.checking.always?.[0]).toEqual({
        target: 'done',
        guard: 'isReady',
      });
    });
  });

  describe('compound states', () => {
    it('should convert compound states with children', () => {
      const config: WorkflowBuilderConfig = {
        id: 'compound',
        name: 'Compound',
        version: 1,
        nodes: [
          {
            id: 'parent',
            type: 'compound',
            position: { x: 0, y: 0 },
            data: {
              label: 'review',
              xstateType: 'compound',
              isInitial: true,
              initialChild: 'technical',
            },
          },
          {
            id: 'child1',
            type: 'atomic',
            position: { x: 50, y: 50 },
            parentId: 'parent',
            data: { label: 'technical', xstateType: 'atomic', isInitial: false },
          },
          {
            id: 'child2',
            type: 'atomic',
            position: { x: 150, y: 50 },
            parentId: 'parent',
            data: { label: 'business', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'child1',
            target: 'child2',
            type: 'transition',
            data: { event: 'NEXT', transitionType: 'event' },
          },
        ],
      };

      const result = workflowToXState(config);

      expect(result.states.review.states).toBeDefined();
      expect(result.states.review.initial).toBe('technical');
      expect(result.states.review.states?.technical).toBeDefined();
      expect(result.states.review.states?.business).toBeDefined();
      expect(result.states.review.states?.technical.on?.NEXT).toBe('business');
    });
  });

  describe('guard config conversion', () => {
    it('should convert simple guard to name', () => {
      const config: WorkflowBuilderConfig = {
        id: 'simple-guard',
        name: 'Simple Guard',
        version: 1,
        nodes: [
          {
            id: 'node1',
            type: 'atomic',
            position: { x: 0, y: 0 },
            data: { label: 'start', xstateType: 'atomic', isInitial: true },
          },
          {
            id: 'node2',
            type: 'atomic',
            position: { x: 200, y: 0 },
            data: { label: 'end', xstateType: 'atomic', isInitial: false },
          },
        ],
        edges: [
          {
            id: 'edge1',
            source: 'node1',
            target: 'node2',
            type: 'transition',
            data: {
              event: 'GO',
              transitionType: 'event',
              guard: {
                type: 'simple',
                field: 'amount',
                operator: 'greaterThan',
                value: 100,
              },
            },
          },
        ],
      };

      const result = workflowToXState(config);

      const transition = result.states.start.on?.GO as { guard: string };
      expect(transition.guard).toBe('check_amount_greaterThan');
    });
  });
});
