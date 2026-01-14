import type {
  WorkflowBuilderConfig,
  WorkflowNode,
  WorkflowEdge,
  XStateMachineConfig,
  XStateStateConfig,
  XStateTransition,
  WorkflowNodeData,
  WorkflowEdgeData,
  XStateNodeType,
  DomainNodeType,
  ApprovalNodeData,
  ThresholdGateNodeData,
  ClassificationBranchNodeData,
  AutoActionNodeData,
  EndNodeData,
  StartNodeData,
} from '../types';

// Helper to check if a state has domain node metadata
interface DomainNodeMeta {
  type: DomainNodeType;
  [key: string]: unknown;
}

function hasDomainNodeMeta(config: XStateStateConfig): config is XStateStateConfig & {
  meta: { domain_node: DomainNodeMeta };
} {
  return config.meta?.domain_node?.type !== undefined;
}

let nodeIdCounter = 0;
let edgeIdCounter = 0;

function generateNodeId(): string {
  return `node_${++nodeIdCounter}`;
}

function generateEdgeId(): string {
  return `edge_${++edgeIdCounter}`;
}

/**
 * Converts an XState v5 JSON configuration to WorkflowBuilder format
 */
export function xstateToWorkflow(
  xstate: XStateMachineConfig,
  existingLayout?: WorkflowBuilderConfig
): WorkflowBuilderConfig {
  // Reset counters
  nodeIdCounter = 0;
  edgeIdCounter = 0;

  const nodes: WorkflowNode[] = [];
  const edges: WorkflowEdge[] = [];

  // Create a map for existing positions if available
  const existingPositions = new Map<string, { x: number; y: number }>();
  if (existingLayout) {
    for (const node of existingLayout.nodes) {
      existingPositions.set(node.data.label, node.position);
    }
  }

  // Process all states
  const stateIdMap = new Map<string, string>(); // label -> node id

  processStates(
    xstate.states,
    xstate.initial,
    nodes,
    edges,
    stateIdMap,
    existingPositions
  );

  return {
    id: xstate.id,
    name: xstate.id,
    version: parseInt(xstate.version || '1', 10),
    context: xstate.context,
    nodes,
    edges,
  };
}

/**
 * Process states recursively
 */
function processStates(
  states: Record<string, XStateStateConfig>,
  initialState: string,
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  stateIdMap: Map<string, string>,
  existingPositions: Map<string, { x: number; y: number }>,
  parentId?: string,
  basePosition = { x: 100, y: 100 }
): void {
  const stateNames = Object.keys(states);
  let xOffset = 0;
  let yOffset = 0;

  for (const stateName of stateNames) {
    const stateConfig = states[stateName];
    const nodeId = generateNodeId();
    stateIdMap.set(stateName, nodeId);

    // Check if this is a domain node
    if (hasDomainNodeMeta(stateConfig)) {
      const domainNode = buildDomainNode(
        nodeId,
        stateName,
        stateConfig,
        existingPositions,
        basePosition,
        xOffset,
        yOffset,
        parentId
      );
      nodes.push(domainNode);

      // Update offsets
      xOffset += 200;
      if (xOffset > 600) {
        xOffset = 0;
        yOffset += 150;
      }
      continue;
    }

    // Determine state type
    const xstateType = determineStateType(stateConfig);
    const isInitial = stateName === initialState && !parentId;

    // Get position from existing layout or auto-layout
    const position = existingPositions.get(stateName) || {
      x: basePosition.x + xOffset,
      y: basePosition.y + yOffset,
    };

    const nodeData: WorkflowNodeData = {
      label: stateName,
      xstateType,
      isInitial,
      entryActions: normalizeActions(stateConfig.entry),
      exitActions: normalizeActions(stateConfig.exit),
    };

    // Handle history type
    if (xstateType === 'history') {
      nodeData.historyType = stateConfig.history || 'shallow';
    }

    // Handle compound state initial
    if (stateConfig.initial) {
      nodeData.initialChild = stateConfig.initial;
    }

    const node: WorkflowNode = {
      id: nodeId,
      type: xstateType,
      position,
      data: nodeData,
      ...(parentId && { parentId, extent: 'parent' as const }),
    };

    nodes.push(node);

    // Process nested states
    if (stateConfig.states) {
      processStates(
        stateConfig.states,
        stateConfig.initial || '',
        nodes,
        edges,
        stateIdMap,
        existingPositions,
        nodeId,
        { x: position.x + 50, y: position.y + 80 }
      );
    }

    // Update offsets for next node
    xOffset += 200;
    if (xOffset > 600) {
      xOffset = 0;
      yOffset += 150;
    }
  }

  // Process transitions after all nodes are created
  for (const stateName of stateNames) {
    const stateConfig = states[stateName];
    const sourceId = stateIdMap.get(stateName)!;

    // Process event transitions
    if (stateConfig.on) {
      processEventTransitions(stateConfig.on, sourceId, edges, stateIdMap);
    }

    // Process delayed transitions
    if (stateConfig.after) {
      processDelayedTransitions(stateConfig.after, sourceId, edges, stateIdMap);
    }

    // Process always transitions
    if (stateConfig.always) {
      processAlwaysTransitions(stateConfig.always, sourceId, edges, stateIdMap);
    }
  }
}

/**
 * Determine XState node type from config
 */
function determineStateType(config: XStateStateConfig): XStateNodeType {
  if (config.type === 'final') return 'final';
  if (config.type === 'parallel') return 'parallel';
  if (config.type === 'history') return 'history';
  if (config.states) return 'compound';
  return 'atomic';
}

/**
 * Normalize actions to string array
 */
function normalizeActions(actions?: string | string[]): string[] | undefined {
  if (!actions) return undefined;
  if (typeof actions === 'string') return [actions];
  return actions;
}

