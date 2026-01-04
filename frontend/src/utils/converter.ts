// Converters between React Flow and XState formats

import type {
  StateNode,
  TransitionEdge,
  XStateMachineConfig,
  XStateStateConfig,
  XStateTransition,
  ReactFlowConfig,
  StateNodeData
} from '../types';

/**
 * Convert React Flow nodes/edges to XState machine config
 */
export function reactFlowToXState(
  nodes: StateNode[],
  edges: TransitionEdge[],
  machineId: string,
  context: Record<string, unknown> = {}
): XStateMachineConfig {
  // Find initial node
  const initialNode = nodes.find(n => n.data.stateType === 'initial');
  const initial = initialNode?.id || nodes[0]?.id || 'idle';

  // Build states
  const states: Record<string, XStateStateConfig> = {};

  for (const node of nodes) {
    const stateConfig: XStateStateConfig = {};

    // Set type for special states
    if (node.data.stateType === 'final') {
      stateConfig.type = 'final';
    } else if (node.data.stateType === 'parallel') {
      stateConfig.type = 'parallel';
    } else if (node.data.stateType === 'history') {
      stateConfig.type = 'history';
      if (node.data.historyType) {
        stateConfig.history = node.data.historyType;
      }
    }

    // Add entry/exit actions
    if (node.data.entryActions?.length) {
      stateConfig.entry = node.data.entryActions;
    }
    if (node.data.exitActions?.length) {
      stateConfig.exit = node.data.exitActions;
    }

    // Build transitions from edges
    const nodeEdges = edges.filter(e => e.source === node.id);
    if (nodeEdges.length > 0) {
      const on: Record<string, XStateTransition | XStateTransition[]> = {};

      for (const edge of nodeEdges) {
        const eventName = edge.data?.event || edge.label || `TO_${edge.target.toUpperCase()}`;

        // Build transition
        const hasGuardOrActions = edge.data?.guard || (edge.data?.actions?.length ?? 0) > 0;

        if (hasGuardOrActions) {
          const transition: XStateTransition = {
            target: edge.target
          };

          if (edge.data?.guard) {
            transition.guard = edge.data.guard;
          }

          if (edge.data?.actions?.length) {
            transition.actions = edge.data.actions;
          }

          // Check if we already have this event (multiple transitions = conditional)
          if (on[eventName]) {
            const existing = on[eventName];
            if (Array.isArray(existing)) {
              existing.push(transition);
            } else {
              on[eventName] = [existing, transition];
            }
          } else {
            on[eventName] = transition;
          }
        } else {
          // Simple transition - just target string
          on[eventName] = edge.target;
        }
      }

      stateConfig.on = on;
    }

    states[node.id] = Object.keys(stateConfig).length > 0 ? stateConfig : {};
  }

  return {
    id: machineId,
    initial,
    context,
    states
  };
}

/**
 * Convert XState machine config to React Flow nodes/edges
 */
export function xstateToReactFlow(config: XStateMachineConfig): ReactFlowConfig {
  const nodes: StateNode[] = [];
  const edges: TransitionEdge[] = [];

  const states = config.states || {};
  const initialState = config.initial || '';

  // Layout constants
  const X_SPACING = 250;
  const Y_SPACING = 150;
  const X_START = 50;
  const Y_START = 50;

  // Create nodes
  const stateNames = Object.keys(states);
  stateNames.forEach((stateName, index) => {
    const stateConfig = states[stateName];

    // Determine state type
    let stateType: StateNodeData['stateType'] = 'atomic';
    if (stateName === initialState) {
      stateType = 'initial';
    } else if (stateConfig.type === 'final') {
      stateType = 'final';
    } else if (stateConfig.type === 'parallel') {
      stateType = 'parallel';
    } else if (stateConfig.type === 'history') {
      stateType = 'history';
    } else if (stateConfig.states) {
      stateType = 'compound';
    }

    // Calculate position in grid
    const col = index % 4;
    const row = Math.floor(index / 4);

    const node: StateNode = {
      id: stateName,
      type: 'stateNode',
      position: {
        x: X_START + col * X_SPACING,
        y: Y_START + row * Y_SPACING
      },
      data: {
        label: stateName,
        stateType,
        entryActions: normalizeActions(stateConfig.entry),
        exitActions: normalizeActions(stateConfig.exit),
        historyType: stateConfig.history
      }
    };

    nodes.push(node);

    // Create edges from transitions
    const onTransitions = stateConfig.on || {};
    for (const [eventName, transition] of Object.entries(onTransitions)) {
      const transitions = Array.isArray(transition) ? transition : [transition];

      for (const t of transitions) {
        const target = typeof t === 'string' ? t : t.target;
        if (!target) continue;

        const edge: TransitionEdge = {
          id: `${stateName}-${eventName}-${target}-${Math.random().toString(36).substr(2, 9)}`,
          source: stateName,
          target,
          type: 'transitionEdge',
          label: eventName,
          data: {
            event: eventName,
            guard: typeof t === 'object' ? (t.guard || t.cond) : undefined,
            actions: typeof t === 'object' ? normalizeActions(t.actions) : [],
            isConditional: Array.isArray(transition)
          }
        };

        edges.push(edge);
      }
    }
  });

  return {
    machineId: config.id || 'workflow',
    nodes,
    edges,
    context: config.context || {}
  };
}

/**
 * Normalize actions to array format
 */
function normalizeActions(actions: string | string[] | undefined): string[] {
  if (!actions) return [];
  if (Array.isArray(actions)) return actions;
  return [actions];
}

/**
 * Validate XState config structure
 */
export function validateXStateConfig(config: unknown): config is XStateMachineConfig {
  if (!config || typeof config !== 'object') return false;

  const c = config as Record<string, unknown>;

  if (typeof c.id !== 'string') return false;
  if (typeof c.states !== 'object' || c.states === null) return false;

  return true;
}

/**
 * Generate a unique state ID
 */
export function generateStateId(existingIds: string[]): string {
  let counter = 1;
  let id = `state${counter}`;

  while (existingIds.includes(id)) {
    counter++;
    id = `state${counter}`;
  }

  return id;
}
