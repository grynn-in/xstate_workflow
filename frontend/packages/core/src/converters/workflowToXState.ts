import type {
  WorkflowBuilderConfig,
  WorkflowNode,
  WorkflowEdge,
  XStateMachineConfig,
  XStateStateConfig,
  XStateTransition,
  GuardConfig,
} from '../types';

/**
 * Converts a WorkflowBuilder configuration to XState v5 JSON format
 */
export function workflowToXState(config: WorkflowBuilderConfig): XStateMachineConfig {
  const { id, nodes, edges, context } = config;

  // Find the initial state
  const initialNode = nodes.find((n) => n.data.isInitial);
  if (!initialNode) {
    throw new Error('No initial state found in workflow');
  }

  // Build the states object
  const states: Record<string, XStateStateConfig> = {};

  // Process top-level nodes (nodes without parentId)
  const topLevelNodes = nodes.filter((n) => !n.parentId);

  for (const node of topLevelNodes) {
    states[node.data.label] = buildStateConfig(node, nodes, edges);
  }

  return {
    id,
    version: String(config.version),
    initial: initialNode.data.label,
    context: context || {},
    states,
  };
}

/**
 * Builds an XState state configuration from a workflow node
 */
function buildStateConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const config: XStateStateConfig = {};
  const { data } = node;

  // Set state type for special states
  if (data.xstateType === 'final') {
    config.type = 'final';
  } else if (data.xstateType === 'parallel') {
    config.type = 'parallel';
  } else if (data.xstateType === 'history') {
    config.type = 'history';
    config.history = data.historyType || 'shallow';
  }

  // Add entry/exit actions
  if (data.entryActions?.length) {
    config.entry = data.entryActions;
  }
  if (data.exitActions?.length) {
    config.exit = data.exitActions;
  }

  // Handle compound states (nested states)
  if (data.xstateType === 'compound' || data.xstateType === 'parallel') {
    const childNodes = allNodes.filter((n) => n.parentId === node.id);
    if (childNodes.length > 0) {
      config.states = {};
      for (const child of childNodes) {
        config.states[child.data.label] = buildStateConfig(child, allNodes, allEdges);
      }

      // Set initial child for compound states
      if (data.xstateType === 'compound' && data.initialChild) {
        config.initial = data.initialChild;
      }
    }
  }

  // Handle invoke configuration
  if (data.invokeConfig) {
    config.invoke = {
      src: data.invokeConfig.src,
      ...(data.invokeConfig.onDone && { onDone: data.invokeConfig.onDone }),
      ...(data.invokeConfig.onError && { onError: data.invokeConfig.onError }),
    };
  }

  // Build transitions from edges
  const outgoingEdges = allEdges.filter((e) => e.source === node.id);

  // Group edges by type
  const eventEdges = outgoingEdges.filter((e) => e.data.transitionType === 'event');
  const delayedEdges = outgoingEdges.filter((e) => e.data.transitionType === 'delayed');
  const alwaysEdges = outgoingEdges.filter((e) => e.data.transitionType === 'always');

  // Process event transitions
  if (eventEdges.length > 0) {
    config.on = {};

    // Group by event name (for conditional transitions)
    const eventGroups = new Map<string, WorkflowEdge[]>();
    for (const edge of eventEdges) {
      const eventName = edge.data.event || 'UNKNOWN';
      if (!eventGroups.has(eventName)) {
        eventGroups.set(eventName, []);
      }
      eventGroups.get(eventName)!.push(edge);
    }

    for (const [eventName, groupEdges] of eventGroups) {
      if (groupEdges.length === 1) {
        config.on[eventName] = buildTransition(groupEdges[0], allNodes);
      } else {
        // Multiple transitions for same event = conditional
        // Map to XStateTransition[] - convert strings to objects
        config.on[eventName] = groupEdges.map((e) => {
          const transition = buildTransition(e, allNodes);
          return typeof transition === 'string'
            ? { target: transition }
            : transition;
        });
      }
    }
  }

  // Process delayed transitions
  if (delayedEdges.length > 0) {
    config.after = {};
    for (const edge of delayedEdges) {
      const delay = calculateDelayMs(edge.data.delay || 0, edge.data.delayUnit);
      config.after[delay] = buildTransition(edge, allNodes);
    }
  }

  // Process always transitions
  if (alwaysEdges.length > 0) {
    config.always = alwaysEdges.map((e) => {
      const transition = buildTransition(e, allNodes);
      // Always transitions should always be objects, not strings
      return typeof transition === 'string'
        ? { target: transition }
        : transition;
    });
  }

  return config;
}

/**
 * Builds an XState transition from a workflow edge
 */
function buildTransition(edge: WorkflowEdge, allNodes: WorkflowNode[]): XStateTransition | string {
  const targetNode = allNodes.find((n) => n.id === edge.target);
  const targetLabel = targetNode?.data.label || edge.target;

  const { data } = edge;
  const hasGuard = !!data.guard;
  const hasActions = (data.actions?.length || 0) > 0;

  // Simple transition (just target)
  if (!hasGuard && !hasActions) {
    return targetLabel;
  }

  // Complex transition
  const transition: XStateTransition = {
    target: targetLabel,
  };

  if (hasGuard) {
    transition.guard = guardConfigToString(data.guard!);
  }

  if (hasActions) {
    transition.actions = data.actions;
  }

  return transition;
}

/**
 * Converts a GuardConfig to a guard name string
 */
function guardConfigToString(guard: GuardConfig): string {
  switch (guard.type) {
    case 'python':
      return guard.name;
    case 'simple':
      // Generate a guard name based on the condition
      return `check_${guard.field}_${guard.operator}`;
    case 'compound':
      // Generate a combined guard name
      return `combined_guard_${guard.operator}`;
    default:
      return 'unknown_guard';
  }
}

/**
 * Converts delay value and unit to milliseconds
 */
function calculateDelayMs(delay: number, unit?: string): number {
  switch (unit) {
    case 'seconds':
      return delay * 1000;
    case 'minutes':
      return delay * 60 * 1000;
    case 'hours':
      return delay * 60 * 60 * 1000;
    default: // 'ms' or undefined
      return delay;
  }
}