/**
 * Process event-based transitions
 */
function processEventTransitions(
  on: Record<string, XStateTransition | XStateTransition[] | string>,
  sourceId: string,
  edges: WorkflowEdge[],
  stateIdMap: Map<string, string>
): void {
  for (const [eventName, transition] of Object.entries(on)) {
    // Skip undefined/null transitions
    if (transition == null) continue;

    if (Array.isArray(transition)) {
      // Multiple conditional transitions
      for (const t of transition) {
        if (t != null) {
          createEdgeFromTransition(t, eventName, 'event', sourceId, edges, stateIdMap);
        }
      }
    } else {
      createEdgeFromTransition(transition, eventName, 'event', sourceId, edges, stateIdMap);
    }
  }
}

/**
 * Process delayed transitions
 */
function processDelayedTransitions(
  after: Record<string, XStateTransition | string>,
  sourceId: string,
  edges: WorkflowEdge[],
  stateIdMap: Map<string, string>
): void {
  for (const [delay, transition] of Object.entries(after)) {
    // Skip undefined/null transitions
    if (transition == null) continue;

    const delayMs = parseInt(delay, 10);
    createEdgeFromTransition(
      transition,
      undefined,
      'delayed',
      sourceId,
      edges,
      stateIdMap,
      delayMs
    );
  }
}

/**
 * Process always transitions
 */
function processAlwaysTransitions(
  always: XStateTransition[],
  sourceId: string,
  edges: WorkflowEdge[],
  stateIdMap: Map<string, string>
): void {
  for (const transition of always) {
    // Skip undefined/null transitions
    if (transition == null) continue;

    createEdgeFromTransition(transition, undefined, 'always', sourceId, edges, stateIdMap);
  }
}

/**
 * Create a workflow edge from an XState transition
 */
function createEdgeFromTransition(
  transition: XStateTransition | string,
  eventName: string | undefined,
  transitionType: 'event' | 'delayed' | 'always',
  sourceId: string,
  edges: WorkflowEdge[],
  stateIdMap: Map<string, string>,
  delay?: number
): void {
  // Skip null/undefined transitions
  if (transition == null) return;

  // Handle simple string transitions
  if (typeof transition === 'string') {
    const targetId = stateIdMap.get(transition);
    if (!targetId) return;

    edges.push({
      id: generateEdgeId(),
      source: sourceId,
      target: targetId,
      type: 'transition',
      data: {
        event: eventName,
        transitionType,
        ...(delay && { delay, delayUnit: 'ms' as const }),
      },
    });
    return;
  }

  // Handle object transitions
  const targetLabel = transition.target;
  if (!targetLabel) return;

  const targetId = stateIdMap.get(targetLabel);
  if (!targetId) return;

  const edgeData: WorkflowEdgeData = {
    event: eventName,
    transitionType,
    ...(delay && { delay, delayUnit: 'ms' as const }),
    actions: transition.actions,
  };

  // Convert guard string to guard config
  if (transition.guard) {
    edgeData.guard = {
      type: 'python',
      name: transition.guard,
    };
  }

  edges.push({
    id: generateEdgeId(),
    source: sourceId,
    target: targetId,
    type: 'transition',
    data: edgeData,
  });
}

/**
 * Build a domain node from XState config with domain_node metadata
 */
function buildDomainNode(
  nodeId: string,
  stateName: string,
  stateConfig: XStateStateConfig & { meta: { domain_node: DomainNodeMeta } },
  existingPositions: Map<string, { x: number; y: number }>,
  basePosition: { x: number; y: number },
  xOffset: number,
  yOffset: number,
  parentId?: string
): WorkflowNode {
  const meta = stateConfig.meta.domain_node;
  const domainType = meta.type;

  const position = existingPositions.get(stateName) || {
    x: basePosition.x + xOffset,
    y: basePosition.y + yOffset,
  };

  // Build node data based on domain type
  let nodeData: WorkflowNodeData;

  switch (domainType) {
    case 'start':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'atomic',
        domainType: 'start',
      } as StartNodeData;
      break;

    case 'end':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'final',
        domainType: 'end',
        finalStatus: meta.final_status as string | undefined,
      } as EndNodeData;
      break;

    case 'approval':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'atomic',
        domainType: 'approval',
        resolver: meta.resolver,
        availableActions: (meta.available_actions as string[]) || ['Approve', 'Reject'],
        slaHours: meta.sla_hours as number | undefined,
        priority: meta.priority as 'Low' | 'Medium' | 'High' | 'Urgent' | undefined,
        fallbackUser: meta.fallback_user as string | undefined,
        escalation: meta.escalation as ApprovalNodeData['escalation'],
      } as ApprovalNodeData;
      break;

    case 'threshold_gate':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'atomic',
        domainType: 'threshold_gate',
        threshold: meta.threshold as ThresholdGateNodeData['threshold'],
      } as ThresholdGateNodeData;
      break;

    case 'classification_branch':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'atomic',
        domainType: 'classification_branch',
        field: meta.field as string,
        branches: meta.branches as ClassificationBranchNodeData['branches'],
        defaultTarget: meta.default_target as string | undefined,
      } as ClassificationBranchNodeData;
      break;

    case 'auto_action':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'atomic',
        domainType: 'auto_action',
        actionType: meta.action_type as AutoActionNodeData['actionType'],
        actionConfig: (meta.action_config as AutoActionNodeData['actionConfig']) || {},
      } as AutoActionNodeData;
      break;

    default:
      nodeData = {
        label: stateName,
        xstateType: 'atomic',
      };
  }

  return {
    id: nodeId,
    type: domainType,
    position,
    data: nodeData,
    ...(parentId && { parentId, extent: 'parent' as const }),
  };
}
