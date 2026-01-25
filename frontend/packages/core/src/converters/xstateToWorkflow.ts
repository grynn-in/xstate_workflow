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
  ParallelApprovalNodeData,
  ThresholdGateNodeData,
  ClassificationBranchNodeData,
  AutoActionNodeData,
  AgenticNodeData,
  RestFetchNodeData,
  EndNodeData,
  StartNodeData,
  ToolConfig,
  AllowedMethod,
  DataInputConfig,
  MCPServerConfig,
  RestEndpointConfig,
  DecisionRoute,
  CustomAgentEvent,
} from '../types';

/**
 * Simple grid-based layout for initial node positioning
 * Used when no saved positions exist - ELK auto-layout can be applied later
 */
function calculateSimpleGridLayout(
  states: Record<string, unknown>,
  nodeWidth = 250,
  nodeHeight = 120,
  gapX = 200,
  gapY = 150,
  startX = 50,
  startY = 50,
  columns = 3
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const stateNames = Object.keys(states);

  stateNames.forEach((name, index) => {
    const col = index % columns;
    const row = Math.floor(index / columns);
    positions.set(name, {
      x: startX + col * (nodeWidth + gapX),
      y: startY + row * (nodeHeight + gapY),
    });
  });

  return positions;
}

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
  // Match by stateName (XState state name) for reliable position persistence
  let existingPositions = new Map<string, { x: number; y: number }>();
  if (existingLayout && existingLayout.nodes.length > 0) {
    for (const node of existingLayout.nodes) {
      // Primary key: stateName (XState state name) - most reliable match
      if (node.data?.stateName) {
        existingPositions.set(node.data.stateName, node.position);
      }
      // Fallback: node.id for older saved configs
      if (node.id) {
        existingPositions.set(node.id, node.position);
      }
      // Fallback: label for backwards compatibility
      if (node.data?.label) {
        existingPositions.set(node.data.label, node.position);
      }
    }
  }

  // Create a map for existing edge control points
  // Key: "sourceLabel->targetLabel:event" for reliable matching
  const existingEdgeData = new Map<string, WorkflowEdgeData>();
  if (existingLayout && existingLayout.edges?.length > 0) {
    for (const edge of existingLayout.edges) {
      // Find source and target labels from existing nodes
      const sourceNode = existingLayout.nodes.find(n => n.id === edge.source);
      const targetNode = existingLayout.nodes.find(n => n.id === edge.target);
      const sourceLabel = sourceNode?.data?.stateName || sourceNode?.data?.label || edge.source;
      const targetLabel = targetNode?.data?.stateName || targetNode?.data?.label || edge.target;
      const event = edge.data?.event || '';
      const key = `${sourceLabel}->${targetLabel}:${event}`;
      if (edge.data) {
        existingEdgeData.set(key, edge.data);
      }
    }
  }

  // If no existing positions, use simple grid layout
  // (ELK auto-layout can be applied later via the UI for better positioning)
  if (existingPositions.size === 0 && xstate.states) {
    existingPositions = calculateSimpleGridLayout(xstate.states);
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

  // Restore edge control points from saved config
  if (existingEdgeData.size > 0) {
    restoreEdgeControlPoints(edges, nodes, existingEdgeData);
  }

  // Calculate path offsets for edges from the same source to spread them out
  calculateEdgeOffsets(edges);

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
 * Restore control points and other edge-specific data from saved config
 */
function restoreEdgeControlPoints(
  edges: WorkflowEdge[],
  nodes: WorkflowNode[],
  existingEdgeData: Map<string, WorkflowEdgeData>
): void {
  for (const edge of edges) {
    // Find source and target labels
    const sourceNode = nodes.find(n => n.id === edge.source);
    const targetNode = nodes.find(n => n.id === edge.target);
    const sourceLabel = sourceNode?.data?.stateName || sourceNode?.data?.label || edge.source;
    const targetLabel = targetNode?.data?.stateName || targetNode?.data?.label || edge.target;
    const event = edge.data?.event || '';
    const key = `${sourceLabel}->${targetLabel}:${event}`;

    const savedData = existingEdgeData.get(key);
    if (savedData?.controlPoint) {
      // Restore the control point
      edge.data.controlPoint = savedData.controlPoint;
    }
  }
}

/**
 * Calculate path offsets for edges to prevent overlap
 * Edges from the same source get spread out vertically
 */
function calculateEdgeOffsets(edges: WorkflowEdge[]): void {
  // Group edges by source
  const edgesBySource = new Map<string, WorkflowEdge[]>();
  for (const edge of edges) {
    const source = edge.source;
    if (!edgesBySource.has(source)) {
      edgesBySource.set(source, []);
    }
    edgesBySource.get(source)!.push(edge);
  }

  // Assign offsets to edges from the same source
  for (const [, sourceEdges] of edgesBySource) {
    if (sourceEdges.length <= 1) continue;

    // Sort edges by target to get consistent ordering
    sourceEdges.sort((a, b) => a.target.localeCompare(b.target));

    // Calculate offset for each edge (-1, 0, 1 for 3 edges, etc.)
    const count = sourceEdges.length;
    const spread = 2; // Offset multiplier
    for (let i = 0; i < count; i++) {
      const offset = (i - (count - 1) / 2) * spread;
      sourceEdges[i].data.pathOffset = offset;
    }
  }
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

      // Set isInitial for domain nodes (was missing - caused "No initial state found" error)
      if (stateName === initialState && !parentId) {
        domainNode.data.isInitial = true;
      }

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
      stateName, // Store for position matching on reload
      xstateType,
      isInitial,
      allowsSubmit: stateConfig.meta?.allowsSubmit === true ? true : undefined,
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

    // Handle parallel state regions
    if (xstateType === 'parallel' && stateConfig.states) {
      nodeData.regions = Object.entries(stateConfig.states).map(([regionName, regionConfig]) => {
        const region = regionConfig as XStateStateConfig;
        return {
          name: regionName,
          label: region.meta?.label || regionName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          initial: region.initial,
          childStates: region.states ? Object.keys(region.states) : [],
        };
      });
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

  // Update nodes with their outgoing events (for dynamic handle generation)
  updateNodesWithOutgoingEvents(nodes, edges);
}

/**
 * Update nodes with their outgoing event names for dynamic handle creation
 */
function updateNodesWithOutgoingEvents(nodes: WorkflowNode[], edges: WorkflowEdge[]): void {
  // Group edges by source node
  const edgesBySource = new Map<string, WorkflowEdge[]>();
  for (const edge of edges) {
    if (!edgesBySource.has(edge.source)) {
      edgesBySource.set(edge.source, []);
    }
    edgesBySource.get(edge.source)!.push(edge);
  }

  // Update each node with its outgoing events
  for (const node of nodes) {
    const nodeEdges = edgesBySource.get(node.id) || [];
    const eventSet = new Set<string>();

    for (const edge of nodeEdges) {
      // Only include event-based transitions (not delayed/always)
      if (edge.data?.transitionType === 'event' && edge.data?.event) {
        eventSet.add(edge.data.event);
      }
    }

    // Convert to array and sort for consistent handle ordering
    const outgoingEvents = Array.from(eventSet).sort();

    // Only add outgoingEvents if there are multiple event-based transitions
    // (single events use the default centered handle)
    if (outgoingEvents.length > 1) {
      node.data.outgoingEvents = outgoingEvents;
    }
  }

  // Fix edge sourceHandles: remove sourceHandle from edges whose source node
  // does NOT have outgoingEvents set (those nodes use a default handle with no ID)
  for (const edge of edges) {
    if (edge.sourceHandle) {
      const sourceNode = nodes.find(n => n.id === edge.source);
      if (sourceNode && !sourceNode.data.outgoingEvents) {
        delete edge.sourceHandle;
      }
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
 * Converts milliseconds to human-readable delay with appropriate unit
 */
function convertMsToHumanReadable(ms: number): { delay: number; delayUnit: 'ms' | 'seconds' | 'minutes' | 'hours' | 'days' } {
  const DAY_MS = 24 * 60 * 60 * 1000;
  const HOUR_MS = 60 * 60 * 1000;
  const MINUTE_MS = 60 * 1000;
  const SECOND_MS = 1000;

  if (ms >= DAY_MS && ms % DAY_MS === 0) {
    return { delay: ms / DAY_MS, delayUnit: 'days' };
  }
  if (ms >= HOUR_MS && ms % HOUR_MS === 0) {
    return { delay: ms / HOUR_MS, delayUnit: 'hours' };
  }
  if (ms >= MINUTE_MS && ms % MINUTE_MS === 0) {
    return { delay: ms / MINUTE_MS, delayUnit: 'minutes' };
  }
  if (ms >= SECOND_MS && ms % SECOND_MS === 0) {
    return { delay: ms / SECOND_MS, delayUnit: 'seconds' };
  }
  return { delay: ms, delayUnit: 'ms' };
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
    const { delay: humanDelay, delayUnit } = convertMsToHumanReadable(delayMs);
    createEdgeFromTransition(
      transition,
      undefined,
      'delayed',
      sourceId,
      edges,
      stateIdMap,
      humanDelay,
      delayUnit
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
  delay?: number,
  delayUnit?: 'ms' | 'seconds' | 'minutes' | 'hours' | 'days'
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
      // Set sourceHandle for event-based transitions (will be used if node has multiple events)
      ...(transitionType === 'event' && eventName && { sourceHandle: eventName }),
      data: {
        event: eventName,
        transitionType,
        ...(delay !== undefined && { delay, delayUnit: delayUnit || 'ms' }),
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
    ...(delay !== undefined && { delay, delayUnit: delayUnit || 'ms' }),
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
    // Set sourceHandle for event-based transitions (will be used if node has multiple events)
    ...(transitionType === 'event' && eventName && { sourceHandle: eventName }),
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
  // Normalize domain type (handle both hyphen and underscore variants)
  const rawType = meta.type;
  const domainType = typeof rawType === 'string' ? rawType.replace(/-/g, '_') : rawType;

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

    case 'parallel_approval':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'parallel',
        domainType: 'parallel_approval',
        approvers: meta.approvers as ParallelApprovalNodeData['approvers'],
        completionRule: (meta.completion_rule as ParallelApprovalNodeData['completionRule']) || 'all_required',
        quorumCount: meta.quorum_count as number | undefined,
        onReject: (meta.on_reject as ParallelApprovalNodeData['onReject']) || 'reject_all',
        slaHours: meta.sla_hours as number | undefined,
        priority: meta.priority as 'Low' | 'Medium' | 'High' | 'Urgent' | undefined,
      } as ParallelApprovalNodeData;
      break;

    case 'threshold_gate': {
      // Handle both new checkMode and legacy checkType
      const checkMode = meta.checkMode as ThresholdGateNodeData['checkMode'];
      const legacyCheckType = meta.checkType as 'field' | 'method' | undefined;

      // Determine effective mode for backward compatibility
      let effectiveMode: 'simple' | 'compound' | 'method' = 'simple';
      if (checkMode) {
        effectiveMode = checkMode;
      } else if (legacyCheckType === 'method') {
        effectiveMode = 'method';
      }

      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'atomic',
        domainType: 'threshold_gate',
        checkMode: effectiveMode,
        threshold: meta.threshold as ThresholdGateNodeData['threshold'],
        conditions: meta.conditions as ThresholdGateNodeData['conditions'],
        conditionLogic: (meta.conditionLogic as 'and' | 'or') || 'and',
        methodCheck: meta.methodCheck as ThresholdGateNodeData['methodCheck'],
      } as ThresholdGateNodeData;
      break;
    }

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

    case 'agentic':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'atomic',
        domainType: 'agentic',
        agentType: meta.agent_type as AgenticNodeData['agentType'],
        systemPrompt: meta.system_prompt as string,
        model: meta.model as string,
        enabledTools: meta.enabled_tools as ToolConfig[],
        frappeAccess: meta.frappe_access as AgenticNodeData['frappeAccess'],
        allowedMethods: meta.allowed_methods as AllowedMethod[],
        dataInput: meta.data_input as DataInputConfig,
        enabledMcps: meta.enabled_mcps as MCPServerConfig[],
        restEndpoints: meta.rest_endpoints as RestEndpointConfig[],
        transitionMode: meta.transition_mode as AgenticNodeData['transitionMode'],
        decisionRoutes: meta.decision_routes as DecisionRoute[],
        customEvents: meta.custom_events as CustomAgentEvent[],
        maxIterations: meta.max_iterations as number,
        timeoutSeconds: meta.timeout_seconds as number,
        retryOnFailure: meta.retry_on_failure as boolean,
        maxRetries: meta.max_retries as number,
      } as AgenticNodeData;
      break;

    case 'rest_fetch':
      nodeData = {
        label: (meta.label as string) || stateName,
        xstateType: 'atomic',
        domainType: 'rest_fetch',
        url: meta.url as string,
        method: meta.method as RestFetchNodeData['method'],
        authType: meta.auth_type as RestFetchNodeData['authType'],
        authCredential: meta.auth_credential as string,
        headers: meta.headers as Record<string, string>,
        body: meta.body as string,
        saveResponseTo: meta.save_response_to as string,
        onSuccess: meta.on_success as string,
        onError: meta.on_error as string,
        timeoutSeconds: meta.timeout_seconds as number,
      } as RestFetchNodeData;
      break;

    default:
      nodeData = {
        label: stateName,
        xstateType: 'atomic',
      };
  }

  // Add stateName to all domain nodes for position matching on reload
  nodeData.stateName = stateName;

  return {
    id: nodeId,
    type: domainType,
    position,
    data: nodeData,
    ...(parentId && { parentId, extent: 'parent' as const }),
  };
}
